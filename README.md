# boBnox File Organizer

A modern file organizer with Bento Grid dark UI, built with customtkinter and Geist font.

## Features

- **Bento Grid UI**: Modern dark theme with rounded cards and smooth animations
- **Geist Font**: Clean typography throughout the interface
- **Smart Organization**: Automatically categorizes files by extension into organized folders
- **Dry Run Mode**: Preview changes before moving any files
- **Undo Support**: Restore files to their original locations with one click
- **Recursive Sorting**: Organize files in subdirectories too
- **JSON Configuration**: Customize extension mappings via `~/.config/bobnox/config.json`
- **CLI Tool**: Full command-line interface for scripting and automation
- **Persistent History**: Undo history survives application restarts
- **Automatic Logging**: Every run generates a timestamped log file
- **Duplicate Handling**: Intelligently renames conflicting files
- **Progress Tracking**: Real-time progress bar and status updates

## Quick Install

### One-Line Install (Linux/macOS)

```bash
curl -sSL https://raw.githubusercontent.com/anorak999/boBnox/Home/install.sh | bash
```

This will:
- Clone the repository to `~/.local/share/bobnox`
- Set up a Python virtual environment
- Install all dependencies
- Create CLI commands (`bobnox`, `bobnox-gui`)
- Add a desktop launcher to your applications menu

### Uninstall

```bash
curl -sSL https://raw.githubusercontent.com/anorak999/boBnox/Home/uninstall.sh | bash
```

Or manually:
```bash
rm -rf ~/.local/share/bobnox ~/.local/bin/bobnox ~/.local/bin/bobnox-gui ~/.local/share/applications/bobnox.desktop
```

## Alternative Installation

### Docker with Browser GUI

```bash
./run-docker-vnc.sh
# Open http://localhost:6080/vnc.html
```

### Docker CLI (Headless)

```bash
docker run --rm -v /path/to/folder:/data ghcr.io/anorak999/bobnox:latest organize --path /data
```

### Manual Install

```bash
git clone https://github.com/anorak999/boBnox.git
cd boBnox
pip install -r requirements.txt
python bobnox.py
```

## CLI Usage

After installation, use the `bobnox` command:

```bash
# Organize a folder (dry run first to preview)
bobnox organize --path ~/Downloads --dry-run

# Actually organize
bobnox organize --path ~/Downloads

# Include subdirectories
bobnox organize --path ~/Downloads --recursive

# Undo last organization
bobnox undo

# View configuration
bobnox config --show

# List extension mappings
bobnox config --list-extensions
```

## File Categories

| Category | Extensions |
|----------|------------|
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`, `.tiff`, `.webp`, `.heic` |
| Documents | `.pdf`, `.doc`, `.docx`, `.rtf`, `.odt` |
| Text Documents | `.txt`, `.md` |
| Spreadsheets | `.xls`, `.xlsx`, `.csv` |
| Presentations | `.ppt`, `.pptx` |
| Audio | `.mp3`, `.wav`, `.aac`, `.flac`, `.ogg`, `.m4a` |
| Videos | `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv` |
| Archives | `.zip`, `.rar`, `.7z`, `.tar`, `.gz` |
| Scripts | `.py`, `.js`, `.sh` |
| Web Files | `.html`, `.css` |
| Code | `.java`, `.cpp`, `.c` |
| Executables | `.exe`, `.msi`, `.dmg` |

Unknown file types are automatically grouped into `[EXT] Files` folders.

## GUI Usage

1. **Browse**: Click the **Browse** button to select a folder
2. **Options**: Enable **Dry Run** to preview, or **Include Subdirectories** for recursive sorting
3. **Organize**: Click the organize button to start
4. **Undo**: Click **Undo** to restore files to original locations
5. **Settings**: Click **Settings** to customize extension mappings

### Example

```
Before:
  /Downloads
    ├── photo.jpg
    ├── document.pdf
    ├── song.mp3
    └── video.mp4

After:
  /Downloads
    ├── Images/
    │   └── photo.jpg
    ├── Documents/
    │   └── document.pdf
    ├── Audio/
    │   └── song.mp3
    ├── Videos/
    │   └── video.mp4
    └── bobnox-log-20260628-123456.txt
```

## Configuration

Configuration is stored at `~/.config/bobnox/config.json`:

```json
{
  "extension_map": {
    ".jpg": "Images",
    ".pdf": "Documents",
    ".mp3": "Audio"
  },
  "organize_subdirectories": false,
  "create_log_file": true
}
```

Edit via CLI:
```bash
bobnox config --set organize_subdirectories true
bobnox config --set create_log_file false
```

## Docker Deployment

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

### Build & Publish

```bash
# Create and push a version tag
git tag v2.0.0
git push origin v2.0.0
```

GitHub Actions automatically builds and publishes Docker images.

## Repository Structure

```
bobnox/
├── bobnox.py              # Main GUI application (customtkinter Bento UI)
├── organize_cli.py        # CLI tool
├── install.sh             # One-line installer
├── uninstall.sh           # Uninstaller
├── run-bobnox.sh          # Native launcher
├── run-docker-vnc.sh      # VNC Docker wrapper
├── docker-start-vnc.sh    # VNC startup script
├── bobnox.desktop         # Desktop launcher
├── Dockerfile             # CLI Docker image
├── Dockerfile.vnc         # VNC GUI image
├── requirements.txt       # Python dependencies (customtkinter, cairosvg, Pillow)
├── Geist/                 # Geist font family
├── BoBnox-icon/           # Application icons
├── assets/                # SVG icons
└── .github/workflows/     # CI/CD
```

## Troubleshooting

**SVG icon not showing?**
```bash
pip install --upgrade cairosvg Pillow
```

**CLI command not found?**
```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc or ~/.zshrc for persistence
```

**Docker VNC not accessible?**
- Ensure port 6080 is not in use: `lsof -i :6080`
- Check Docker logs: `docker logs <container-id>`

## License

Open source - feel free to use and modify.

## Contributing

This is a minimal, focused tool. Keep it simple!
