#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
AO_DIR="$APP_DIR/autoortho"
RUNTIME_DIR="$APP_DIR/runtime"
VENV_DIR="$RUNTIME_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
WHEELHOUSE="$APP_DIR/wheelhouse"
REQ="$APP_DIR/requirements-mac.txt"

echo "Auto Ortho for Silicon Mac"
echo "Package folder: $APP_DIR"

if [ ! -d "$AO_DIR" ]; then
  echo "Missing autoortho folder:"
  echo "$AO_DIR"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

if [ ! -f "$REQ" ]; then
  echo "Missing requirements file:"
  echo "$REQ"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

if [ ! -d "$WHEELHOUSE" ]; then
  echo "Missing wheelhouse folder:"
  echo "$WHEELHOUSE"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

if [ ! -x "$PYTHON" ]; then
  echo "Creating local Python runtime..."
  mkdir -p "$RUNTIME_DIR"

  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 was not found."
    echo "Install Python 3.12 or newer, then run this launcher again."
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
  fi

  python3 -m venv "$VENV_DIR"
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install --no-index --find-links "$WHEELHOUSE" -r "$REQ"
else
  echo "Using existing local runtime."
fi

echo
echo "Checking FUSE-T..."
if [ ! -f "/usr/local/lib/libfuse-t.dylib" ]; then
  echo "FUSE-T was not found at:"
  echo "/usr/local/lib/libfuse-t.dylib"
  echo
  echo "Please install FUSE-T, then run this launcher again."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

echo "FUSE-T found."

cd "$AO_DIR"

echo
echo "Launching Auto Ortho for Silicon Mac..."
"$PYTHON" -u autoortho.py -c

echo
echo "Auto Ortho closed."
read -n 1 -s -r -p "Press any key to close..."
