# Running boBnox Without VS Code

Since GUI in Docker with Wayland is complex, here's the **simple solution** that works on your system.

## ✅ Recommended: Run Directly on Host

### Quick Start

```bash
cd /home/anorak/Works/bobnox
./run-bobnox.sh
```

That's it! The GUI will open.

### What It Does

The `run-bobnox.sh` script:
1. Creates/activates Python virtual environment automatically
2. Installs dependencies if needed
3. Runs the boBnox GUI
4. Cleans up when you close the app

No VS Code, no Docker complexity, just works!

## 🚀 Desktop Launcher (Even Easier!)

Install the desktop launcher:

```bash
cp /home/anorak/Works/bobnox/bobnox.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/bobnox.desktop
```

Now you can:
- ✅ Find "boBnox File Organizer" in your application menu
- ✅ Pin it to favorites/dock
- ✅ Launch with one click - no terminal needed!

## Alternative: Docker (Headless CLI Only)

For organizing files via command line in Docker:

```bash
docker build -t bobnox:cli .
docker run --rm -v /path/to/folder:/data bobnox:cli --path /data
```

Note: GUI in Docker requires complex X11/Wayland setup on your system. The host-based script above is simpler and more reliable.

## Usage

### Method 1: From Terminal
```bash
./run-bobnox.sh
```

### Method 2: From Application Menu
1. Press Super/Windows key
2. Type "bobnox"
3. Click "boBnox File Organizer"

### Method 3: Create Alias (Optional)
Add to your `~/.zshrc`:
```bash
alias bobnox='/home/anorak/Works/bobnox/run-bobnox.sh'
```

Then just run:
```bash
bobnox
```

## Updating

When you pull new code:
```bash
cd /home/anorak/Works/bobnox
git pull
./run-bobnox.sh  # Dependencies auto-update if needed
```

## Uninstalling Desktop Launcher

```bash
rm ~/.local/share/applications/bobnox.desktop
```

## Why This Approach?

- ✅ **Simple**: No Docker/X11/Wayland complexity
- ✅ **Fast**: No container overhead
- ✅ **Works**: Native GUI on your Wayland system
- ✅ **Integrated**: Uses system file dialogs and themes
- ✅ **Portable**: Same script works on any Linux distro

Docker is great for servers and CLI tools. For desktop GUI apps, native execution is simpler!
