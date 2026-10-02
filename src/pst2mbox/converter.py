"""
Core PST/OST to mbox converter implementation.
"""

from datetime import datetime, timezone
import email
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
import logging
import mailbox
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from pst2mbox.header_helper import HeaderItemsHelper

# Optional RTF to text converter
try:
    from striprtf.striprtf import rtf_to_text
    HAS_STRIPRTF = True
except ImportError:
    HAS_STRIPRTF = False

# Backend detection: Prioritize direct pypff (libpff-python), fallback to libratom
HAS_PYPFF = False
HAS_LIBRATOM = False

try:
    import pypff
    HAS_PYPFF = True
except ImportError:
    try:
        from libratom.lib.pff import PffArchive
        HAS_LIBRATOM = True
    except ImportError:
        pass


# MAPI Property Tags for deep inspection
MAPI_PR_SENDER_NAME = 0x0C1A
MAPI_PR_SENDER_EMAIL = 0x0C1F
MAPI_PR_SENT_REPRESENTING_NAME = 0x0042
MAPI_PR_SENT_REPRESENTING_EMAIL = 0x0065
MAPI_PR_DISPLAY_TO = 0x0E04
MAPI_PR_DISPLAY_CC = 0x0E03
MAPI_PR_DISPLAY_BCC = 0x0E02
MAPI_PR_MESSAGE_DELIVERY_TIME = 0x0E06
MAPI_PR_CLIENT_SUBMIT_TIME = 0x0039
MAPI_PR_CREATION_TIME = 0x3007
MAPI_PR_LAST_MODIFICATION_TIME = 0x3008
MAPI_PR_ATTACH_LONG_FILENAME = 0x3707
MAPI_PR_ATTACH_FILENAME = 0x3704
MAPI_PR_ATTACH_MIME_TAG = 0x370E
MAPI_PR_ATTACH_CONTENT_ID = 0x3712
MAPI_PR_ATTACH_DATA_BIN = 0x3701
MAPI_PR_RECIPIENT_TYPE = 0x0C15
MAPI_PR_DISPLAY_NAME = 0x3001
MAPI_PR_EMAIL_ADDRESS = 0x3003
MAPI_PR_SMTP_ADDRESS = 0x39FE


class PSTToMboxConverter:
    """Convert Outlook PST files to standard mbox format with high efficiency and robust error handling."""

    def __init__(
        self,
        pst_file: Union[str, Path],
        output_file: Union[str, Path],
        verbose: bool = False,
        quiet: bool = False,
        overwrite: bool = False,
        split_folders: bool = False,
        include_orphans: bool = False,
    ):
        """
        Initialize the converter.

        Args:
            pst_file: Path to the input PST/OST file.
            output_file: Path to the output mbox file (or directory if split_folders).
            verbose: Enable detailed debug logging.
            quiet: Suppress non-error output.
            overwrite: Overwrite existing output file(s) without prompt.
            split_folders: Split conversion into separate mbox files per folder.
            include_orphans: Include recovered orphan items if found.
        """
        self.pst_file = Path(pst_file).resolve()
        self.output_file = Path(output_file).resolve()
        self.verbose = verbose
        self.quiet = quiet
        self.overwrite = overwrite
        self.split_folders = split_folders
        self.include_orphans = include_orphans

        self.processed_emails = 0
        self.failed_emails = 0
        self.processed_folders = 0
        self.attachments_found = 0
        self.attachments_extracted = 0
        self.attachment_bytes = 0

        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging format and handlers."""
        if self.quiet:
            log_level = logging.WARNING
        elif self.verbose:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True,
        )
        self.logger = logging.getLogger("pst2mbox")

    def validate_files(self) -> None:
        """Validate input and output paths before starting."""
        if not self.pst_file.exists():
            raise FileNotFoundError(f"PST file not found: {self.pst_file}")

        if not self.pst_file.is_file():
            raise ValueError(f"Specified PST path is not a file: {self.pst_file}")

        if self.pst_file.suffix.lower() not in [".pst", ".ost"]:
            self.logger.warning(f"File extension is not .pst or .ost: {self.pst_file.name}")

        if self.split_folders:
            self.output_file.mkdir(parents=True, exist_ok=True)
        else:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            if self.output_file.exists() and not self.overwrite:
                try:
                    response = input(f"Output file '{self.output_file.name}' already exists. Overwrite? (y/N): ")
                    if response.strip().lower() not in ["y", "yes"]:
                        raise ValueError("Operation cancelled by user.")
                except EOFError:
                    raise ValueError(f"Output file '{self.output_file}' already exists. Use --overwrite to replace.")

    @staticmethod
    def safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
        """Safely retrieve attribute or method result from libpff / python objects."""
        if obj is None:
            return default
        try:
            val = getattr(obj, attr, default)
            if callable(val):
                val = val()
            return val if val is not None else default
        except (SystemError, ValueError, UnicodeDecodeError, OverflowError, AttributeError, Exception):
            return default

    @staticmethod
    def safe_decode(data: Any, default: str = "") -> str:
        """Safely decode binary data to string using multiple encoding fallbacks."""
        if data is None:
            return default
        if isinstance(data, str):
            return data
        if not isinstance(data, (bytes, bytearray)):
            return str(data)

        for enc in ("utf-8", "cp1252", "iso-8859-1", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("latin-1", errors="replace")

    @staticmethod
    def get_record_entry_value(record_set: Any, entry_type: int) -> Any:
        """Extract typed value from a libpff record_set by MAPI entry_type."""
        if not record_set:
            return None
        try:
            entry = record_set.get_entry_by_type(entry_type)
            if entry:
                s = getattr(entry, "data_as_string", None) or (
                    entry.get_data_as_string() if hasattr(entry, "get_data_as_string") else None
                )
                if s:
                    return s
                dt = getattr(entry, "data_as_datetime", None) or (
                    entry.get_data_as_datetime() if hasattr(entry, "get_data_as_datetime") else None
                )
                if dt:
                    return dt
                num = getattr(entry, "data_as_integer", None) or (
                    entry.get_data_as_integer() if hasattr(entry, "get_data_as_integer") else None
                )
                if num is not None:
                    return num
                d = getattr(entry, "data", None) or (entry.get_data() if hasattr(entry, "get_data") else None)
                if d:
                    return d
        except Exception:
            pass
        return None

    def format_email_address(self, address: Optional[str], name: Optional[str] = None) -> str:
        """Format display name and email address into RFC 2822 compliant string."""
        address = (address or "").strip()
        name = (name or "").strip()

        # Clean Exchange X.500 DNs like /O=EXCHANGELABS/OU=...
        if address.startswith("/") and "=" in address:
            cn_matches = re.findall(r"cn=([^/]+)", address, re.IGNORECASE)
            if cn_matches:
                extracted_name = cn_matches[-1].strip()
                if not name:
                    name = extracted_name
            address = ""

        if not address and not name:
            return ""

        if name and address:
            try:
                name.encode("ascii")
                clean_name = name.replace('"', '\\"')
                return f'"{clean_name}" <{address}>'
            except UnicodeEncodeError:
                encoded_name = Header(name, "utf-8").encode()
                return f"{encoded_name} <{address}>"
        elif address:
            return f"<{address}>" if ("@" in address and not address.startswith("<")) else address
        else:
            try:
                name.encode("ascii")
                return name
            except UnicodeEncodeError:
                return Header(name, "utf-8").encode()

    def extract_attachments(self, pst_message: Any) -> List[Dict[str, Any]]:
        """Extract attachments with full binary payloads, sanitized filenames, and MIME headers."""
        attachments = []
        num_attachments = self.safe_get_attr(pst_message, "number_of_attachments", 0) or 0
        if num_attachments <= 0:
            num_attachments = self.safe_get_attr(pst_message, "get_number_of_attachments", 0) or 0

        if num_attachments > 0:
            self.logger.debug(f"Message has {num_attachments} attachment(s)")
            self.attachments_found += num_attachments

            for i in range(num_attachments):
                try:
                    att = None
                    if hasattr(pst_message, "get_attachment"):
                        att = pst_message.get_attachment(i)
                    elif hasattr(pst_message, "attachments") and i < len(pst_message.attachments):
                        att = pst_message.attachments[i]

                    if not att:
                        continue

                    # Extract attachment filename from multiple possible attributes
                    filename = (
                        self.safe_get_attr(att, "long_filename")
                        or self.safe_get_attr(att, "get_long_filename")
                        or self.safe_get_attr(att, "name")
                        or self.safe_get_attr(att, "get_name")
                    )

                    # If not found via direct attributes, search record sets
                    if not filename and hasattr(att, "get_number_of_record_sets"):
                        for r_idx in range(self.safe_get_attr(att, "get_number_of_record_sets", 0) or 0):
                            rs = att.get_record_set(r_idx)
                            filename = self.get_record_entry_value(rs, MAPI_PR_ATTACH_LONG_FILENAME)
                            if not filename:
                                filename = self.get_record_entry_value(rs, MAPI_PR_ATTACH_FILENAME)
                            if filename:
                                break

                    # Sanitize filename
                    if filename:
                        filename = self.safe_decode(filename)
                        filename = os.path.basename(filename).strip()
                        filename = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", filename)

                    size = self.safe_get_attr(att, "size", 0) or self.safe_get_attr(att, "get_size", 0) or 0

                    # Read binary data
                    data = None
                    if hasattr(att, "read_buffer"):
                        try:
                            data = att.read_buffer(size) if size > 0 else att.read_buffer()
                        except Exception as e:
                            self.logger.debug(f"read_buffer error on attachment {i}: {e}")

                    if data is None and hasattr(att, "get_data"):
                        try:
                            data = att.get_data()
                        except Exception:
                            pass

                    if data is None:
                        data = self.safe_get_attr(att, "data", None)

                    # Determine MIME type
                    actual_size = len(data) if data else 0
                    if not filename:
                        ext = ".bin"
                        if data and data[:4] == b"%PDF":
                            ext = ".pdf"
                        elif data and data[:2] == b"\xff\xd8":
                            ext = ".jpg"
                        elif data and data[:8] == b"\x89PNG\r\n\x1a\n":
                            ext = ".png"
                        filename = f"attachment_{i+1}{ext}"

                    mime_type, _ = mimetypes.guess_type(filename)
                    if not mime_type:
                        mime_type = "application/octet-stream"

                    att_info = {
                        "filename": filename,
                        "size": actual_size or size,
                        "data": data,
                        "mime_type": mime_type,
                    }
                    attachments.append(att_info)

                    if actual_size > 0:
                        self.attachments_extracted += 1
                        self.attachment_bytes += actual_size
                        self.logger.debug(f"Extracted attachment: '{filename}' ({actual_size} bytes)")
                    elif size > 0:
                        self.logger.warning(f"Attachment '{filename}' reported size {size} but payload was empty")

                except Exception as e:
                    self.logger.warning(f"Failed to extract attachment {i}: {e}")

        return attachments

    def _extract_sender_info(self, pst_message: Any, hih: HeaderItemsHelper) -> Tuple[str, str]:
        """Extract sender name and email from transport headers, MAPI attributes, or record sets."""
        sender_name = ""
        sender_email = ""

        # 1. Try transport headers
        has_from, from_val = hih.get_header_item("From")
        if has_from and from_val:
            parsed_name, parsed_addr = email.utils.parseaddr(from_val)
            if parsed_addr:
                sender_email = parsed_addr
                sender_name = parsed_name
            elif from_val:
                match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", from_val)
                if match:
                    sender_email = match.group(1)
                    sender_name = from_val.replace(match.group(0), "").strip(' <"\'>\t\n\r')

        # 2. Check direct PST message attributes
        if not sender_name:
            sender_name = self.safe_decode(
                self.safe_get_attr(pst_message, "sender_name") or self.safe_get_attr(pst_message, "get_sender_name")
            )
        if not sender_email:
            sender_email = self.safe_decode(self.safe_get_attr(pst_message, "sender_email_address"))

        # 3. Check record sets for MAPI properties
        if hasattr(pst_message, "get_number_of_record_sets"):
            try:
                for r_idx in range(pst_message.get_number_of_record_sets()):
                    rs = pst_message.get_record_set(r_idx)
                    if not sender_name:
                        sender_name = self.safe_decode(
                            self.get_record_entry_value(rs, MAPI_PR_SENDER_NAME)
                            or self.get_record_entry_value(rs, MAPI_PR_SENT_REPRESENTING_NAME)
                        )
                    if not sender_email:
                        sender_email = self.safe_decode(
                            self.get_record_entry_value(rs, MAPI_PR_SENDER_EMAIL)
                            or self.get_record_entry_value(rs, MAPI_PR_SENT_REPRESENTING_EMAIL)
                        )
                    if sender_name and sender_email:
                        break
            except Exception:
                pass

        # Cleanup Exchange DNs
        if sender_email and sender_email.startswith("/") and "=" in sender_email:
            cn_matches = re.findall(r"cn=([^/]+)", sender_email, re.IGNORECASE)
            if cn_matches:
                extracted_name = cn_matches[-1].strip()
                if not sender_name:
                    sender_name = extracted_name
            sender_email = ""

        if not sender_email and not sender_name:
            sender_name = "Unknown Sender"
            sender_email = "unknown@pst-archive.local"
        elif not sender_email:
            clean_local = re.sub(r"[^a-zA-Z0-9._-]", "", sender_name.lower().replace(" ", ".")) or "user"
            sender_email = f"{clean_local}@pst-archive.local"

        return sender_name.strip(), sender_email.strip()

    def _extract_recipients(self, pst_message: Any, hih: HeaderItemsHelper) -> Dict[str, List[str]]:
        """Extract To, Cc, Bcc recipients from transport headers or message recipient structures."""
        recipients = {"To": [], "Cc": [], "Bcc": []}

        # 1. Transport headers
        for field in ("To", "Cc", "Bcc"):
            exists, val = hih.get_header_item(field)
            if exists and val:
                recipients[field].append(val)

        # 2. If transport headers didn't have recipients, check PST recipient structures
        if not recipients["To"] and not recipients["Cc"] and not recipients["Bcc"]:
            recips_obj = self.safe_get_attr(pst_message, "recipients")
            if recips_obj and hasattr(recips_obj, "get_number_of_recipients"):
                num_recips = self.safe_get_attr(recips_obj, "get_number_of_recipients", 0) or 0
                for r_idx in range(num_recips):
                    try:
                        recip_item = recips_obj.get_recipient(r_idx)
                        r_name = ""
                        r_email = ""
                        r_type = 1

                        if hasattr(recip_item, "get_number_of_record_sets"):
                            for s_idx in range(recip_item.get_number_of_record_sets()):
                                rs = recip_item.get_record_set(s_idx)
                                if not r_name:
                                    r_name = self.safe_decode(self.get_record_entry_value(rs, MAPI_PR_DISPLAY_NAME))
                                if not r_email:
                                    r_email = self.safe_decode(
                                        self.get_record_entry_value(rs, MAPI_PR_SMTP_ADDRESS)
                                        or self.get_record_entry_value(rs, MAPI_PR_EMAIL_ADDRESS)
                                    )
                                t_val = self.get_record_entry_value(rs, MAPI_PR_RECIPIENT_TYPE)
                                if t_val is not None:
                                    r_type = t_val

                        formatted = self.format_email_address(r_email, r_name)
                        if formatted:
                            if r_type == 2:
                                recipients["Cc"].append(formatted)
                            elif r_type == 3:
                                recipients["Bcc"].append(formatted)
                            else:
                                recipients["To"].append(formatted)
                    except Exception as e:
                        self.logger.debug(f"Error parsing recipient {r_idx}: {e}")

            if not recipients["To"]:
                disp_to = self.safe_decode(self.safe_get_attr(pst_message, "display_to"))
                if disp_to:
                    recipients["To"].append(disp_to)
            if not recipients["Cc"]:
                disp_cc = self.safe_decode(self.safe_get_attr(pst_message, "display_cc"))
                if disp_cc:
                    recipients["Cc"].append(disp_cc)

        return recipients

    def _extract_datetime(self, pst_message: Any, hih: HeaderItemsHelper) -> datetime:
        """Extract delivery / message timestamp as a valid datetime object and RFC 2822 string."""
        for attr in (
            "delivery_time",
            "get_delivery_time",
            "client_submit_time",
            "get_client_submit_time",
            "creation_time",
            "get_creation_time",
            "modification_time",
            "get_modification_time",
        ):
            dt = self.safe_get_attr(pst_message, attr)
            if isinstance(dt, datetime):
                return dt
            elif isinstance(dt, (int, float)) and dt > 0:
                try:
                    return datetime.fromtimestamp(dt, tz=timezone.utc)
                except Exception:
                    pass

        has_date, date_val = hih.get_header_item("Date", decode=False)
        if has_date and date_val:
            try:
                dt = email.utils.parsedate_to_datetime(date_val.strip())
                if dt:
                    return dt
            except Exception:
                pass

        return datetime.now(timezone.utc)

    def convert_pst_message_to_email(self, pst_message: Any, folder_path: str = "") -> email.message.Message:
        """
        Convert a single PST message into a standard email.message.Message object.
        """
        try:
            raw_headers = (
                self.safe_get_attr(pst_message, "transport_headers")
                or self.safe_get_attr(pst_message, "get_transport_headers")
                or ""
            )
            hih = HeaderItemsHelper(raw_headers)

            body_text = self.safe_decode(
                self.safe_get_attr(pst_message, "plain_text_body")
                or self.safe_get_attr(pst_message, "get_plain_text_body")
            )
            body_html = self.safe_decode(
                self.safe_get_attr(pst_message, "html_body") or self.safe_get_attr(pst_message, "get_html_body")
            )
            body_rtf = self.safe_decode(
                self.safe_get_attr(pst_message, "rtf_body") or self.safe_get_attr(pst_message, "get_rtf_body")
            )

            if not body_text and not body_html and body_rtf:
                if HAS_STRIPRTF:
                    try:
                        body_text = rtf_to_text(body_rtf)
                    except Exception:
                        body_text = body_rtf
                else:
                    body_text = body_rtf

            attachments = self.extract_attachments(pst_message)

            if attachments:
                msg = MIMEMultipart("mixed")
                if body_html and body_text:
                    alt_part = MIMEMultipart("alternative")
                    alt_part.attach(MIMEText(body_text, "plain", "utf-8"))
                    alt_part.attach(MIMEText(body_html, "html", "utf-8"))
                    msg.attach(alt_part)
                elif body_html:
                    msg.attach(MIMEText(body_html, "html", "utf-8"))
                elif body_text:
                    msg.attach(MIMEText(body_text, "plain", "utf-8"))
                else:
                    msg.attach(MIMEText("(No message body)", "plain", "utf-8"))

                for att in attachments:
                    data = att.get("data")
                    if data:
                        maintype, subtype = att.get("mime_type", "application/octet-stream").split("/", 1)
                        part = MIMEBase(maintype, subtype)
                        part.set_payload(data)
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f'attachment; filename="{att["filename"]}"')
                        msg.attach(part)

            elif body_html and body_text:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
                msg.attach(MIMEText(body_html, "html", "utf-8"))
            elif body_html:
                msg = MIMEText(body_html, "html", "utf-8")
            elif body_text:
                msg = MIMEText(body_text, "plain", "utf-8")
            else:
                msg = MIMEText("(No message body)", "plain", "utf-8")

            subject = ""
            has_subj, header_subj = hih.get_header_item("Subject")
            if has_subj and header_subj:
                subject = header_subj
            else:
                subject = self.safe_decode(
                    self.safe_get_attr(pst_message, "subject") or self.safe_get_attr(pst_message, "get_subject")
                )

            msg["Subject"] = subject or "(No Subject)"

            sender_name, sender_email = self._extract_sender_info(pst_message, hih)
            msg["From"] = self.format_email_address(sender_email, sender_name)

            dt = self._extract_datetime(pst_message, hih)
            msg["Date"] = email.utils.format_datetime(dt)

            asctime_date = dt.strftime("%a %b %d %H:%M:%S %Y")
            msg.set_unixfrom(f"From {sender_email} {asctime_date}")

            recipients = self._extract_recipients(pst_message, hih)
            if recipients["To"]:
                msg["To"] = ", ".join(recipients["To"])
            if recipients["Cc"]:
                msg["Cc"] = ", ".join(recipients["Cc"])
            if recipients["Bcc"]:
                msg["Bcc"] = ", ".join(recipients["Bcc"])

            has_mid, msg_id = hih.get_header_item("Message-ID")
            if has_mid and msg_id:
                msg["Message-ID"] = msg_id
            else:
                clean_id = f"{abs(hash((subject, sender_email, dt.isoformat()))):x}"
                domain = sender_email.split("@")[-1] if "@" in sender_email else "pst-export.local"
                msg["Message-ID"] = f"<{clean_id}@{domain}>"

            has_reply_to, reply_to = hih.get_header_item("In-Reply-To")
            if has_reply_to and reply_to:
                msg["In-Reply-To"] = reply_to

            has_refs, refs = hih.get_header_item("References")
            if has_refs and refs:
                msg["References"] = refs

            if folder_path:
                msg["X-Folder"] = folder_path

            return msg

        except Exception as e:
            self.logger.error(f"Error converting PST message to email: {e}", exc_info=self.verbose)
            raise

    def _iterate_pypff(self, pff_file: Any) -> Iterator[Tuple[str, Any]]:
        """Recursively iterate over all folders and submessages using pypff."""
        root_folder = pff_file.get_root_folder()
        if not root_folder:
            return

        def _traverse_folder(folder: Any, path: str = "") -> Iterator[Tuple[str, Any]]:
            folder_name = self.safe_decode(
                self.safe_get_attr(folder, "name") or self.safe_get_attr(folder, "get_name") or ""
            )
            current_path = f"{path}/{folder_name}".strip("/") if path else folder_name

            num_msgs = (
                self.safe_get_attr(folder, "number_of_sub_messages", 0)
                or self.safe_get_attr(folder, "get_number_of_sub_messages", 0)
                or 0
            )
            if num_msgs > 0:
                self.logger.debug(f"Scanning folder: '{current_path}' ({num_msgs} messages)")
                self.processed_folders += 1
                for m_idx in range(num_msgs):
                    try:
                        msg = None
                        if hasattr(folder, "get_sub_message"):
                            msg = folder.get_sub_message(m_idx)
                        elif hasattr(folder, "sub_messages") and m_idx < len(folder.sub_messages):
                            msg = folder.sub_messages[m_idx]

                        if msg:
                            yield current_path, msg
                    except Exception as e:
                        self.failed_emails += 1
                        self.logger.error(f"Failed reading message {m_idx} in folder '{current_path}': {e}")

            num_subfolders = (
                self.safe_get_attr(folder, "number_of_sub_folders", 0)
                or self.safe_get_attr(folder, "get_number_of_sub_folders", 0)
                or 0
            )
            for f_idx in range(num_subfolders):
                try:
                    sub = None
                    if hasattr(folder, "get_sub_folder"):
                        sub = folder.get_sub_folder(f_idx)
                    elif hasattr(folder, "sub_folders") and f_idx < len(folder.sub_folders):
                        sub = folder.sub_folders[f_idx]

                    if sub:
                        yield from _traverse_folder(sub, current_path)
                except Exception as e:
                    self.logger.error(f"Failed traversing subfolder {f_idx} in '{current_path}': {e}")

        yield from _traverse_folder(root_folder)

        if self.include_orphans and hasattr(pff_file, "get_number_of_orphan_items"):
            num_orphans = self.safe_get_attr(pff_file, "get_number_of_orphan_items", 0) or 0
            if num_orphans > 0:
                self.logger.info(f"Found {num_orphans} orphan item(s) in PST")
                for o_idx in range(num_orphans):
                    try:
                        orphan_msg = pff_file.get_orphan_item(o_idx)
                        if orphan_msg:
                            yield "Recovered_Orphans", orphan_msg
                    except Exception as e:
                        self.logger.debug(f"Failed reading orphan item {o_idx}: {e}")

    def _iterate_libratom(self, pst_archive: Any) -> Iterator[Tuple[str, Any]]:
        """Iterate messages using libratom PffArchive."""
        for pst_message in pst_archive.messages():
            folder_path = "Unknown"
            try:
                if hasattr(pst_message, "folder") and pst_message.folder:
                    folder_path = self.safe_get_attr(pst_message.folder, "name", "Unknown")
            except Exception:
                pass
            yield folder_path, pst_message

    def convert(self) -> bool:
        """Execute the conversion process."""
        start_time = time.time()
        self.logger.info(f"Starting PST to mbox conversion: '{self.pst_file.name}'")

        if not HAS_PYPFF and not HAS_LIBRATOM:
            self.logger.error("No PST parsing library found! Please install libpff-python: pip install libpff-python")
            return False

        self.validate_files()

        pff_handle = None
        pst_archive = None

        if HAS_PYPFF:
            try:
                pff_handle = pypff.file()
                pff_handle.open(str(self.pst_file))
                pst_size_mb = self.pst_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"Opened PST archive using libpff ({pst_size_mb:.2f} MB)")
            except Exception as e:
                self.logger.error(f"Failed opening PST file with libpff: {e}")
                return False
        elif HAS_LIBRATOM:
            try:
                pst_archive = PffArchive(str(self.pst_file))
                pst_size_mb = self.pst_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"Opened PST archive using libratom ({pst_size_mb:.2f} MB)")
            except Exception as e:
                self.logger.error(f"Failed opening PST file with libratom: {e}")
                return False

        open_mbox_files: Dict[Union[str, Path], mailbox.mbox] = {}

        try:
            if not self.split_folders:
                main_mbox = mailbox.mbox(str(self.output_file))
                main_mbox.lock()
                open_mbox_files["default"] = main_mbox

            msg_iterator = self._iterate_pypff(pff_handle) if HAS_PYPFF else self._iterate_libratom(pst_archive)

            for folder_path, pst_message in msg_iterator:
                try:
                    email_msg = self.convert_pst_message_to_email(pst_message, folder_path)

                    if self.split_folders:
                        clean_folder = re.sub(r'[\\/*?:"<>|]', "_", folder_path).strip("_") or "Inbox"
                        folder_mbox_path = self.output_file / f"{clean_folder}.mbox"
                        if folder_mbox_path not in open_mbox_files:
                            m = mailbox.mbox(str(folder_mbox_path))
                            m.lock()
                            open_mbox_files[folder_mbox_path] = m
                        target_mbox = open_mbox_files[folder_mbox_path]
                    else:
                        target_mbox = open_mbox_files["default"]

                    target_mbox.add(email_msg)
                    self.processed_emails += 1

                    if self.processed_emails % 100 == 0:
                        elapsed = time.time() - start_time
                        speed = self.processed_emails / elapsed if elapsed > 0 else 0
                        self.logger.info(f"Progress: {self.processed_emails} emails processed ({speed:.1f} emails/s)...")

                except Exception as e:
                    self.failed_emails += 1
                    self.logger.error(f"Failed to process email {self.processed_emails + self.failed_emails}: {e}")

            for m in open_mbox_files.values():
                try:
                    m.flush()
                finally:
                    m.unlock()
                    m.close()

        finally:
            if pff_handle:
                try:
                    pff_handle.close()
                except Exception:
                    pass

        duration = time.time() - start_time
        out_size_mb = 0.0
        if self.split_folders:
            out_size_mb = sum(f.stat().st_size for f in self.output_file.glob("*.mbox")) / (1024 * 1024)
        elif self.output_file.exists():
            out_size_mb = self.output_file.stat().st_size / (1024 * 1024)

        self.logger.info("\n" + "=" * 55)
        self.logger.info("🎉 CONVERSION COMPLETED SUCCESSFULLY")
        self.logger.info("=" * 55)
        self.logger.info(f"Input file:            {self.pst_file}")
        self.logger.info(f"Output location:       {self.output_file}")
        self.logger.info(f"Emails converted:      {self.processed_emails}")
        self.logger.info(f"Failed emails:         {self.failed_emails}")
        self.logger.info(
            f"Attachments extracted: {self.attachments_extracted} ({self.attachment_bytes / (1024*1024):.2f} MB)"
        )
        self.logger.info(f"Total output size:     {out_size_mb:.2f} MB")
        self.logger.info(f"Total time elapsed:    {duration:.2f} seconds")
        if self.processed_emails > 0 and duration > 0:
            self.logger.info(f"Average speed:         {self.processed_emails / duration:.1f} emails/second")
        self.logger.info("=" * 55 + "\n")

        return True
