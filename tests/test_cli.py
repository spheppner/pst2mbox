"""
Unit tests for pst2mbox CLI.
"""

import unittest
from unittest.mock import patch
from pathlib import Path

from pst2mbox.cli import collect_interactive_options, main


class TestCLI(unittest.TestCase):
    def test_help_flag(self):
        with patch("sys.stdout"):
            with self.assertRaises(SystemExit) as cm:
                main(["--help"])
            self.assertEqual(cm.exception.code, 0)

    def test_version_flag(self):
        with patch("sys.stdout"):
            with self.assertRaises(SystemExit) as cm:
                main(["--version"])
            self.assertEqual(cm.exception.code, 0)

    def test_missing_arguments(self):
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                main(["input_only.pst"])
            self.assertNotEqual(cm.exception.code, 0)

    @patch("pst2mbox.cli.PSTToMboxConverter.convert")
    def test_valid_conversion_invocation(self, mock_convert):
        mock_convert.return_value = True
        code = main(["input.pst", "output.mbox", "-y", "-q"])
        self.assertEqual(code, 0)
        self.assertTrue(mock_convert.called)

    @patch("pst2mbox.cli.PSTToMboxConverter.convert")
    def test_stats_only_invocation(self, mock_convert):
        mock_convert.return_value = True
        code = main(["input.pst", "--stats-only"])
        self.assertEqual(code, 0)
        self.assertTrue(mock_convert.called)

    @patch("pst2mbox.cli.PSTToMboxConverter.convert")
    def test_filters_and_export_flags(self, mock_convert):
        mock_convert.return_value = True
        code = main([
            "input.pst",
            "output.mbox",
            "--from-date", "2024-01-01",
            "--to-date", "2024-12-31",
            "--folder", "Inbox",
            "--sender", "boss@company.com",
            "--search", "urgent",
            "--metadata-csv", "meta.csv",
            "--extract-attachments", "./atts/",
            "--dry-run"
        ])
        self.assertEqual(code, 0)
        self.assertTrue(mock_convert.called)


class TestInteractiveWizard(unittest.TestCase):
    def test_wizard_collects_all_options(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            pst = Path(tmp) / "a.pst"
            pst.write_bytes(b"x")
            answers = [
                "1", str(pst),          # mode, input
                "n", "out.mbox",        # split folders, output
                "y",                    # advanced
                "2024-01-01", "2024-12-31", "Inbox", "boss@x.com", "me@x.com", "invoice",
                "atts", "m.csv", "m.json",
                "y", "y",               # orphans, verbose
                "y",                    # overwrite
                "y",                    # start
            ]
            with patch("builtins.input", side_effect=answers), patch("builtins.print"):
                opts = collect_interactive_options()
        self.assertEqual(opts["from_date"], "2024-01-01")
        self.assertEqual(opts["to_date"], "2024-12-31")
        self.assertEqual(opts["folder_filter"], "Inbox")
        self.assertEqual(opts["sender_filter"], "boss@x.com")
        self.assertEqual(opts["recipient_filter"], "me@x.com")
        self.assertEqual(opts["search_query"], "invoice")
        self.assertEqual(opts["extract_attachments_dir"], "atts")
        self.assertEqual(opts["metadata_csv"], "m.csv")
        self.assertEqual(opts["metadata_json"], "m.json")
        self.assertTrue(opts["include_orphans"])
        self.assertTrue(opts["overwrite"])
        self.assertFalse(opts["split_folders"])

    def test_wizard_stats_only(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            pst = Path(tmp) / "a.pst"
            pst.write_bytes(b"x")
            with patch("builtins.input", side_effect=["2", str(pst), "n"]), patch("builtins.print"):
                opts = collect_interactive_options()
        self.assertTrue(opts["stats_only"])

    def test_wizard_cancel(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            pst = Path(tmp) / "a.pst"
            pst.write_bytes(b"x")
            answers = ["1", str(pst), "n", "", "n", "n", "n"]
            with patch("builtins.input", side_effect=answers), patch("builtins.print"):
                self.assertIsNone(collect_interactive_options())


if __name__ == "__main__":
    unittest.main()
