#!/bin/bash
# boBnox Uninstaller
# Usage: curl -sSL https://raw.githubusercontent.com/Himath-Rajapaksha/boBnox/Home/uninstall.sh | bash

INSTALL_DIR="$HOME/.local/share/bobnox"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "Removing boBnox..."
rm -rf "$INSTALL_DIR"
rm -f "$BIN_DIR/bobnox" "$BIN_DIR/bobnox-gui"
rm -f "$DESKTOP_DIR/bobnox.desktop"
echo "boBnox has been uninstalled."
