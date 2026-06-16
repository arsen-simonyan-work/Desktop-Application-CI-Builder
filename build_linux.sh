#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${BUILD_VENV:-$ROOT_DIR/.venv-build}"

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
fi

PYTHON_BIN="$VENV_DIR/bin/python"

"$PYTHON_BIN" -m pip install --upgrade pip
if [[ -f requirements.txt ]]; then
    "$PYTHON_BIN" -m pip install -r requirements.txt
fi
"$PYTHON_BIN" -m pip install pyinstaller pillow
"$PYTHON_BIN" scripts/generate_icons.py --require-icns

"$PYTHON_BIN" -m PyInstaller DesktopAppCiBuilder.spec \
    --noconfirm \
    --clean

echo "Build complete"
