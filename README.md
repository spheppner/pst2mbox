<div align="center">

# pst2mbox

**High-performance, memory-efficient Microsoft Outlook PST & OST to standard mbox converter.**

[![CI](https://github.com/pst2mbox/pst2mbox/actions/workflows/ci.yml/badge.svg)](https://github.com/pst2mbox/pst2mbox/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

</div>

---

`pst2mbox` converts Microsoft Outlook **PST** and **OST** archives into standard **mbox** format (RFC 4155 / RFC 2822). It handles large multi-gigabyte mailboxes with minimal memory consumption, preserves full email fidelity (HTML, plain text, RTF, attachments, headers, folder hierarchies), and comes with a **zero-dependency portable Windows executable**.

---

## ✨ Key Features

- ⚡ **Ultra-Low Memory & Fast Streaming**: Streams messages directly via `libpff` C-bindings (<50 MB RAM even for 50GB+ PST files).
- 📦 **Standalone Windows Binary**: Runs out-of-the-box on Windows 10/11 with no Python or dependencies required.
- 🎯 **Interactive & CLI Modes**: Double-click `pst2mbox.exe` for a guided wizard with drag-and-drop support, or use the full command-line interface.
- 🎨 **Full Content Fidelity**: Seamlessly preserves multipart bodies, HTML formatting, plain text, and RTF conversion.
- 📎 **Binary Attachments**: Reliably extracts and embeds documents, images, PDFs, inline CID attachments, and MIME types.
- 🗂️ **Folder Preservation & Splitting**: Retains Outlook folder paths in `X-Folder` headers or splits archives into separate `.mbox` files per folder (`--split-folders`).
- 🔍 **Orphan Item Recovery**: Optional recovery of unindexed, orphaned, or deleted items (`--include-orphans`).
- 🐍 **Python Library**: Clean and typed API for embedding directly into Python migration scripts.

---

## 🚀 Quick Start

### Option 1: Standalone Windows Executable (No Python Required)

1. Download the latest `pst2mbox.exe` from [Releases](https://github.com/pst2mbox/pst2mbox/releases) (or build locally via `build_exe.bat`).
2. **Interactive**: Double-click `pst2mbox.exe`, drag and drop your `.pst` file into the prompt, and press **Enter**.
3. **Command Line**:
   ```cmd
   pst2mbox.exe "C:\Users\Name\Documents\Outlook.pst" "C:\Users\Name\Documents\archive.mbox"
   ```

### Option 2: Python Package (All Platforms)

Install directly using `pip`:

```bash
pip install .
```

Or for development / testing:

```bash
pip install -e ".[dev,build]"
```

---

## 💻 Command-Line Usage

```bash
# Basic conversion (single output mbox)
pst2mbox input.pst output.mbox

# Overwrite output file without confirmation
pst2mbox -y archive.pst backup.mbox

# Split each Outlook folder into its own .mbox file
pst2mbox --split-folders archive.pst ./exported_folders/

# Verbose debug logging
pst2mbox -v input.pst output.mbox

# Quiet mode (errors only)
pst2mbox -q input.pst output.mbox

# Include recovered orphan / deleted items
pst2mbox --include-orphans input.pst output.mbox

# Show help & version
pst2mbox --help
pst2mbox --version
```

### Options Reference

| Flag | Long Option | Description |
|---|---|---|
| `-v` | `--verbose` | Enable detailed debug logging output |
| `-q` | `--quiet` | Suppress non-error progress messages |
| `-y` | `--overwrite` | Overwrite existing output file(s) without interactive confirmation |
| | `--split-folders` | Export each PST folder as a separate `.mbox` file in a directory |
| | `--include-orphans` | Include recovered orphaned / deleted items if available |
| `-h` | `--help` | Display usage manual and exit |
| | `--version` | Show program version number |

---

## 🐍 Python API Usage

You can use `pst2mbox` as a Python module in your own scripts:

```python
from pathlib import Path
from pst2mbox import PSTToMboxConverter

converter = PSTToMboxConverter(
    pst_file="archive.pst",
    output_file="emails.mbox",
    verbose=True,
    overwrite=True,
    split_folders=False,
    include_orphans=False
)

success = converter.convert()
if success:
    print(f"Successfully converted {converter.processed_emails} emails!")
    print(f"Attachments extracted: {converter.attachments_extracted}")
```

---

## 📬 Importing `.mbox` Files into Email Clients

Once converted, your `.mbox` file is compatible with standard email clients:

- **Mozilla Thunderbird**: 
  - Install the *ImportExportTools NG* add-on, right-click any local folder, and select **ImportExportTools NG > Import mbox file**.
  - Or use Thunderbird's built-in **Tools > Import > Mail**.
- **Apple Mail (macOS)**: 
  - Choose **File > Import Mailboxes...**, select **Files in mbox format**, and choose your `.mbox` file.
- **Gmail / Google Workspace**: 
  - Configure your Gmail account via IMAP in Thunderbird or Apple Mail, then drag and drop the imported local folders into your Gmail account.
- **Microsoft 365 / Exchange**: 
  - Import the `.mbox` into Thunderbird configured with your Exchange IMAP account and move messages to your server folders.

---

## 🛠️ Building the Standalone Executable

To generate a standalone Windows executable (`dist/pst2mbox.exe` ~7 MB):

### Automatic (Windows Batch)
Double-click `build_exe.bat`.

### Manual (CLI)
```cmd
python build_exe.py
```

---

## 🧪 Testing & Development

Run the test suite using `pytest`:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
