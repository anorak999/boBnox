#!/bin/bash
# Build .deb and .rpm packages for BoBnox v5.0.0
# Usage: ./packaging/build-package.sh

set -euo pipefail

VERSION="5.0.0"
PKG_NAME="bobnox"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
STAGE_DIR="$SCRIPT_DIR/stage"
BUILD_DIR="$SCRIPT_DIR/build"

echo "=== Building BoBnox v${VERSION} packages ==="

# Clean previous builds
rm -rf "$STAGE_DIR" "$BUILD_DIR"
mkdir -p "$STAGE_DIR/usr/bin"
mkdir -p "$STAGE_DIR/usr/lib/$PKG_NAME"
mkdir -p "$STAGE_DIR/usr/share/applications"
mkdir -p "$STAGE_DIR/usr/share/icons"
mkdir -p "$STAGE_DIR/usr/share/doc/$PKG_NAME"

echo "[1/5] Staging Python backend..."
cp "$PROJECT_DIR/bobnox.py" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp "$PROJECT_DIR/organize_cli.py" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp "$PROJECT_DIR/requirements.txt" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp -r "$PROJECT_DIR/backend" "$STAGE_DIR/usr/lib/$PKG_NAME/"

echo "[2/5] Staging frontend + Electron..."
cp -r "$PROJECT_DIR/Geist" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp -r "$PROJECT_DIR/assets" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp -r "$PROJECT_DIR/BoBnox-icon" "$STAGE_DIR/usr/lib/$PKG_NAME/"

# Copy built frontend (static files)
if [ -d "$PROJECT_DIR/frontend/dist" ]; then
    cp -r "$PROJECT_DIR/frontend/dist" "$STAGE_DIR/usr/lib/$PKG_NAME/"
    echo "  Included built frontend from frontend/dist/"
else
    echo "  WARNING: frontend/dist/ not found. Run 'cd frontend && npm run build' first."
fi

# Copy Electron main process files
mkdir -p "$STAGE_DIR/usr/lib/$PKG_NAME/electron"
cp "$PROJECT_DIR/frontend/electron/main.js" "$STAGE_DIR/usr/lib/$PKG_NAME/electron/"
cp "$PROJECT_DIR/frontend/electron/preload.js" "$STAGE_DIR/usr/lib/$PKG_NAME/electron/"

echo "[3/5] Installing launcher scripts..."
cp "$SCRIPT_DIR/bobnox" "$STAGE_DIR/usr/bin/bobnox"
cp "$SCRIPT_DIR/bobnox-gui" "$STAGE_DIR/usr/bin/bobnox-gui"
chmod +x "$STAGE_DIR/usr/bin/bobnox" "$STAGE_DIR/usr/bin/bobnox-gui"
cp "$SCRIPT_DIR/bobnox.desktop" "$STAGE_DIR/usr/share/applications/$PKG_NAME.desktop"
cp "$PROJECT_DIR/BoBnox-icon/Bobnox-icon.png" "$STAGE_DIR/usr/share/icons/$PKG_NAME.png"
cp "$PROJECT_DIR/README.md" "$STAGE_DIR/usr/share/doc/$PKG_NAME/"
cp "$PROJECT_DIR/LICENSE" "$STAGE_DIR/usr/share/doc/$PKG_NAME/"

echo "[4/5] Cleaning up..."
find "$STAGE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$STAGE_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "[4/5] Building packages..."
python3 "$SCRIPT_DIR/build_deb.py" \
    --stage "$STAGE_DIR" \
    --output "$BUILD_DIR" \
    --version "$VERSION"

python3 "$SCRIPT_DIR/build_rpm.py" \
    --stage "$STAGE_DIR" \
    --output "$BUILD_DIR" \
    --version "$VERSION"

rm -rf "$STAGE_DIR"

echo ""
echo "=== Build complete ==="
echo "Packages created in: $BUILD_DIR"
ls -lh "$BUILD_DIR"/${PKG_NAME}*.{deb,rpm} 2>/dev/null || true
echo ""
echo "Install with:"
echo "  sudo dpkg -i $BUILD_DIR/bobnox_${VERSION}-1_all.deb"
echo "  sudo rpm -i $BUILD_DIR/bobnox-${VERSION}-1.*.rpm"
