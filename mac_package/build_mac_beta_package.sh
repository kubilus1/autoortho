#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG_SRC="$ROOT/mac_package"
OUT_ROOT="$HOME/Desktop/AutoOrtho-Silicon-Mac-Beta"
ZIP_PATH="$HOME/Desktop/AutoOrtho-Silicon-Mac-Beta.zip"

PYTHON="$ROOT/venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "Could not find project venv Python at:"
  echo "$PYTHON"
  exit 1
fi

echo "Building AutoOrtho Silicon Mac beta package..."
echo "Root: $ROOT"
echo "Output: $OUT_ROOT"

rm -rf "$OUT_ROOT"
rm -f "$ZIP_PATH"

mkdir -p "$OUT_ROOT"
mkdir -p "$OUT_ROOT/autoortho"
mkdir -p "$OUT_ROOT/wheelhouse"
mkdir -p "$OUT_ROOT/runtime"

echo "Copying launcher files..."
cp "$PKG_SRC/Start Auto Ortho for Silicon Mac.command" "$OUT_ROOT/"
cp "$PKG_SRC/README-Mac-Beta.txt" "$OUT_ROOT/"
cp "$PKG_SRC/requirements-mac.txt" "$OUT_ROOT/"
cp "$PKG_SRC/self_test_mac_beta_package.sh" "$OUT_ROOT/"

chmod +x "$OUT_ROOT/Start Auto Ortho for Silicon Mac.command"
chmod +x "$OUT_ROOT/self_test_mac_beta_package.sh"

echo "Copying AutoOrtho source..."
rsync -a "$ROOT/autoortho/" "$OUT_ROOT/autoortho/" \
  --exclude "venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude ".DS_Store"

echo "Building local wheelhouse..."
"$PYTHON" -m pip download \
  --dest "$OUT_ROOT/wheelhouse" \
  -r "$PKG_SRC/requirements-mac.txt"

echo "Removing old local runtime if present..."
rm -rf "$OUT_ROOT/runtime/venv"

echo "Creating zip..."
cd "$HOME/Desktop"

echo "Creating portable macOS app wrapper..."
WRAPPER_SCRIPT="$ROOT/mac_package/create_macos_app_wrapper.sh"
WRAPPER_PACKAGE_DIR="$HOME/Desktop/AutoOrtho-Silicon-Mac-Beta"

if [ -x "$WRAPPER_SCRIPT" ] && [ -d "$WRAPPER_PACKAGE_DIR" ]; then
  "$WRAPPER_SCRIPT" "$WRAPPER_PACKAGE_DIR"
else
  echo "Warning: could not create app wrapper."
  echo "  WRAPPER_SCRIPT=$WRAPPER_SCRIPT"
  echo "  WRAPPER_PACKAGE_DIR=$WRAPPER_PACKAGE_DIR"
fi

zip -r "AutoOrtho-Silicon-Mac-Beta.zip" "AutoOrtho-Silicon-Mac-Beta" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "*.DS_Store"

echo
echo "Done:"
echo "$ZIP_PATH"
