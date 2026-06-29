#!/bin/sh
set -e

# Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/ 2>/dev/null || true
fi

# Update font cache for Geist fonts
if command -v fc-cache &>/dev/null; then
    fc-cache -f 2>/dev/null || true
fi

# Install Python dependencies if pip is available
if command -v pip3 &>/dev/null; then
    pip3 install --quiet fastapi uvicorn websockets pydantic 2>/dev/null || true
fi
