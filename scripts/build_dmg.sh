#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(python3 "$ROOT_DIR/scripts/validate_version.py")"
APP_NAME="DesktopAppCiBuilder"
APP_BUNDLE="$ROOT_DIR/dist/${APP_NAME}.app"
STAGING_DIR="$ROOT_DIR/build/dmg"
OUTPUT_DIR="$ROOT_DIR/artifacts"
OUTPUT_FILE="$OUTPUT_DIR/${APP_NAME}-${VERSION}-macos.dmg"

if [[ ! -d "$APP_BUNDLE" ]]; then
    echo "Missing app bundle: $APP_BUNDLE" >&2
    exit 1
fi

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"
cp -R "$APP_BUNDLE" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

rm -f "$OUTPUT_FILE"
hdiutil create     -volname "Desktop App CI Builder"     -srcfolder "$STAGING_DIR"     -ov     -format UDZO     "$OUTPUT_FILE"

echo "$OUTPUT_FILE"
