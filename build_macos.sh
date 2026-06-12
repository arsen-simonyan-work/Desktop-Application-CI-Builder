#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

python3 -m pip install --upgrade pip
if [[ -f requirements.txt ]]; then
    python3 -m pip install -r requirements.txt
fi
python3 -m pip install pyinstaller pillow
python3 scripts/generate_icons.py --require-icns

python3 -m PyInstaller DesktopAppCiBuilder.spec     --noconfirm     --clean

echo "Build complete"
