"""
HeaderItemsHelper - Robust parser and decoder for email transport headers (RFC 5322 / RFC 2822 / RFC 822).
"""

from email.header import decode_header
from typing import Dict, List, Optional, Tuple, Union


class HeaderItemsHelper:
    """Helps working with the items contained in the transport headers of an email message."""

    def __init__(self, email_transport_header: Optional[Union[str, bytes]] = None):
        self.__items_dictionary: Dict[str, str] = {}  # normalized lowercase key -> value
        self.__original_keys: Dict[str, str] = {}  # normalized lowercase key -> original casing key
        self.raw_headers = email_transport_header or ""
        self.header_to_dict(email_transport_header)

    @staticmethod
    def decode_rfc2047(header_val: Optional[str]) -> str:
        """Safely decode RFC 2047 encoded words (e.g. =?UTF-8?B?...?=)."""
        if not header_val:
            return ""
        try:
            decoded_parts = decode_header(header_val)
            result = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    enc = encoding or "utf-8"
                    try:
                        result.append(part.decode(enc, errors="replace"))
                    except (LookupError, UnicodeDecodeError):
                        result.append(part.decode("latin-1", errors="replace"))
                else:
                    result.append(str(part))
            return "".join(result)
        except Exception:
            return str(header_val)

    def header_to_dict(self, headers: Optional[Union[str, bytes]]) -> None:
        """Convert headers string or bytes to a normalized dictionary."""
        self.__items_dictionary.clear()
        self.__original_keys.clear()

        if not headers:
            return

        if isinstance(headers, bytes):
            try:
                headers_str = headers.decode("utf-8", errors="replace")
            except Exception:
                headers_str = headers.decode("latin-1", errors="replace")
        else:
            headers_str = str(headers)

        current_header_key = None

        for h_line in headers_str.splitlines():
            # Check for header continuation (folding, starts with space or tab)
            if h_line and h_line[0] in (" ", "\t"):
                if current_header_key:
                    self.__items_dictionary[current_header_key] += " " + h_line.strip()
            elif ":" in h_line:
                key, value = h_line.split(":", 1)
                clean_key = key.strip()
                norm_key = clean_key.lower()
                clean_val = value.strip()

                # If duplicate header (e.g. Received), append with newline
                if norm_key in self.__items_dictionary:
                    self.__items_dictionary[norm_key] += "\n" + clean_val
                else:
                    self.__items_dictionary[norm_key] = clean_val
                    self.__original_keys[norm_key] = clean_key
                current_header_key = norm_key
            else:
                # Malformed line without colon and not indented
                current_header_key = None

    def get_header_item(self, header_item_name: str, decode: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Get the value of a specific header item, case-insensitively.

        Returns:
            Tuple[bool, Optional[str]]: (exists, value)
        """
        if not header_item_name:
            return False, None

        norm_key = header_item_name.strip().lower()
        if norm_key in self.__items_dictionary:
            val = self.__items_dictionary[norm_key]
            if decode:
                val = self.decode_rfc2047(val)
            return True, val
        return False, None

    def contains_header_item(self, header_item_name: str) -> bool:
        """Check if a specific header item exists in the transport headers."""
        if not header_item_name:
            return False
        return header_item_name.strip().lower() in self.__items_dictionary

    def header_item_names(self) -> List[str]:
        """Get all header item names (original casing preserved)."""
        return sorted(self.__original_keys.values())

    def get_dict(self, decode: bool = True) -> Dict[str, str]:
        """Return all headers as a dictionary (original casing)."""
        res = {}
        for norm_key, orig_key in self.__original_keys.items():
            val = self.__items_dictionary[norm_key]
            res[orig_key] = self.decode_rfc2047(val) if decode else val
        return res
