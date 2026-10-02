"""
CLI entry point for pst2mbox.
"""

import argparse
from pathlib import Path
import sys

from pst2mbox import __version__
from pst2mbox.converter import PSTToMboxConverter


def run_interactive_mode() -> int:
    """Friendly interactive CLI prompt for users who double-click the .exe or run without arguments."""
    print("=" * 55)
    print(f"        pst2mbox v{__version__} (Portable & High-Performance)")
    print("=" * 55)
    print("Convert Outlook PST/OST files to standard mbox format.")
    print()

    while True:
        try:
            pst_input = input("Enter path to input PST file: ").strip().strip('"\'')
            if not pst_input:
                print("❌ PST file path cannot be empty.")
                continue
            pst_path = Path(pst_input)
            if not pst_path.exists():
                print(f"❌ File not found: {pst_path}")
                continue
            break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return 0

    default_output = pst_path.with_suffix(".mbox")
    try:
        out_input = input(f"Enter path to output mbox file [Default: {default_output.name}]: ").strip().strip('"\'')
        output_path = Path(out_input) if out_input else default_output
    except (KeyboardInterrupt, EOFError):
        output_path = default_output

    print()
    converter = PSTToMboxConverter(pst_path, output_path, verbose=False, overwrite=False)
    try:
        success = converter.convert()
    except Exception as e:
        print(f"\n❌ Conversion error: {e}")
        success = False

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

    # If no arguments provided in interactive terminal, launch guided prompt
    if len(argv) == 0 and sys.stdin.isatty():
        return run_interactive_mode()

    parser = argparse.ArgumentParser(
        prog="pst2mbox",
        description="Convert Microsoft Outlook PST / OST files to standard mbox format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pst2mbox archive.pst output.mbox
  pst2mbox -v "C:\\Users\\User\\Documents\\Outlook.pst" "emails.mbox"
  pst2mbox --split-folders input.pst ./output_folder/
  pst2mbox -y backup.pst converted.mbox
        """,
    )

    parser.add_argument("pst_file", help="Path to input PST or OST file")
    parser.add_argument("output_file", help="Path to output mbox file (or directory if --split-folders)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error messages")
    parser.add_argument("-y", "--overwrite", action="store_true", help="Overwrite existing output files without prompting")
    parser.add_argument(
        "--split-folders", action="store_true", help="Split emails into separate mbox files per PST folder"
    )
    parser.add_argument("--include-orphans", action="store_true", help="Include recovered orphan items if available")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args(argv)

    converter = PSTToMboxConverter(
        pst_file=args.pst_file,
        output_file=args.output_file,
        verbose=args.verbose,
        quiet=args.quiet,
        overwrite=args.overwrite,
        split_folders=args.split_folders,
        include_orphans=args.include_orphans,
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
