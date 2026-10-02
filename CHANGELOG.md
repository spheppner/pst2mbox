# Changelog

All notable changes to `pst2mbox` are documented in this file.

## [2.0.0] - 2026-10-02

### 🚀 Major Improvements & Architecture Refactoring
- **Modern Package Structure**: Migrated codebase to a standard `src/pst2mbox` layout with PEP 517/621 `pyproject.toml` packaging.
- **Unified CLI Tool**: Introduced `pst2mbox` command-line executable and `python -m pst2mbox` module execution.
- **Enhanced Standalone Executable**: Upgraded Windows standalone build script (`build_exe.py` / `build_exe.bat`) generating a compact, zero-dependency ~7.2 MB binary.
- **Streamlined Memory Management**: Optimized message streaming directly from `libpff` C-bindings, keeping RAM usage <50 MB on multi-gigabyte mailboxes.
- **GitHub Actions Node 24 Migration**: Upgraded CI workflows (`actions/checkout@v7`, `actions/setup-python@v7`) to resolve Node 20 deprecation warnings.

### ✨ Advanced Features & PR Community Enhancements
- **Interactive Wizard**: Added interactive guided wizard with drag-and-drop path support when launched with no arguments or double-clicked in Windows Explorer. It exposes every CLI option (convert / stats-only / dry-run, split folders, all filters, attachment extraction, metadata export, orphans, verbose/quiet, overwrite).
- **Application Icon**: New icon embedded in `pst2mbox.exe` and shown in the README (`assets/`).
- **Disclaimer**: Added an explicit no-liability / use-at-your-own-risk notice to the README, `--help` and the interactive wizard.
- **Folder Splitting & Filtering**: Added `--split-folders` to export individual `.mbox` files per Outlook folder (inspired by JailsCarvalho, PR #13) and `--folder` to convert specific folders.
- **Date & Sender Filtering**: Added `--from-date`, `--to-date`, `--sender`, and `--recipient` filtering (inspired by victoMR, PR #10).
- **Keyword Search**: Added `--search` to filter emails matching keywords in subject or body.
- **Raw Attachment Disk Dump**: Added `--extract-attachments <DIR>` to extract binary attachments directly to organized directories on disk.
- **Metadata Export**: Added `--metadata-csv` and `--metadata-json` export options for mail analysis and reporting.
- **Archive Analytics & Dry Run**: Added `--stats-only` to inspect PST folder and message counts without converting, and `--dry-run` to preview conversions.
- **Orphan Item Recovery**: Added `--include-orphans` flag to recover unindexed or deleted Outlook messages.
- **Enhanced Extraction & Robustness**: Multi-method fallback attachment extraction and corrupted attribute safety handling (inspired by LatinRickshaw, PR #8).
- **RFC 2047 & MIME Decoding**: Fully compliant header parsing and decoding for encoded subject lines and international character sets.

### 🧪 CI/CD & Testing
- **Automated GitHub Actions CI**: Multi-OS (Ubuntu, Windows, macOS) matrix tests across Python 3.8 to 3.13.
- **Automated Release Pipeline**: Automated standalone `.exe` and wheel builds on GitHub tag releases.
- **Comprehensive Test Suite**: Unit and integration tests covering filters, metadata export, MIME parsing, headers, attachments, and mbox export.

---

## [1.0.0] - 2025-07-15
- Initial release by Jérôme Lambert (`Jerome2606/PstMboxConverter`).
