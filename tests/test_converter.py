"""
Unit tests for pst2mbox converter, filters, metadata export, and HeaderItemsHelper.
"""

import csv
from datetime import datetime, timezone
import json
import mailbox
from pathlib import Path
import tempfile
import unittest

from pst2mbox.converter import PSTToMboxConverter
from pst2mbox.header_helper import HeaderItemsHelper


class TestHeaderItemsHelper(unittest.TestCase):
    def test_empty_and_none(self):
        h1 = HeaderItemsHelper(None)
        self.assertEqual(h1.get_header_item("From"), (False, None))
        self.assertFalse(h1.contains_header_item("Subject"))

        h2 = HeaderItemsHelper("")
        self.assertEqual(h2.get_header_item("Date"), (False, None))

    def test_case_insensitivity(self):
        raw = "From: Alice <alice@example.com>\nSUBJECT: Test Subject\ndate: Fri, 02 Oct 2026 10:00:00 +0000"
        h = HeaderItemsHelper(raw)
        self.assertTrue(h.contains_header_item("from"))
        self.assertTrue(h.contains_header_item("FROM"))
        self.assertTrue(h.contains_header_item("Subject"))
        self.assertTrue(h.contains_header_item("DATE"))
        self.assertEqual(h.get_header_item("from")[1], "Alice <alice@example.com>")
        self.assertEqual(h.get_header_item("subject")[1], "Test Subject")

    def test_multiline_folding(self):
        raw = (
            "Subject: This is a very long\n"
            " subject line that was\n"
            " folded across multiple lines\n"
            "From: Bob <bob@test.com>"
        )
        h = HeaderItemsHelper(raw)
        self.assertEqual(
            h.get_header_item("Subject")[1],
            "This is a very long subject line that was folded across multiple lines",
        )
        self.assertEqual(h.get_header_item("From")[1], "Bob <bob@test.com>")

    def test_rfc2047_decoding(self):
        encoded_subj = "=?UTF-8?B?SGVsbG8gV29ybGQg8J+agA==?="
        raw = f"Subject: {encoded_subj}\nFrom: =?ISO-8859-1?Q?Andr=E9?= <andre@example.com>"
        h = HeaderItemsHelper(raw)
        self.assertEqual(h.get_header_item("Subject")[1], "Hello World 🚀")
        self.assertEqual(h.get_header_item("From")[1], "André <andre@example.com>")

    def test_parsing_stops_at_end_of_header_block(self):
        raw = (
            "Subject: Outer\r\nTo: a@example.com\r\n\r\n--boundary\r\nContent-Type: message/rfc822\r\n\r\n"
            "Subject: Attached mail\r\nTo: b@example.com\r\n"
        )
        h = HeaderItemsHelper(raw)
        self.assertEqual(h.get_header_item("Subject"), (True, "Outer"))
        self.assertEqual(h.get_header_item("To"), (True, "a@example.com"))
        self.assertFalse(h.contains_header_item("Content-Type"))

    def test_single_value_headers_return_first_occurrence(self):
        h = HeaderItemsHelper("Received: one\r\nSubject: First\r\nReceived: two\r\nSubject: Second\r\n")
        self.assertEqual(h.get_header_item("Subject"), (True, "First"))
        self.assertEqual(h.get_header_item("Received"), (True, "one\ntwo"))

    def test_get_dict_and_names(self):
        raw = "From: Alice <alice@example.com>\nTo: Bob <bob@example.com>\nSubject: Hi"
        h = HeaderItemsHelper(raw)
        d = h.get_dict()
        self.assertEqual(len(d), 3)
        self.assertIn("From", d)
        self.assertIn("To", d)
        self.assertIn("Subject", d)
        names = h.header_item_names()
        self.assertEqual(names, ["From", "Subject", "To"])


class MockPffAttachment:
    def __init__(self, name, data, size=None):
        self._name = name
        self._data = data
        self._size = size if size is not None else (len(data) if data else 0)

    def get_long_filename(self):
        return self._name

    def get_size(self):
        return self._size

    def read_buffer(self, size=0):
        return self._data

    def get_number_of_record_sets(self):
        return 0


class MockPffMessage:
    def __init__(
        self,
        subject="Test",
        sender_name="Sender",
        sender_email="sender@example.com",
        body_text="Hello text",
        body_html="<p>Hello HTML</p>",
        transport_headers="",
        delivery_time=None,
        attachments=None,
    ):
        self.subject = subject
        self.sender_name = sender_name
        self.sender_email_address = sender_email
        self.plain_text_body = body_text
        self.html_body = body_html
        self.transport_headers = transport_headers
        self.delivery_time = delivery_time or datetime(2026, 10, 2, 8, 30, 0, tzinfo=timezone.utc)
        self._attachments = attachments or []

    def get_number_of_attachments(self):
        return len(self._attachments)

    def get_attachment(self, idx):
        return self._attachments[idx]

    def get_number_of_record_sets(self):
        return 0


class TestPSTToMboxConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_mbox = Path(self.temp_dir.name) / "test.mbox"
        self.converter = PSTToMboxConverter(
            pst_file=Path(self.temp_dir.name) / "fake.pst",
            output_file=self.output_mbox,
            verbose=False,
            quiet=True,
            overwrite=True,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_message_conversion_basic(self):
        mock_msg = MockPffMessage(
            subject="Important Meeting",
            sender_name="John Doe",
            sender_email="john.doe@example.com",
            body_text="See you tomorrow at 10 AM.",
            body_html="<p>See you tomorrow at 10 AM.</p>",
            delivery_time=datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc),
        )
        res = self.converter.convert_pst_message_to_email(mock_msg, folder_path="Inbox/Work")
        self.assertIsNotNone(res)
        email_msg, meta, atts = res

        self.assertEqual(email_msg["Subject"], "Important Meeting")
        self.assertEqual(email_msg["From"], '"John Doe" <john.doe@example.com>')
        self.assertIn("10:00:00", email_msg["Date"])
        self.assertEqual(email_msg["X-Folder"], "Inbox/Work")
        self.assertTrue(email_msg.is_multipart())
        self.assertEqual(meta["subject"], "Important Meeting")

    def test_message_with_attachment(self):
        pdf_bytes = b"%PDF-1.4 test pdf content here"
        att = MockPffAttachment("report.pdf", pdf_bytes)
        mock_msg = MockPffMessage(subject="Report Attached", attachments=[att])
        res = self.converter.convert_pst_message_to_email(mock_msg)
        self.assertIsNotNone(res)
        email_msg, meta, atts = res

        self.assertEqual(email_msg["Subject"], "Report Attached")
        self.assertEqual(len(atts), 1)
        self.assertEqual(atts[0]["filename"], "report.pdf")

    def test_date_and_folder_filtering(self):
        msg_old = MockPffMessage(
            subject="Old Message",
            delivery_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        msg_new = MockPffMessage(
            subject="New Message",
            delivery_time=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )

        date_filtered_converter = PSTToMboxConverter(
            pst_file=Path(self.temp_dir.name) / "fake.pst",
            output_file=self.output_mbox,
            from_date="2025-01-01",
            folder_filter="Inbox",
            quiet=True,
        )

        # Older message should be filtered out (return None)
        self.assertIsNone(date_filtered_converter.convert_pst_message_to_email(msg_old, "Inbox"))
        # Folder mismatch should be filtered out
        self.assertIsNone(date_filtered_converter.convert_pst_message_to_email(msg_new, "Archive"))
        # Matching message and folder should succeed
        self.assertIsNotNone(date_filtered_converter.convert_pst_message_to_email(msg_new, "Inbox"))

    def test_search_and_sender_filtering(self):
        msg = MockPffMessage(
            subject="Urgent: Invoice 12345",
            sender_name="Accounting Dept",
            sender_email="billing@company.com",
            body_text="Please pay the attached invoice.",
        )

        search_conv = PSTToMboxConverter(
            pst_file=Path(self.temp_dir.name) / "fake.pst",
            output_file=self.output_mbox,
            sender_filter="billing@company.com",
            search_query="invoice",
            quiet=True,
        )
        self.assertIsNotNone(search_conv.convert_pst_message_to_email(msg, "Inbox"))

        nomatch_conv = PSTToMboxConverter(
            pst_file=Path(self.temp_dir.name) / "fake.pst",
            output_file=self.output_mbox,
            sender_filter="support@other.com",
            quiet=True,
        )
        self.assertIsNone(nomatch_conv.convert_pst_message_to_email(msg, "Inbox"))

    def test_raw_attachment_and_metadata_export(self):
        att_dir = Path(self.temp_dir.name) / "attachments"
        csv_file = Path(self.temp_dir.name) / "meta.csv"
        json_file = Path(self.temp_dir.name) / "meta.json"

        conv = PSTToMboxConverter(
            pst_file=Path(self.temp_dir.name) / "fake.pst",
            output_file=self.output_mbox,
            extract_attachments_dir=att_dir,
            metadata_csv=csv_file,
            metadata_json=json_file,
            quiet=True,
            overwrite=True,
        )

        doc_bytes = b"Sample document text content"
        att = MockPffAttachment("sample.txt", doc_bytes)
        msg = MockPffMessage(subject="File Share", attachments=[att])

        res = conv.convert_pst_message_to_email(msg, "Shared")
        self.assertIsNotNone(res)
        email_msg, meta, atts = res
        conv.metadata_records.append(meta)
        conv._save_raw_attachments("Shared", atts)
        conv._write_metadata_files()

        # Check saved attachment on disk
        saved_file = att_dir / "Shared" / "sample.txt"
        self.assertTrue(saved_file.exists())
        self.assertEqual(saved_file.read_bytes(), doc_bytes)

        # Check CSV and JSON exports
        self.assertTrue(csv_file.exists())
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 1)
            self.assertEqual(reader[0]["subject"], "File Share")

        self.assertTrue(json_file.exists())
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["subject"], "File Share")

    def test_rtf_body_fallback(self):
        rtf_content = r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Arial;}}\f0\fs24 Hello from RTF body!}"
        mock_msg = MockPffMessage(subject="RTF Only", body_text="", body_html="", transport_headers="")
        mock_msg.rtf_body = rtf_content
        res = self.converter.convert_pst_message_to_email(mock_msg)
        self.assertIsNotNone(res)
        email_msg, _, _ = res
        self.assertEqual(email_msg["Subject"], "RTF Only")
        payload = email_msg.get_payload(decode=True).decode("utf-8")
        self.assertIn("Hello from RTF body!", payload)

    def test_rtf_emoji_surrogates_are_joined(self):
        # striprtf turns RTF \uN escapes for emoji into UTF-16 surrogate halves, which UTF-8 cannot encode
        rtf_content = r"{\rtf1\ansi Handy \u-10179?\u-8975? funktioniert}"
        mock_msg = MockPffMessage(subject="Emoji", body_text="", body_html="")
        mock_msg.rtf_body = rtf_content
        email_msg, _, _ = self.converter.convert_pst_message_to_email(mock_msg)
        payload = email_msg.get_payload(decode=True).decode("utf-8")
        self.assertIn("Handy \U0001f4f1 funktioniert", payload)

    def test_rtf_with_undecodable_byte_is_still_converted(self):
        # \'8d is undefined in cp1252; striprtf used to raise and the raw RTF source ended up as the body
        mock_msg = MockPffMessage(subject="RTF", body_text="", body_html="")
        mock_msg.rtf_body = r"{\rtf1\ansi\ansicpg1252 Gr\'fc\'dfe \'8d Ende}"
        email_msg, _, _ = self.converter.convert_pst_message_to_email(mock_msg)
        payload = email_msg.get_payload(decode=True).decode("utf-8")
        self.assertIn("Grüße", payload)
        self.assertNotIn("rtf1", payload)

    def test_lone_surrogates_are_replaced(self):
        mock_msg = MockPffMessage(subject="Broken \ud83d text", body_text="a\udcf1b", body_html="")
        email_msg, _, _ = self.converter.convert_pst_message_to_email(mock_msg)
        self.assertEqual(email_msg["Subject"], "Broken � text")
        self.assertIn("a�b", email_msg.get_payload(decode=True).decode("utf-8"))
        email_msg.as_bytes()

    def test_duplicate_transport_headers_use_first_value(self):
        headers = (
            "Subject: Panalpina / Rahbanan AZ 009-912-10\r\n"
            "From: Alice <alice@example.com>\r\n"
            "\r\n"
            "Subject: AW: Unfall vom 9.1.2010\r\n"
            "From: Bob <bob@example.com>\r\n"
        )
        mock_msg = MockPffMessage(transport_headers=headers)
        email_msg, _, _ = self.converter.convert_pst_message_to_email(mock_msg)
        self.assertEqual(email_msg["Subject"], "Panalpina / Rahbanan AZ 009-912-10")
        self.assertEqual(email_msg["From"], '"Alice" <alice@example.com>')
        email_msg.as_bytes()  # used to raise "header value appears to contain an embedded header"

    def test_line_breaks_in_header_values_are_removed(self):
        mock_msg = MockPffMessage(subject="Line one\r\nLine two", sender_name="Jane\nDoe")
        email_msg, _, _ = self.converter.convert_pst_message_to_email(mock_msg, "Inbox\nSub")
        self.assertEqual(email_msg["Subject"], "Line one Line two")
        self.assertEqual(email_msg["From"], '"Jane Doe" <sender@example.com>')
        self.assertEqual(email_msg["X-Folder"], "Inbox Sub")
        email_msg.as_bytes()

    def test_mbox_file_integration(self):
        mock_msg1 = MockPffMessage(
            subject="Email 1",
            sender_name="Alice",
            sender_email="alice@example.com",
            body_text="Body 1",
        )
        mock_msg2 = MockPffMessage(
            subject="Email 2",
            sender_name="Bob",
            sender_email="bob@example.com",
            body_text="Body 2",
        )
        mbox_target = Path(self.temp_dir.name) / "output.mbox"
        mb = mailbox.mbox(str(mbox_target))
        mb.lock()
        res1 = self.converter.convert_pst_message_to_email(mock_msg1, "Inbox")
        res2 = self.converter.convert_pst_message_to_email(mock_msg2, "Archive")
        mb.add(res1[0])
        mb.add(res2[0])
        mb.flush()
        mb.unlock()
        mb.close()

        read_mb = mailbox.mbox(str(mbox_target))
        self.assertEqual(len(read_mb), 2)
        self.assertEqual(read_mb[0]["Subject"], "Email 1")
        self.assertEqual(read_mb[0]["X-Folder"], "Inbox")
        self.assertEqual(read_mb[1]["Subject"], "Email 2")
        self.assertEqual(read_mb[1]["X-Folder"], "Archive")
        read_mb.close()


class message:  # noqa: N801 - name mirrors pypff.message, which the recovery path checks by type name
    pass


class folder_stub:  # noqa: N801
    """Folder whose message table is damaged but whose item tree is intact."""

    name = "Inbox"
    number_of_sub_folders = 0

    def __init__(self, items, table_ok=False):
        self._items = items
        self._table_ok = table_ok

    @property
    def number_of_sub_messages(self):
        if self._table_ok:
            return len(self._items)
        raise OSError("libpff_table_read_index_entries: invalid table index offset")

    @property
    def number_of_sub_items(self):
        return len(self._items)

    def get_sub_item(self, i):
        return self._items[i]

    def get_sub_message(self, i):
        return self._items[i]


class root_stub:  # noqa: N801
    name = ""
    number_of_sub_messages = 0
    number_of_sub_folders = 1

    def __init__(self, sub):
        self._sub = sub

    def get_sub_folder(self, i):
        return self._sub


class pff_stub:  # noqa: N801
    number_of_orphan_items = 0

    def __init__(self, root):
        self._root = root

    def get_root_folder(self):
        return self._root


class TestMboxFromLine(unittest.TestCase):
    def test_non_ascii_sender_is_sanitised(self):
        f = PSTToMboxConverter._mbox_from_address
        self.assertEqual(f("jürgen@example.com"), "jurgen@example.com")
        self.assertEqual(f("Üö ä"), "UoA".replace("A", "a"))
        self.assertEqual(f("日本"), "MAILER-DAEMON")
        self.assertEqual(f(None), "MAILER-DAEMON")

    def test_mbox_write_with_non_ascii_sender(self):
        with tempfile.TemporaryDirectory() as tmp:
            pst = Path(tmp) / "t.pst"
            pst.write_bytes(b"x")
            conv = PSTToMboxConverter(pst, Path(tmp) / "o.mbox", quiet=True)
            msg = MockPffMessage(subject="Hi", sender_email="jürgen@müller.de", sender_name="Jürgen")
            email_msg, _, _ = conv.convert_pst_message_to_email(msg, "Inbox")
            box = mailbox.mbox(str(Path(tmp) / "o.mbox"))
            box.add(email_msg)
            box.flush()
            box.close()
            self.assertEqual(len(mailbox.mbox(str(Path(tmp) / "o.mbox"))), 1)


class TestDamagedFolderRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pst = Path(self.tmp.name) / "t.pst"
        self.pst.write_bytes(b"x")

    def tearDown(self):
        self.tmp.cleanup()

    def _iterate(self, folder):
        conv = PSTToMboxConverter(self.pst, Path(self.tmp.name) / "o.mbox", quiet=True)
        return conv, list(conv._iterate_pypff(pff_stub(root_stub(folder))))

    def test_damaged_table_recovered_via_item_tree(self):
        items = [message(), message(), object()]  # last one is not a message and must be skipped
        conv, found = self._iterate(folder_stub(items))
        self.assertEqual(len(found), 2)
        self.assertEqual(conv.recovered_folders, ["Inbox"])
        self.assertEqual(conv.unreadable_folders, [])

    def test_unreadable_folder_is_reported(self):
        conv, found = self._iterate(folder_stub([]))
        self.assertEqual(found, [])
        self.assertEqual(conv.unreadable_folders, ["Inbox"])

    def test_healthy_folder_uses_normal_path(self):
        conv, found = self._iterate(folder_stub([message()], table_ok=True))
        self.assertEqual(len(found), 1)
        self.assertEqual(conv.recovered_folders, [])
        self.assertEqual(conv.unreadable_folders, [])


if __name__ == "__main__":
    unittest.main()
