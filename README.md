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

## 🚀 Installation

### Prerequisites

```bash
# Python 3.7+
python --version
```

### Install Dependencies

```bash
pip install cairosvg Pillow
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

## 💻 Usage

### Run the Application

```bash
python bobnox.py
```

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

## 📝 Log Files

Each organization run automatically creates a log file with:
- Start/end timestamps
- Directory path
- Detailed file move operations
- Total files moved
- Any errors encountered

**Log Format**: `bobnox-log-YYYYMMDD-HHMMSS.txt`

## 🐳 Docker (headless)

You can run boBnox in a container (headless) to organize folders on the host. This is suitable for publishing a container image to GitHub Packages / GitHub Container Registry.

Build the image locally:

```bash
# from repository root
docker build -t ghcr.io/<OWNER>/bobnox:latest .
```

Run the container and mount a host folder to `/data` inside the container:

```bash
docker run --rm -v /path/to/folder:/data ghcr.io/<OWNER>/bobnox:latest --path /data
```

Publish to GitHub Container Registry (example):

```bash
# Log in to GHCR
echo $CR_PAT | docker login ghcr.io -u <GITHUB_USERNAME> --password-stdin
docker tag ghcr.io/<OWNER>/bobnox:latest ghcr.io/<OWNER>/bobnox:latest
docker push ghcr.io/<OWNER>/bobnox:latest
```

Notes:
- The container runs a headless CLI (`organize_cli.py`) that calls the same organizing logic as the GUI.
- Bind-mount the host folder you want organized into the container and pass `--path /data` (or the mountpoint you choose).


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

## 📄 License

Open source - feel free to use and modify.

## 🤝 Contributing

This is a minimal, focused tool. Keep it simple!
