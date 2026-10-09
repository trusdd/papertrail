# papertrail

> Local document organizer with OCR search. Your papers never leave your computer.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-MVP-orange)]()
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)]()

Your receipts, contracts, warranties, and medical records are scattered across folders named "Downloads" and "Desktop". **papertrail** turns that chaos into a searchable, private archive — like Google Photos, but for your papers.

![screenshot](docs/screenshot.png)

## Why

There are two kinds of tools for managing documents today:

1. **Cloud services** like Google Drive and Dropbox — convenient, but you're giving a company permanent access to your passport scans and tax returns.
2. **Self-hosted solutions** like Paperless-ngx — powerful and private, but they require Docker, a server running 24/7, and comfort with the command line.

**papertrail is the missing middle.** It runs as a regular desktop app on your laptop, stores its index in a single SQLite file next to your documents, and never sends a single byte over the network.

## Features

- **Full-text search** inside PDFs and images (OCR via Tesseract)
- **100% local** — no cloud, no accounts, no telemetry
- **Russian + English** OCR out of the box
- **Portable archive** — copy the folder with documents, keep the index
- **Incremental indexing** — files are re-scanned only when they change (SHA-256)
- **Simple GUI** — pick a folder, search, double-click to open
- **Tested** — 39 unit tests, no GUI dependencies in the core

## Install

### macOS

    brew install tesseract tesseract-lang poppler python-tk@3.12
    git clone https://github.com/trusdd/papertrail.git
    cd papertrail
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .

### Linux

    sudo apt install tesseract-ocr tesseract-ocr-rus poppler-utils python3-tk
    git clone https://github.com/trusdd/papertrail.git
    cd papertrail
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .

## Usage

Run the app:

    papertrail

Then:

1. Click **"Выбрать папку и проиндексировать"** and pick a folder with your documents.
2. Wait while papertrail runs OCR on each file. The status bar will show progress.
3. Type anything in the **search box** — results update live as you type.
4. **Double-click** any row to open the file in your default app.

The index is stored in `~/papertrail.db`. Your documents themselves stay where they are — papertrail never moves or modifies them.

## How it works

    papertrail/
    ├── src/papertrail/
    │   ├── db.py         # SQLite schema and queries
    │   ├── scanner.py    # folder walker + SHA-256 change detection
    │   ├── ocr.py        # Tesseract wrapper (PDF and images)
    │   ├── indexer.py    # glue: scan → OCR → upsert
    │   └── app.py        # Tkinter GUI
    └── tests/            # 39 tests, all mocked (no real Tesseract needed)

**Design principles:**

- **No cloud, ever.** The app has no networking code.
- **The index is yours.** A single SQLite file you can back up or move.
- **Incremental by default.** Files are hashed and re-indexed only when changed.
- **OCR is replaceable.** The `ocr.py` module is a thin wrapper — swap Tesseract for something else later.

## Roadmap

- [x] SQLite index and document model
- [x] Folder scanner with hash-based change detection
- [x] OCR via Tesseract (Russian + English)
- [x] Tkinter GUI with live search
- [x] Human-readable date formatting
- [ ] Drag-and-drop a folder onto the window
- [ ] Auto-categorization (invoice, contract, receipt) by keywords
- [ ] Thumbnail previews instead of plain table
- [ ] Packaged `.dmg` for macOS (no Python install required)
- [ ] Windows and Linux builds
- [ ] Multi-language OCR (German, French, Spanish)
- [ ] Encrypted index (optional password)

## Contributing

Issues and pull requests are welcome. If you're planning a big change, please open an issue first to discuss.

    pytest -v
    papertrail

## License

MIT — see [LICENSE](LICENSE).
