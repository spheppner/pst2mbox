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


if __name__ == "__main__":
    unittest.main()
