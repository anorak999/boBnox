# Running boBnox GUI in Docker

This guide shows how to run the boBnox GUI application in a Docker container without opening VS Code.

## Prerequisites

- Docker installed
- X11 server running (standard on Linux desktop environments)
- `xhost` utility (usually pre-installed)

## Quick Start

### Method 1: Using the Script (Recommended)

Simply run the provided script:

```bash
cd /home/anorak/Works/bobnox
./run-gui.sh
```

The script will:
1. Build the Docker image (first time only)
2. Start the GUI application
3. Automatically handle X11 permissions
4. Clean up when you close the app

### Method 2: Manual Docker Commands

**Build the image:**
```bash
docker build -f Dockerfile.gui -t bobnox-gui:latest .
```

**Run the container:**
```bash
# Allow Docker to access X server
xhost +local:docker

# Run the GUI
docker run --rm \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v $HOME:$HOME \
    --name bobnox-gui \
    bobnox-gui:latest

# Revoke access after closing
xhost -local:docker
```

## Usage

1. Run the script or Docker command
2. The boBnox GUI window will appear
3. Use the application normally:
   - Click **Browse** to select a folder
   - Click the **icon button** to organize files
   - Watch the progress bar
4. Close the window when done

## File Access

The container has access to your entire home directory (`$HOME`), so you can:
- Browse any folder in your home directory
- Organize files anywhere in `/home/anorak/`
- Organized files and logs remain on your host system

## Troubleshooting

### Error: "cannot open display"

```bash
# Check if DISPLAY is set
echo $DISPLAY

# If empty, set it:
export DISPLAY=:0

# Try again
./run-gui.sh
```

### Error: "No protocol specified"

```bash
# Reset X server permissions
xhost +local:docker
./run-gui.sh
```

### GUI doesn't appear

```bash
# Check if X server is running
echo $XDG_SESSION_TYPE  # should show "x11" or "wayland"

# For Wayland, you may need XWayland
sudo apt install xwayland
```

### Build fails

```bash
# Check Docker daemon is running
docker ps

# Rebuild with verbose output
docker build -f Dockerfile.gui -t bobnox-gui:latest . --progress=plain
```

## Creating a Desktop Shortcut (Optional)

Create a desktop launcher to run boBnox like a regular app:

**Create file:** `~/.local/share/applications/bobnox.desktop`

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=boBnox File Organizer
Comment=Organize files into categorized folders
Exec=/home/anorak/Works/bobnox/run-gui.sh
Icon=folder-open
Terminal=false
Categories=Utility;FileTools;
```

Then:
```bash
chmod +x ~/.local/share/applications/bobnox.desktop
```

Now you can launch boBnox from your application menu!

## Updating the Container

When you update the code:

```bash
cd /home/anorak/Works/bobnox
docker build -f Dockerfile.gui -t bobnox-gui:latest .
```

Or just delete the image and run the script again:

```bash
docker rmi bobnox-gui:latest
./run-gui.sh
```

## Benefits of Docker GUI

✅ **No VS Code needed** - Run standalone  
✅ **Clean environment** - Isolated dependencies  
✅ **Easy updates** - Rebuild image to update  
✅ **Portable** - Same experience everywhere  
✅ **Safe** - Container isolation from host
