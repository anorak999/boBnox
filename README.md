<div align="center">

# boBnox

**A file organization engine built with Python.**

![Version](https://img.shields.io/badge/version-4.2.0-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Docker](https://img.shields.io/badge/docker-enabled-2496ED?style=flat-square&logo=docker&logoColor=white)

<br>

<img src="BoBnox-icon/Bobnox-icon.png" width="120" alt="boBnox icon">

<br>

Automatic file sorting. Deduplication. Entropy analysis. One command.

</div>

---

## What it does

boBnox scans a directory, reads file metadata and content signatures, then moves each file into a categorized folder. It handles conflicts, tracks every move in a SQLite ledger, and can undo everything.

## Features

| Feature | Description |
|---------|-------------|
| Smart sorting | Categorizes files by extension or MIME type into organized folders |
| Dry run | Preview all moves before touching any files |
| Undo | Roll back any number of previous operations via SQLite ledger |
| Deduplication | SHA-256 hash-based duplicate detection with reflink support |
| Entropy filter | Detects encrypted or random data files and quarantines them |
| MIME validation | Content-based routing using magic bytes, not just extensions |
| inotify daemon | Watches directories and auto-organizes new files in real time |
| Regex templates | Custom destination patterns with date, extension, and filename tokens |
| Light/Dark theme | Toggle between themes with a single switch |

## Quick start

```bash
# Install
curl -sSL https://raw.githubusercontent.com/Himath-Rajapaksha/boBnox/Home/install.sh | bash

# Launch GUI
bobnox-gui

# Or use CLI
bobnox organize ~/Downloads --dry-run
```

## Manual setup

```bash
git clone https://github.com/Himath-Rajapaksha/boBnox.git
cd boBnox
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python bobnox.py
```

### Requirements

- Python 3.10+
- zenity (Linux, for folder picker dialog)

### Dependencies

```
customtkinter
cairosvg
Pillow
python-magic
inotify-simple
```

## CLI

```bash
# Organize with preview
bobnox organize ~/Downloads --dry-run

# Organize for real
bobnox organize ~/Downloads

# Include subdirectories
bobnox organize ~/Downloads --recursive

# MIME-based sorting
bobnox organize ~/Downloads --use-mime

# Scan duplicates
bobnox organize ~/Downloads --dedup

# Watch mode (auto-organize new files)
bobnox organize ~/Downloads --daemon

# Undo last batch
bobnox undo

# Show config
bobnox config --show
```

## Configuration

Extension mappings live at `~/.config/bobnox/config.json`. Edit directly or use the Settings dialog in the GUI.

```json
{
  "extension_map": {
    ".pdf": "Documents",
    ".jpg": "Images",
    ".mp4": "Videos"
  },
  "organize_subdirectories": false,
  "dark_mode": true
}
```

## Project structure

```
bobnox.py           # GUI + CLI + all engines (single file)
organize_cli.py     # CLI entry point
requirements.txt    # Python dependencies
Geist/              # Font assets
BoBnox-icon/        # App icon
assets/             # SVG assets
install.sh          # One-line installer
uninstall.sh        # Uninstaller
packaging/          # deb/rpm build scripts
Dockerfile          # CLI container
Dockerfile.vnc      # GUI container (VNC)
```

## Docker

```bash
# CLI mode
docker run --rm -v ~/Downloads:/data ghcr.io/Himath-Rajapaksha/bobnox:latest organize --path /data

# GUI mode (VNC)
docker build -f Dockerfile.vnc -t bobnox-vnc .
docker run --rm -p 6080:6080 -v $HOME:$HOME bobnox-vnc
# Open http://localhost:6080/vnc.html
```

## Uninstall

```bash
curl -sSL https://raw.githubusercontent.com/Himath-Rajapaksha/boBnox/Home/uninstall.sh | bash
```

## Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feature/your-feature`)
3. Commit (`git commit -m 'feat: add feature'`)
4. Push and open a PR

---

<div align="center">

Built with Python. Runs anywhere.

</div>
