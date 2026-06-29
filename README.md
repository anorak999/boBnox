# boBnox

![Build status](https://img.shields.io/github/actions/workflow/status/anorak999/boBnox/ci.yml?style=for-the-badge&logo=githubactions&logoColor=white&label=CI) ![GitHub stars](https://img.shields.io/github/stars/anorak999/boBnox?style=for-the-badge&logo=github) ![GitHub forks](https://img.shields.io/github/forks/anorak999/boBnox?style=for-the-badge&logo=github) ![GitHub issues](https://img.shields.io/github/issues/anorak999/boBnox?style=for-the-badge&logo=github) ![Last commit](https://img.shields.io/github/last-commit/anorak999/boBnox?style=for-the-badge&logo=github) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Download & Install](#download--install)
- [Building Packages](#building-packages)
- [CLI Usage](#cli-usage)
- [API Server](#api-server)
- [Development](#development)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

## Description

boBnox — a modern file organizer with a Vue.js frontend, Python FastAPI backend, and Electron desktop shell. Automatically sorts files into categorized folders with advanced deduplication, entropy analysis, and inotify daemon support.

## Features

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
- **Conflict Resolution**: Smart rename, overwrite, or skip on collisions
- **Vue.js Frontend**: Smooth Bento Grid dark UI with WebSocket real-time updates
- **Electron Desktop**: Cross-platform desktop app (Linux, Windows, macOS)

## Download & Install

### deb Package (Debian/Ubuntu)

```bash
# Download the latest .deb from releases
wget https://github.com/anorak999/boBnox/releases/download/v5.0.0/bobnox_5.0.0-1_all.deb

# Install
sudo dpkg -i bobnox_5.0.0-1_all.deb
sudo apt-get install -f  # fix any missing dependencies
```

### rpm Package (Fedora/RHEL)

```bash
# Download the latest .rpm from releases
wget https://github.com/anorak999/boBnox/releases/download/v5.0.0/bobnox-5.0.0-1.noarch.rpm

# Install
sudo rpm -i bobnox-5.0.0-1.noarch.rpm
```

### pip Install (any platform)

```bash
pip install git+https://github.com/anorak999/boBnox.git
```

### One-Line Install (Linux/macOS)

```bash
curl -sSL https://raw.githubusercontent.com/anorak999/boBnox/Home/install.sh | bash
```

### One-Line Uninstall

```bash
curl -sSL https://github.com/anorak999/boBnox/raw/Home/uninstall.sh | bash
```

## Building Packages

### Prerequisites

```bash
# Debian/Ubuntu
sudo apt install fakeroot python3 python3-pip nodejs npm

# Fedora/RHEL
sudo dnf install fakeroot python3 python3-pip nodejs npm
```

### Build deb Package

```bash
cd boBnox
python3 packaging/build_deb.py --stage packaging/stage --output packaging/build --version 5.0.0
# Output: packaging/build/bobnox_5.0.0-1_all.deb
```

### Build rpm Package

```bash
cd boBnox
python3 packaging/build_rpm.py --stage packaging/stage --output packaging/build --version 5.0.0
# Output: packaging/build/bobnox-5.0.0-1.noarch.rpm
```

### Build Both with build-package.sh

```bash
./packaging/build-package.sh
# Creates both .deb and .rpm in packaging/build/
```

### Push Packages to GitHub Release

```bash
# Tag the release
git tag -a v5.0.0 -m "v5.0.0 release"
git push origin v5.0.0

# Create release and upload packages
gh release create v5.0.0 \
  packaging/build/bobnox_5.0.0-1_all.deb \
  packaging/build/bobnox-5.0.0-1.noarch.rpm \
  --title "v5.0.0" \
  --notes "Vue.js frontend, FastAPI backend, Electron desktop"
```

## CLI Usage

```bash
# Organize a folder (dry run first to preview)
bobnox organize ~/Downloads --dry-run

# Actually organize
bobnox organize ~/Downloads

# Include subdirectories
bobnox organize ~/Downloads --recursive

# Use MIME-based sorting
bobnox organize ~/Downloads --use-mime

# Scan for duplicates
bobnox dedup ~/Downloads

# Run in daemon mode (auto-organize new files)
bobnox organize ~/Downloads --daemon

# Undo last operation
bobnox undo

# View configuration
bobnox config --show
bobnox config --list-extensions
```

## API Server

Start the FastAPI backend server:

```bash
python3 -m backend.server
# API: http://localhost:8420
# Docs: http://localhost:8420/docs
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/version` | Get app version |
| GET | `/api/config` | Get configuration |
| PUT | `/api/config` | Update configuration |
| POST | `/api/organize` | Start organize job |
| GET | `/api/organize/{id}` | Get job status |
| POST | `/api/undo` | Undo last operation |
| POST | `/api/dedup/scan` | Scan for duplicates |
| GET | `/api/ledger/history` | Get operation history |
| GET | `/api/ledger/count` | Get pending count |
| POST | `/api/daemon/start` | Start inotify watcher |
| POST | `/api/daemon/stop` | Stop watcher |
| GET | `/api/directory/list` | Browse directories |
| WS | `/ws/events` | Real-time progress/logs |

## Development

### Run in Dev Mode

```bash
# Start both backend + frontend with hot reload
./run-web.sh

# Or manually:
python3 -m backend.server &    # API on :8420
cd frontend && npm run dev     # Frontend on :5173
```

### Build Electron App

```bash
cd frontend
npm install
npm run electron:build
```

## Tech Stack

- **Vue 3** + TypeScript — Frontend UI
- **Pinia** — State management
- **Tailwind CSS** — Styling
- **FastAPI** — Python REST API
- **WebSocket** — Real-time updates
- **Electron** — Desktop shell
- **SQLite** — Transactional ledger
- **inotify** — Linux file system monitoring

## Project Structure

```
boBnox/
├── bobnox.py              # Pure backend (no GUI dependencies)
├── backend/               # FastAPI API server
│   ├── server.py          # REST + WebSocket endpoints
│   └── models.py          # Pydantic request/response models
├── frontend/              # Vue.js + Electron app
│   ├── electron/          # Electron main process
│   └── src/
│       ├── components/    # Vue components (Bento Grid layout)
│       ├── stores/        # Pinia state management
│       └── composables/   # API + WebSocket hooks
├── packaging/             # deb/rpm build scripts
│   ├── build-package.sh   # Build both packages
│   ├── build_deb.py       # Debian package builder
│   └── build_rpm.py       # RPM package builder
├── Geist/                 # Geist font family
├── BoBnox-icon/           # Application icons
├── assets/                # SVG icons
├── install.sh             # One-line installer
├── uninstall.sh           # Uninstaller
├── run-web.sh             # Dev launcher (backend + frontend)
└── requirements.txt       # Python dependencies
```

## Contributing

Contributions are welcome! Here's the standard flow:

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/anorak999/boBnox.git`
3. **Branch**: `git checkout -b feature/your-feature`
4. **Commit**: `git commit -m 'feat: add some feature'`
5. **Push**: `git push origin feature/your-feature`
6. **Open** a pull request

Please follow the existing code style and include tests for new behavior where applicable.
