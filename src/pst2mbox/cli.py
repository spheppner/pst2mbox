"""
CLI entry point for pst2mbox.
"""

import argparse
from pathlib import Path
import sys
import textwrap
from typing import Any, Dict, Optional

from pst2mbox import __version__
from pst2mbox.converter import PSTToMboxConverter, parse_date_arg


DISCLAIMER = (
    "DISCLAIMER: This software is provided \"as is\", without warranty of any kind. "
    "The author takes NO liability for lost, damaged or corrupted data or any other damage "
    "arising from its use. Always keep a backup of your original PST/OST files."
)


def _clean_path(raw: str) -> str:
    return raw.strip().strip("\"'")


def _ask(text: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{text}{suffix}: ").strip()
    return answer if answer else (default or "")


def _ask_path(text: str, default: Optional[str] = None) -> str:
    return _clean_path(_ask(text, default))


def _ask_yes_no(text: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{text} ({hint}): ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "j", "ja"):
            return True
        if answer in ("n", "no", "nein"):
            return False
        print("  Please answer y or n.")


def _ask_date(text: str) -> Optional[str]:
    while True:
        answer = input(f"{text} (YYYY-MM-DD, empty = none): ").strip()
        if not answer:
            return None
        try:
            parse_date_arg(answer)
            return answer
        except ValueError as e:
            print(f"  [!] {e}")


def collect_interactive_options() -> Optional[Dict[str, Any]]:
    """Guide the user through every option the CLI offers. Returns converter kwargs, or None if cancelled."""
    print("What would you like to do?")
    print("  1) Convert PST/OST to mbox")
    print("  2) Show archive statistics only (no conversion)")
    print("  3) Dry run (simulate conversion, write nothing)")
    while True:
        mode = _ask("Choose 1, 2 or 3", "1")
        if mode in ("1", "2", "3"):
            break
        print("  Please enter 1, 2 or 3.")

    opts: Dict[str, Any] = {"stats_only": mode == "2", "dry_run": mode == "3"}

    while True:
        pst_input = _ask_path("Path to input PST/OST file (drag & drop works)")
        if not pst_input:
            print("[!] The input path cannot be empty.")
            continue
        pst_path = Path(pst_input)
        if not pst_path.is_file():
            print(f"[!] File not found: {pst_path}")
            continue
        break
    opts["pst_file"] = pst_path

    if mode == "2":
        opts["verbose"] = _ask_yes_no("Verbose debug output?", False)
        return opts

    opts["split_folders"] = _ask_yes_no("Split into one .mbox file per Outlook folder?", False)
    if opts["split_folders"]:
        default_out = pst_path.with_name(pst_path.stem + "_folders")
        prompt_text = "Output directory for the folder .mbox files"
    else:
        default_out = pst_path.with_suffix(".mbox")
        prompt_text = "Output .mbox file"
    out = _ask_path(prompt_text, None if mode == "3" else str(default_out))
    opts["output_file"] = Path(out) if out else None

    if _ask_yes_no("Configure advanced options (filters, attachments, metadata, ...)?", False):
        print("\n-- Filters (leave empty to skip) --")
        opts["from_date"] = _ask_date("Only emails on or after")
        opts["to_date"] = _ask_date("Only emails on or before")
        opts["folder_filter"] = _ask("Only folders matching name") or None
        opts["sender_filter"] = _ask("Only emails from sender (name or address)") or None
        opts["recipient_filter"] = _ask("Only emails to recipient (name or address)") or None
        opts["search_query"] = _ask("Only emails containing keyword (subject/body)") or None

        print("\n-- Extras (leave empty to skip) --")
        opts["extract_attachments_dir"] = _ask_path("Directory to save raw attachments") or None
        opts["metadata_csv"] = _ask_path("Metadata CSV file") or None
        opts["metadata_json"] = _ask_path("Metadata JSON file") or None

        print("\n-- Behaviour --")
        opts["include_orphans"] = _ask_yes_no("Include recovered orphan/deleted items?", False)
        opts["verbose"] = _ask_yes_no("Verbose debug output?", False)
        opts["quiet"] = _ask_yes_no("Quiet mode (errors only)?", False) if not opts["verbose"] else False

    opts["overwrite"] = _ask_yes_no("Overwrite existing output without asking?", False)

    print()
    if not _ask_yes_no("Start now?", True):
        return None
    return opts


def run_interactive_mode() -> int:
    """Friendly interactive wizard for users who double-click the .exe or run without arguments."""
    print("=" * 62)
    print(f"        pst2mbox v{__version__} - Outlook PST/OST to mbox")
    print("=" * 62)
    print(textwrap.fill(DISCLAIMER, width=62))
    print("=" * 62)
    print()

    success = False
    try:
        opts = collect_interactive_options()
        if opts is not None:
            print()
            try:
                success = PSTToMboxConverter(**opts).convert()
            except Exception as e:
                print(f"\n[ERROR] Conversion error: {e}")
        else:
            print("Cancelled.")
            success = True
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return 0

    print("\nPress Enter to exit...")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass
    return 0 if success else 1


def main(argv=None) -> int:
    """Main CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) == 0 and sys.stdin.isatty():
        return run_interactive_mode()

    parser = argparse.ArgumentParser(
        prog="pst2mbox",
        description="Convert Microsoft Outlook PST / OST files to standard mbox format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  pst2mbox archive.pst output.mbox

  # Split into separate mbox files per Outlook folder
  pst2mbox --split-folders archive.pst ./exported_folders/

  # Date range and folder filtering
  pst2mbox --from-date 2024-01-01 --to-date 2024-12-31 --folder Inbox archive.pst 2024_inbox.mbox

  # Search keyword and export raw attachments to disk
  pst2mbox --search invoice --extract-attachments ./invoices_attachments/ archive.pst invoices.mbox

  # Export metadata table (CSV & JSON)
  pst2mbox --metadata-csv report.csv --metadata-json report.json archive.pst output.mbox

  # PST statistics overview without converting
  pst2mbox --stats-only archive.pst

Disclaimer: provided "as is" without warranty. The author accepts no liability for
lost or damaged data. Always back up your original PST/OST files.
        """,
    )

    parser.add_argument("pst_file", help="Path to input PST or OST file")
    parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Path to output mbox file (or directory if --split-folders). Optional with --stats-only or --dry-run",
    )

    # General conversion flags
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error messages")
    parser.add_argument("-y", "--overwrite", action="store_true", help="Overwrite existing output files without prompting")
    parser.add_argument(
        "--split-folders", action="store_true", help="Split emails into separate mbox files per PST folder"
    )
    parser.add_argument("--include-orphans", action="store_true", help="Include recovered orphan items if available")

    # Filters
    parser.add_argument("--from-date", help="Convert only emails sent on or after this date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="Convert only emails sent on or before this date (YYYY-MM-DD)")
    parser.add_argument("--folder", dest="folder_filter", help="Convert only emails in matching folder name")
    parser.add_argument("--sender", dest="sender_filter", help="Convert only emails matching sender name or email")
    parser.add_argument(
        "--recipient",
        "--to-filter",
        dest="recipient_filter",
        help="Convert only emails matching recipient name or email",
    )
    parser.add_argument("--search", dest="search_query", help="Convert only emails matching keyword in subject or body")

    # Export extras
    parser.add_argument(
        "--extract-attachments",
        dest="extract_attachments_dir",
        help="Directory to save raw extracted attachment files",
    )
    parser.add_argument("--metadata-csv", help="Path to export email metadata as CSV")
    parser.add_argument("--metadata-json", help="Path to export email metadata as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Simulate conversion without writing files")
    parser.add_argument("--stats-only", action="store_true", help="Print PST folder and message statistics without converting")

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args(argv)

    if not args.output_file and not args.stats_only and not args.dry_run and not (args.metadata_csv or args.metadata_json):
        parser.error("the following arguments are required: output_file (unless --stats-only or --dry-run is specified)")

    converter = PSTToMboxConverter(
        pst_file=args.pst_file,
        output_file=args.output_file,
        verbose=args.verbose,
        quiet=args.quiet,
        overwrite=args.overwrite,
        split_folders=args.split_folders,
        include_orphans=args.include_orphans,
        from_date=args.from_date,
        to_date=args.to_date,
        folder_filter=args.folder_filter,
        sender_filter=args.sender_filter,
        recipient_filter=args.recipient_filter,
        search_query=args.search_query,
        extract_attachments_dir=args.extract_attachments_dir,
        metadata_csv=args.metadata_csv,
        metadata_json=args.metadata_json,
        dry_run=args.dry_run,
        stats_only=args.stats_only,
    )

    try:
        success = converter.convert()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n❌ Conversion cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
