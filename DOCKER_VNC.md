# Running boBnox GUI in Docker (Web Access)

Since direct X11/Wayland forwarding is complex, this solution uses **noVNC** - access the GUI through your web browser!

## 🚀 Quick Start

```bash
cd /home/anorak/Works/bobnox
./run-docker-vnc.sh
```

Then open in your browser:
```
http://localhost:6080/vnc.html
```

Click "Connect" and you'll see the boBnox GUI!

## How It Works

The Docker container runs:
- **Xvfb**: Virtual display server
- **x11vnc**: VNC server
- **noVNC**: Web-based VNC client
- **boBnox GUI**: Your application

Everything is isolated in Docker, but accessible through your browser!

## Step-by-Step

### 1. Build and Run

```bash
./run-docker-vnc.sh
```

Wait for:
- Image to build (~2-3 minutes first time)
- Container to start
- "Access the GUI in your browser" message

### 2. Open Browser

Go to: **http://localhost:6080/vnc.html**

### 3. Connect

Click the "Connect" button on the noVNC page

### 4. Use boBnox

The GUI appears in your browser! Use it normally:
- Browse for folders
- Organize files
- View progress

### 5. Stop

Press `Ctrl+C` in the terminal where the container is running

## Manual Docker Commands

If you prefer manual control:

```bash
# Build
docker build -f Dockerfile.vnc -t bobnox-vnc:latest .

# Run
docker run --rm \
    -p 6080:6080 \
    -v $HOME:$HOME \
    --name bobnox-vnc \
    bobnox-vnc:latest
```

Access at: http://localhost:6080/vnc.html

## Advanced Options

### Custom Resolution

```bash
docker run --rm \
    -p 6080:6080 \
    -e RESOLUTION=1024x768 \
    -v $HOME:$HOME \
    --name bobnox-vnc \
    bobnox-vnc:latest
```

### Run in Background

```bash
docker run -d \
    -p 6080:6080 \
    -v $HOME:$HOME \
    --name bobnox-vnc \
    bobnox-vnc:latest

# View logs
docker logs -f bobnox-vnc

# Stop
docker stop bobnox-vnc
```

### Access from Another Device

```bash
# Run with host IP binding
docker run --rm \
    -p 0.0.0.0:6080:6080 \
    -v $HOME:$HOME \
    --name bobnox-vnc \
    bobnox-vnc:latest
```

Access from another device on your network:
```
http://YOUR_IP:6080/vnc.html
```

## Troubleshooting

### Port already in use

```bash
# Check what's using port 6080
sudo lsof -i :6080

# Use different port
docker run --rm -p 8080:6080 ... bobnox-vnc:latest
# Access at http://localhost:8080/vnc.html
```

### Can't access home directory

The container mounts your entire `$HOME` directory, so you can browse all your files.

### Build fails

```bash
# Check Docker is running
docker ps

# Clean build
docker build --no-cache -f Dockerfile.vnc -t bobnox-vnc:latest .
```

### GUI doesn't appear

1. Wait 10 seconds after container starts
2. Refresh browser
3. Check container logs: `docker logs bobnox-vnc`

## Comparison: Docker vs Host

### Docker VNC (Browser-Based)
- ✅ Fully containerized and isolated
- ✅ Works on any system (no X11/Wayland issues)
- ✅ Access from browser or remote devices
- ❌ Slightly slower (VNC overhead)
- ❌ Requires browser window

### Host-Based (`./run-bobnox.sh`)
- ✅ Native performance
- ✅ Better desktop integration
- ✅ System file dialogs and themes
- ❌ Requires Python environment on host
- ❌ Not containerized

## Which Should You Use?

- **For daily use**: `./run-bobnox.sh` (native, faster)
- **For Docker deployment**: `./run-docker-vnc.sh` (isolated, portable)
- **For remote access**: Docker VNC (access from anywhere)
- **For testing**: Docker VNC (clean environment)

## Publishing Docker Image

Tag and push to GitHub Container Registry:

```bash
# Build
docker build -f Dockerfile.vnc -t ghcr.io/anorak999/bobnox-vnc:latest .

# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u anorak999 --password-stdin

# Push
docker push ghcr.io/anorak999/bobnox-vnc:latest
```

Users can then run:
```bash
docker run --rm -p 6080:6080 -v $HOME:$HOME ghcr.io/anorak999/bobnox-vnc:latest
```

And access at http://localhost:6080/vnc.html
