# Changelog

All notable changes to `pst2mbox` are documented in this file.

## [2.0.2] - 2026-10-05

### 🐛 Bug Fixes
- **`surrogates not allowed` failures**: Emoji in RTF-only messages (and corrupt `&#55xxx;` entities in some HTML) produced unpaired UTF-16 surrogates that cannot be encoded as UTF-8, so the whole message was dropped. Surrogate pairs are now joined into the real character; lone surrogates become `�`.
- **`header value appears to contain an embedded header` failures**: Some PSTs store the entire MIME message as transport headers. The header parser read past the end of the header block and merged `Subject`/`To`/`Date` lines of attached (forwarded) mails into the outer message, which made writing it fail. Parsing now stops at the end of the header block, single-value headers use their first occurrence, and line breaks are stripped from all header values.
- **Raw RTF source as message body**: When an RTF body contained a byte undefined in its code page, `striprtf` raised and the unconverted RTF markup was written as the body. Undecodable bytes are now replaced instead.

## [2.0.1] - 2026-10-02

### 🐛 Bug Fixes
- **Silently skipped folders (data loss)**: A folder whose message table is damaged (libpff: `invalid table index offset value out of bounds`) was treated as empty, so e.g. an entire Inbox could be missing from the output while the run reported success. Such errors are no longer swallowed.
- **Automatic recovery of damaged folders**: When a folder's message table cannot be read, messages are now recovered through libpff's independent item tree. On a 10 GB PST this recovered an Inbox of ~15,400 messages that v2.0.0 dropped.
- **Honest reporting**: Unreadable folders and failed messages are logged as errors, listed in the final summary ("COMPLETED WITH WARNINGS - OUTPUT IS INCOMPLETE"), shown by `--stats-only`, and make the exit code non-zero. Recovered folders are listed as warnings.
- **Console encoding crash**: Fixed `UnicodeEncodeError` on Windows consoles using legacy code pages by forcing UTF-8 output.

---

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
