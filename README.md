# boBnox

![Build status](https://img.shields.io/github/actions/workflow/status/anorak999/boBnox/ci.yml?style=for-the-badge&logo=githubactions&logoColor=white&label=CI) ![GitHub stars](https://img.shields.io/github/stars/anorak999/boBnox?style=for-the-badge&logo=github) ![GitHub forks](https://img.shields.io/github/forks/anorak999/boBnox?style=for-the-badge&logo=github) ![GitHub issues](https://img.shields.io/github/issues/anorak999/boBnox?style=for-the-badge&logo=github) ![Last commit](https://img.shields.io/github/last-commit/anorak999/boBnox?style=for-the-badge&logo=github) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

## 📑 Table of Contents

- [Description](#description)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Uninstallation](#uninstallation)
- [CLI Usage](#cli-usage)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 📝 Description

boBnox — a modern file organizer with Bento Grid dark UI, built with customtkinter and Geist font. Automatically sorts files into categorized folders with advanced deduplication, entropy analysis, and inotify daemon support.

## ✨ Features

- **Smart Organization**: Automatically categorizes files by extension into organized folders
- **Dry Run Mode**: Preview changes before moving any files
- **Undo Support**: Restore files to their original locations with one click
- **Recursive Sorting**: Organize files in subdirectories
- **JSON Configuration**: Customize extension mappings via `~/.config/bobnox/config.json`
- **CLI Tool**: Full command-line interface for scripting and automation
- **MIME Sorting**: Content-based file classification using magic bytes
- **Entropy Analysis**: Detect encrypted/random files and quarantine them
- **Deduplication**: SHA-256 hash-based duplicate detection with reflink support
- **inotify Daemon**: Real-time file system monitoring
- **SQLite Ledger**: Transactional rollback with ACID compliance
- **POSIX Guard**: Symlink/root/dotfile quarantine
- **GTK Conflict Resolution**: Zenity-based collision handling
- **Theme Toggle**: Light/Dark mode with animated transitions

## ⚡ Quick Start

### One-Line Install (Linux/macOS)

```bash
curl -sSL https://raw.githubusercontent.com/anorak999/boBnox/Home/install.sh | bash
```

### One-Line Uninstall

```bash
curl -sSL https://raw.githubusercontent.com/anorak999/boBnox/Home/uninstall.sh | bash
```

### Manual Install

```bash
# Clone the repository
git clone https://github.com/anorak999/boBnox.git
cd boBnox

# Create & activate a virtualenv
python3 -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python bobnox.py
```

## 📦 Installation

### Requirements

- Python 3.10+
- pip
- git
- zenity (Linux, for folder picker)

### Dependencies

```
customtkinter
cairosvg
Pillow
python-magic
inotify-simple
```

### Desktop Integration

After installation, the app is available as:
- **GUI**: `bobnox-gui` command or search "BoBnox" in your apps
- **CLI**: `bobnox organize --path /path/to/folder`
- **Config**: `bobnox config --show`

## 🗑️ Uninstallation

```bash
# One-line uninstall
curl -sSL https://raw.githubusercontent.com/anorak999/boBnox/Home/uninstall.sh | bash

# Or manually
rm -rf ~/.local/share/bobnox ~/.local/bin/bobnox ~/.local/bin/bobnox-gui ~/.local/share/applications/bobnox.desktop
```

## 🖥️ CLI Usage

```bash
# Organize a folder (dry run first to preview)
bobnox organize --path ~/Downloads --dry-run

# Actually organize
bobnox organize --path ~/Downloads

# Include subdirectories
bobnox organize --path ~/Downloads --recursive

# Use MIME-based sorting
bobnox organize --path ~/Downloads --use-mime

# Scan for duplicates
bobnox organize --path ~/Downloads --dedup

# Run in daemon mode (auto-organize new files)
bobnox organize --path ~/Downloads --daemon

# Undo last operation
bobnox undo

# View configuration
bobnox config --show
bobnox config --list-extensions
```

## 🛠️ Tech Stack

- 🐳 **Docker** — Containerized deployment
- 🐍 **Python** — Core language
- 🖼️ **customtkinter** — Modern GUI framework
- 🔤 **Geist Font** — Clean typography
- 🗄️ **SQLite** — Transactional ledger
- 🐧 **inotify** — Linux file system monitoring

## 📁 Project Structure

```
boBnox/
├── bobnox.py              # Main application (GUI + engines)
├── organize_cli.py        # CLI entry point
├── install.sh             # One-line installer
├── uninstall.sh           # Uninstaller
├── requirements.txt       # Python dependencies
├── Geist/                 # Geist font family
├── BoBnox-icon/           # Application icons
├── assets/                # SVG icons
├── Dockerfile             # CLI Docker image
├── Dockerfile.vnc         # VNC GUI image
├── .github/workflows/     # CI/CD
└── README.md
```

## 🚢 Deployment

### Docker CLI

```bash
docker pull ghcr.io/anorak999/bobnox:latest
docker run --rm -v /path/to/folder:/data ghcr.io/anorak999/bobnox:latest organize --path /data
```

### Docker with GUI (VNC)

```bash
docker build -f Dockerfile.vnc -t bobnox-vnc .
docker run --rm -p 6080:6080 -v $HOME:$HOME bobnox-vnc
# Open http://localhost:6080/vnc.html
```

## 👥 Contributing

Contributions are welcome! Here's the standard flow:

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/anorak999/boBnox.git`
3. **Branch**: `git checkout -b feature/your-feature`
4. **Commit**: `git commit -m 'feat: add some feature'`
5. **Push**: `git push origin feature/your-feature`
6. **Open** a pull request

Please follow the existing code style and include tests for new behavior where applicable.
