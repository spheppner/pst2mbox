"""
Unit tests for pst2mbox CLI.
"""

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

from pst2mbox.cli import main


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


if __name__ == "__main__":
    unittest.main()
