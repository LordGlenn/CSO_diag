#!/bin/bash
# Build script for macOS / Linux
# Creates a standalone executable with bundled Chromium browser

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Zyxel CSO Diagnostics Collector - Build Script ==="

# Step 1: Install dependencies
echo "[1/4] Installing Python dependencies..."
pip3 install playwright pyinstaller

# Step 2: Install Chromium browser
echo "[2/4] Installing Chromium browser for Playwright..."
python3 -m playwright install chromium

# Step 3: Find Playwright Chromium path
echo "[3/4] Locating Chromium browser..."

# macOS default path
PW_CACHE="$HOME/Library/Caches/ms-playwright"
if [ ! -d "$PW_CACHE" ]; then
    # Linux default path
    PW_CACHE="$HOME/.cache/ms-playwright"
fi

CHROMIUM_DIR=$(ls -d "$PW_CACHE"/chromium-* 2>/dev/null | sort -V | tail -1)

if [ -z "$CHROMIUM_DIR" ]; then
    echo "ERROR: Could not find Playwright Chromium installation."
    echo "Please run: python3 -m playwright install chromium"
    exit 1
fi

echo "  Found Chromium at: $CHROMIUM_DIR"

# Step 4: Build with PyInstaller
echo "[4/4] Building executable with PyInstaller..."
pyinstaller \
    --onedir \
    --name cso_diag \
    --add-data "$CHROMIUM_DIR:playwright/chromium" \
    --hidden-import playwright \
    --hidden-import playwright.sync_api \
    --hidden-import playwright._impl \
    --hidden-import playwright._impl._driver \
    --noconfirm \
    --clean \
    cso_diag.py

echo ""
echo "=== Build complete! ==="
echo "Output directory: dist/cso_diag/"
echo ""
echo "Usage:"
echo "  ./dist/cso_diag/cso_diag <device_ip> <username> <password>"
echo ""
echo "To distribute, zip the entire dist/cso_diag/ directory:"
echo "  cd dist && zip -r cso_diag_mac.zip cso_diag/"
