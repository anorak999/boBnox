# boBnox File Organizer

A minimal, elegant file organizer with a dark theme UI that automatically sorts files into categorized folders.

## ✨ Features

- **Smart Organization**: Automatically categorizes files by extension into organized folders
- **Elegant Interface**: Clean, minimal 480×360 dark-themed window
- **SVG Icon Button**: Beautiful vector icon for the organize action
- **Automatic Logging**: Every run generates a timestamped log file
- **Duplicate Handling**: Intelligently renames conflicting files
- **Progress Tracking**: Real-time progress bar and status updates
- **Thread-Safe**: Non-blocking UI with background processing
- **Multiple Deployment Options**: Run natively, in Docker CLI, or Docker with browser GUI

## 📂 File Categories

- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`, `.tiff`, `.webp`, `.heic`
- **Documents**: `.pdf`, `.doc`, `.docx`, `.rtf`, `.odt`
- **Text Documents**: `.txt`, `.md`
- **Spreadsheets**: `.xls`, `.xlsx`, `.csv`
- **Presentations**: `.ppt`, `.pptx`
- **Audio**: `.mp3`, `.wav`, `.aac`, `.flac`, `.ogg`, `.m4a`
- **Videos**: `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv`
- **Archives**: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`
- **Scripts**: `.py`, `.js`, `.sh`
- **Web Files**: `.html`, `.css`
- **Code**: `.java`, `.cpp`, `.c`
- **Executables**: `.exe`, `.msi`, `.dmg`

Unknown file types are automatically grouped into `[EXT] Files` folders.

## 🚀 Quick Start

### Option 1: Run Directly (Recommended)

```bash
# Clone the repository
git clone https://github.com/anorak999/boBnox.git
cd boBnox

# Run the launcher script
./run-bobnox.sh
```

The GUI will open automatically!

### Option 2: Docker with Browser GUI

```bash
# Run with VNC (web-based GUI)
./run-docker-vnc.sh
```

Then open: **http://localhost:6080/vnc.html**

### Option 3: Docker CLI (Headless)

```bash
# Organize a folder
docker run --rm -v /path/to/folder:/data ghcr.io/anorak999/bobnox:latest --path /data
```

## 💻 Installation & Usage

### Native Installation

#### Prerequisites

```bash
# Python 3.7+
python --version
```

#### Install Dependencies

```bash
pip install cairosvg Pillow
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

#### Run the Application

```bash
# Using the launcher script (easiest)
./run-bobnox.sh

# Or directly with Python
python bobnox.py
```

#### Desktop Integration (Optional)

Install as a desktop application:

```bash
cp bobnox.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/bobnox.desktop
```

Now launch from your application menu by searching "boBnox"!

### Steps

1. **Browse**: Click the **Browse** button to select a folder to organize
2. **Organize**: Click the SVG icon button to start organizing
3. **Wait**: Watch the progress bar as files are sorted
4. **Done**: Files are now organized into categorized subfolders
5. **Log**: Check the timestamped log file (`bobnox-log-YYYYMMDD-HHMMSS.txt`) in the organized folder

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
    └── bobnox-log-20251104-143015.txt
```

## � Docker Deployment

### Docker CLI (Headless)

Run boBnox in a container for automation and scripting:

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/anorak999/bobnox:latest

# Organize a folder
docker run --rm -v /path/to/folder:/data ghcr.io/anorak999/bobnox:latest --path /data
```

**Build locally:**
```bash
docker build -t bobnox:cli .
docker run --rm -v /path/to/folder:/data bobnox:cli --path /data
```

### Docker with GUI (Browser Access)

Run the full GUI in Docker using noVNC (web-based access):

```bash
# Build and run with VNC
./run-docker-vnc.sh
```

Then open your browser: **http://localhost:6080/vnc.html**

**Or manually:**
```bash
docker build -f Dockerfile.vnc -t bobnox-vnc:latest .
docker run --rm -p 6080:6080 -v $HOME:$HOME bobnox-vnc:latest
```

**Benefits:**
- ✅ Works on any system (no X11/Wayland issues)
- ✅ Access from any device on your network
- ✅ Fully containerized and isolated
- ✅ Perfect for remote servers

### Publishing to GitHub Container Registry

Automatically builds and publishes on version tags via GitHub Actions.

**Manual publish:**

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u anorak999 --password-stdin

# Tag and push CLI version
docker build -t ghcr.io/anorak999/bobnox:latest .
docker push ghcr.io/anorak999/bobnox:latest

# Tag and push VNC version
docker build -f Dockerfile.vnc -t ghcr.io/anorak999/bobnox-vnc:latest .
docker push ghcr.io/anorak999/bobnox-vnc:latest
```

**Automated via GitHub Actions:**

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will automatically build and publish both images.

## 📝 Log Files

Each organization run automatically creates a log file with:
- Start/end timestamps
- Directory path
- Detailed file move operations
- Total files moved
- Any errors encountered

**Log Format**: `bobnox-log-YYYYMMDD-HHMMSS.txt`

## 🎨 UI Specifications

- **Window Size**: 480×360 pixels (minimal, compact)
- **Theme**: Dark mode (`#1E1E1E` background)
- **Font**: Inter (system fallback)
- **Icon**: 48×48px SVG rendered button

## ⚙️ Configuration

Edit `EXTENSION_MAP` in `bobnox.py` to customize file categories and folder names.

## 🔧 Troubleshooting

**SVG icon not showing?**
```bash
pip install --upgrade cairosvg Pillow
```

**Icon still missing?**
- Ensure `assets/Sort--Streamline-Solar.svg` exists
- App will show a fallback "▶" button if SVG fails

**Docker VNC not accessible?**
- Ensure port 6080 is not in use: `lsof -i :6080`
- Check Docker logs: `docker logs <container-id>`
- Verify firewall allows port 6080

**Docker CLI no output?**
- Check volume mount: Ensure `-v` path is correct
- Verify permissions: Container needs write access to mounted folder
- Check logs in organized folder: `bobnox-log-*.txt`

## � Repository Structure

```
bobnox/
├── bobnox.py                    # Main GUI application
├── organize_cli.py              # Headless CLI for Docker
├── run-bobnox.sh               # Native launcher script
├── run-docker-vnc.sh           # VNC Docker wrapper
├── docker-start-vnc.sh         # VNC startup script
├── bobnox.desktop              # Desktop launcher
├── Dockerfile                   # Headless CLI image
├── Dockerfile.vnc              # VNC GUI image
├── .dockerignore               # Docker build exclusions
├── .github/
│   ├── workflows/
│   │   └── docker-publish.yml  # Auto-publish on tags
│   └── copilot-instructions.md # AI coding guidelines
├── assets/
│   └── Sort--Streamline-Solar.svg
└── README.md
```

## �📄 License

Open source - feel free to use and modify.


## 🤝 Contributing

This is a minimal, focused tool. Keep it simple!
