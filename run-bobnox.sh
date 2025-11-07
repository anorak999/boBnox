#!/bin/bash
# Simple wrapper to run boBnox without VS Code
# This runs directly on the host, not in Docker

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install cairosvg Pillow 2>/dev/null || pip install Pillow
else
    source .venv/bin/activate
fi

# Run the GUI application
echo "Starting boBnox..."
python bobnox.py

# Deactivate venv when done
deactivate
