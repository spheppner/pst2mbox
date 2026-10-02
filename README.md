<div align="center">

<img src="assets/icon.png" alt="pst2mbox icon" width="128" height="128">

# pst2mbox

**High-performance, memory-efficient Microsoft Outlook PST & OST to standard mbox converter.**

[![CI](https://github.com/spheppner/pst2mbox/actions/workflows/ci.yml/badge.svg)](https://github.com/spheppner/pst2mbox/actions/workflows/ci.yml)
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
- 🎯 **Interactive & CLI Modes**: Double-click `pst2mbox.exe` for a guided wizard with drag-and-drop support that offers every option the command line has (filters, split, attachments, metadata, dry run, statistics), or use the full command-line interface.
- 🔍 **Advanced Filtering**: Filter by date range (`--from-date`, `--to-date`), folder name (`--folder`), sender (`--sender`), recipient (`--recipient`), or keyword search (`--search`).
- 📁 **Raw Attachment Extraction**: Optionally save binary attachments directly into organized folders on disk (`--extract-attachments`).
- 📊 **Metadata Export & Analytics**: Export email headers and metadata to structured CSV (`--metadata-csv`) or JSON (`--metadata-json`), or view archive statistics without converting (`--stats-only`).
- 🎨 **Full Content Fidelity**: Seamlessly preserves multipart bodies, HTML formatting, plain text, and RTF conversion.
- 🗂️ **Folder Preservation & Splitting**: Retains Outlook folder paths in `X-Folder` headers or splits archives into separate `.mbox` files per folder (`--split-folders`).
- 🛠️ **Orphan Item Recovery**: Optional recovery of unindexed, orphaned, or deleted items (`--include-orphans`).
- 🧪 **Dry-Run Simulation**: Preview conversion operations and counts before writing any files (`--dry-run`).
- 🐍 **Python Library**: Clean, typed API for embedding directly into Python migration scripts.

---

## 🚀 Quick Start

### Option 1: Standalone Windows Executable (No Python Required)

1. Download the latest `pst2mbox.exe` from [Releases](https://github.com/spheppner/pst2mbox/releases) (or build locally via `build_exe.bat`).
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
pst2mbox archive.pst output.mbox

# Split each Outlook folder into its own .mbox file
pst2mbox --split-folders archive.pst ./exported_folders/

# Filter by date range and specific folder
pst2mbox --from-date 2024-01-01 --to-date 2024-12-31 --folder Inbox archive.pst 2024_inbox.mbox

# Search keyword in subject/body and extract raw attachments to disk
pst2mbox --search invoice --extract-attachments ./invoices_attachments/ archive.pst invoices.mbox

# Export metadata table (CSV & JSON)
pst2mbox --metadata-csv report.csv --metadata-json report.json archive.pst output.mbox

# Preview conversion without writing files (dry run)
pst2mbox --dry-run --from-date 2025-01-01 archive.pst output.mbox

# Quickly inspect archive statistics (folders, message counts, sizes)
pst2mbox --stats-only archive.pst

# Include recovered orphan / deleted items
pst2mbox --include-orphans archive.pst output.mbox

# Overwrite output without prompting
pst2mbox -y archive.pst backup.mbox

# Show help & version
pst2mbox --help
pst2mbox --version
```

### Options Reference

| Option | Description |
|---|---|
| `-v`, `--verbose` | Enable detailed debug logging output |
| `-q`, `--quiet` | Suppress non-error progress messages |
| `-y`, `--overwrite` | Overwrite existing output file(s) without interactive confirmation |
| `--split-folders` | Export each PST folder as a separate `.mbox` file in a directory |
| `--include-orphans` | Include recovered orphaned / deleted items if available |
| `--from-date YYYY-MM-DD` | Convert only emails sent on or after this date |
| `--to-date YYYY-MM-DD` | Convert only emails sent on or before this date |
| `--folder <name>` | Convert only emails matching folder name |
| `--sender <query>` | Convert only emails matching sender name or email |
| `--recipient <query>` | Convert only emails matching recipient (To/Cc/Bcc) |
| `--search <keyword>` | Search keyword in subject or body |
| `--extract-attachments <dir>` | Save extracted raw attachments to target directory on disk |
| `--metadata-csv <file>` | Export email metadata table to CSV file |
| `--metadata-json <file>` | Export email metadata table to JSON file |
| `--dry-run` | Simulate conversion without writing output files |
| `--stats-only` | Print PST folder and message statistics without converting |
| `-h`, `--help` | Display usage manual and exit |
| `--version` | Show program version number |

---

## 🐍 Python API Usage

You can use `pst2mbox` as a Python module in your own scripts:

```python
from pathlib import Path
from pst2mbox import PSTToMboxConverter

converter = PSTToMboxConverter(
    pst_file="archive.pst",
    output_file="emails.mbox",
    from_date="2024-01-01",
    folder_filter="Inbox",
    extract_attachments_dir="./attachments/",
    metadata_csv="metadata.csv",
    verbose=True,
    overwrite=True
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

To generate a standalone Windows executable (`dist/pst2mbox.exe` ~7.2 MB):

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

## ⚠️ Disclaimer & Liability

This software is provided **"as is"**, without warranty of any kind, express or implied. **The author takes no liability for lost, damaged or corrupted data, failed or incomplete conversions, or any other direct or indirect damage** resulting from the use of this software. `pst2mbox` only reads your PST/OST file and never modifies it, but you use it entirely at your own risk. **Always keep a backup of your original files** and verify the converted output before deleting anything. See the [LICENSE](LICENSE) for the full terms.

---

## 🙏 Credits & Acknowledgments

This project is a modern continuation and optimization of the original **[PstMboxConverter](https://github.com/Jerome2606/PstMboxConverter)** project by **[Jérôme Lambert](https://github.com/Jerome2606)**.

Special thanks and credit to community contributors whose ideas and PRs helped inspire this version:
- **[LatinRickshaw](https://github.com/LatinRickshaw)** ([PR #8](https://github.com/Jerome2606/PstMboxConverter/pull/8)) — Multi-method attachment extraction and corrupted attribute safety improvements.
- **[JailsCarvalho](https://github.com/JailsCarvalho)** ([PR #13](https://github.com/Jerome2606/PstMboxConverter/pull/13)) — Concept for PST folder hierarchy split export.
- **[victoMR](https://github.com/victoMR)** ([PR #10](https://github.com/Jerome2606/PstMboxConverter/pull/10)) — Advanced filtering (date, folder, sender, search), metadata export (CSV/JSON), raw attachment dump, and PST archive statistics ideas.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
