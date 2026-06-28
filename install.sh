#!/bin/bash
# boBnox Installer - One-line installation
# Usage: curl -sSL https://raw.githubusercontent.com/anorak999/boBnox/Home/install.sh | bash
# Or:    wget -qO- https://raw.githubusercontent.com/anorak999/boBnox/Home/install.sh | bash

set -e

REPO="https://github.com/anorak999/boBnox.git"
BRANCH="Home"
INSTALL_DIR="$HOME/.local/share/bobnox"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "╔═══════════════════════════════════════╗"
echo "║     boBnox File Organizer Installer   ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check for git
if ! command -v git &> /dev/null; then
    echo "Error: git is required but not installed."
    echo "Install it with: sudo apt install git (Ubuntu/Debian)"
    echo "                 sudo dnf install git (Fedora)"
    echo "                 brew install git (macOS)"
    exit 1
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    echo "Install it with: sudo apt install python3 (Ubuntu/Debian)"
    echo "                 sudo dnf install python3 (Fedora)"
    echo "                 brew install python3 (macOS)"
    exit 1
fi

echo "[1/5] Cloning boBnox repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  Updating existing installation..."
    git -C "$INSTALL_DIR" pull --quiet
else
    git clone --quiet --branch "$BRANCH" "$REPO" "$INSTALL_DIR"
fi

echo "[2/5] Setting up Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "[3/5] Creating CLI launcher..."
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/bobnox" << 'LAUNCHER'
#!/bin/bash
# boBnox CLI Launcher
INSTALL_DIR="$HOME/.local/share/bobnox"
source "$INSTALL_DIR/.venv/bin/activate"
cd "$INSTALL_DIR"
python organize_cli.py "$@"
LAUNCHER
chmod +x "$BIN_DIR/bobnox"

echo "[4/5] Creating desktop launcher and installing icon..."
mkdir -p "$DESKTOP_DIR"
mkdir -p "$INSTALL_DIR"

# Copy icon to install dir for desktop integration
cp "$INSTALL_DIR/BoBnox-icon/Bobnox-icon.png" "$INSTALL_DIR/icon.png" 2>/dev/null || true

cat > "$DESKTOP_DIR/bobnox.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=BoBnox
GenericName=File Organizer
Comment=Organize files into categorized folders
Exec=$BIN_DIR/bobnox-gui
Icon=$INSTALL_DIR/icon.png
Terminal=false
Categories=Utility;FileTools;
StartupWMClass=bobnox
StartupNotify=true
DESKTOP

# Also create GUI launcher in BIN_DIR
cat > "$BIN_DIR/bobnox-gui" << 'GUI_LAUNCHER'
#!/bin/bash
# boBnox GUI Launcher
INSTALL_DIR="$HOME/.local/share/bobnox"
source "$INSTALL_DIR/.venv/bin/activate"
cd "$INSTALL_DIR"
python bobnox.py
GUI_LAUNCHER
chmod +x "$BIN_DIR/bobnox-gui"

echo "[5/5] Refreshing desktop database..."
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f "$HOME/.local/share/icons/" 2>/dev/null || true
fi

if echo "$PATH" | grep -q "$BIN_DIR"; then
    PATH_OK=true
else
    PATH_OK=false
fi

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║     Installation Complete!            ║"
echo "╚═══════════════════════════════════════╝"
echo ""
echo "Usage:"
echo "  GUI:    Run 'bobnox-gui' or search 'boBnox' in your apps"
echo "  CLI:    bobnox organize --path /path/to/folder"
echo "  CLI:    bobnox undo"
echo "  CLI:    bobnox config --show"
echo ""

if [ "$PATH_OK" = false ]; then
    echo "NOTE: Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "Uninstall: rm -rf $INSTALL_DIR $BIN_DIR/bobnox $BIN_DIR/bobnox-gui $DESKTOP_DIR/bobnox.desktop"
