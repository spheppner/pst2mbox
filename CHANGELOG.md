# Changelog

All notable changes to `pst2mbox` are documented in this file.

## [2.0.0] - 2026-10-02

### 🚀 Major Improvements & Architecture Refactoring
- **Modern Package Structure**: Migrated codebase to a standard `src/pst2mbox` layout with PEP 517/621 `pyproject.toml` packaging.
- **Unified CLI Tool**: Introduced `pst2mbox` command-line executable and `python -m pst2mbox` module execution.
- **Enhanced Standalone Executable**: Upgraded Windows standalone build script (`build_exe.py` / `build_exe.bat`) generating a compact, zero-dependency ~7 MB binary.
- **Streamlined Memory Management**: Optimized message streaming directly from `libpff` C-bindings, keeping RAM usage <50 MB on multi-gigabyte mailboxes.

### ✨ Features
- **Interactive Wizard**: Added interactive guided wizard with drag-and-drop path support when launched with no arguments or double-clicked in Windows Explorer.
- **Folder Splitting**: Added `--split-folders` to export individual `.mbox` files per Outlook folder with path sanitization.
- **Orphan Item Recovery**: Added `--include-orphans` flag to recover unindexed or deleted Outlook messages.
- **RFC 2047 & MIME Decoding**: Fully compliant header parsing and decoding for encoded subject lines and international character sets.
- **Fidelity Preservation**: Enhanced support for multipart HTML/plain text alternative bodies and RTF body extraction.
- **Attachment Extraction**: Full binary payload extraction with sanitized filenames and automatic MIME type inference.

### 🧪 CI/CD & Testing
- **Automated GitHub Actions CI**: Added multi-OS (Ubuntu, Windows, macOS) matrix tests across Python 3.8 to 3.13.
- **Automated Release Pipeline**: Added automated standalone `.exe` and wheel builds on GitHub tag releases.
- **Comprehensive Test Suite**: Added complete unit and integration tests covering MIME parsing, headers, attachments, and mbox export.

---

## [1.0.0] - 2025-07-15
- Initial release with basic PST to mbox conversion.
