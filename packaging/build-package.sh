#!/bin/bash
# Build .deb and .rpm packages for BoBnox
# Usage: ./packaging/build-package.sh
#
# No external packaging tools required (no fpm, no dpkg-deb, no rpmbuild).
# Uses ar + tar for deb, Python rpm module for rpm.

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

echo "[1/4] Staging application files..."
cp "$PROJECT_DIR/bobnox.py" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp "$PROJECT_DIR/organize_cli.py" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp "$PROJECT_DIR/requirements.txt" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp -r "$PROJECT_DIR/Geist" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp -r "$PROJECT_DIR/assets" "$STAGE_DIR/usr/lib/$PKG_NAME/"
cp -r "$PROJECT_DIR/BoBnox-icon" "$STAGE_DIR/usr/lib/$PKG_NAME/"

echo "[2/4] Installing launcher scripts and desktop integration..."
cp "$SCRIPT_DIR/bobnox" "$STAGE_DIR/usr/bin/bobnox"
cp "$SCRIPT_DIR/bobnox-gui" "$STAGE_DIR/usr/bin/bobnox-gui"
chmod +x "$STAGE_DIR/usr/bin/bobnox" "$STAGE_DIR/usr/bin/bobnox-gui"
cp "$SCRIPT_DIR/bobnox.desktop" "$STAGE_DIR/usr/share/applications/$PKG_NAME.desktop"
cp "$PROJECT_DIR/BoBnox-icon/Bobnox-icon.png" "$STAGE_DIR/usr/share/icons/$PKG_NAME.png"
cp "$PROJECT_DIR/README.md" "$STAGE_DIR/usr/share/doc/$PKG_NAME/"
cp "$PROJECT_DIR/LICENSE" "$STAGE_DIR/usr/share/doc/$PKG_NAME/"

echo "[3/4] Building .deb package..."
python3 "$SCRIPT_DIR/build_deb.py" \
    --stage "$STAGE_DIR" \
    --output "$BUILD_DIR" \
    --version "$VERSION"

echo "[4/4] Building .rpm package..."
python3 "$SCRIPT_DIR/build_rpm.py" \
    --stage "$STAGE_DIR" \
    --output "$BUILD_DIR" \
    --version "$VERSION"

rm -rf "$STAGE_DIR"

echo ""
echo "=== Build complete ==="
echo "Packages created in: $BUILD_DIR"
ls -lh "$BUILD_DIR"/${PKG_NAME}*.{deb,rpm} 2>/dev/null || true
