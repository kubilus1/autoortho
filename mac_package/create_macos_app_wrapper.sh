#!/bin/bash
set -euo pipefail

PACKAGE_DIR="${1:-}"
if [ -z "$PACKAGE_DIR" ]; then
  echo "Usage: $0 /path/to/AutoOrtho-Silicon-Mac-Beta"
  exit 1
fi

APP_NAME="AutoOrtho for Silicon Mac"
APP_DIR="$PACKAGE_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ICON_SOURCE="$SCRIPT_DIR/assets/AutoOrtho.icns"

rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

if [ -f "$ICON_SOURCE" ]; then
  cp "$ICON_SOURCE" "$RESOURCES_DIR/AutoOrtho.icns"
else
  echo "Warning: icon not found at $ICON_SOURCE"
fi

echo "Copying app resources into bundle..."
rsync -a "$PACKAGE_DIR/autoortho/" "$RESOURCES_DIR/autoortho/" \
  --exclude "venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude ".DS_Store"

rsync -a "$PACKAGE_DIR/wheelhouse/" "$RESOURCES_DIR/wheelhouse/" \
  --exclude ".DS_Store"

cp "$PACKAGE_DIR/requirements-mac.txt" "$RESOURCES_DIR/requirements-mac.txt"

chmod +x "$RESOURCES_DIR/autoortho/start_autoortho_mac_fuset.sh" 2>/dev/null || true

cat > "$CONTENTS_DIR/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>AutoOrtho for Silicon Mac</string>
    <key>CFBundleDisplayName</key>
    <string>AutoOrtho for Silicon Mac</string>
    <key>CFBundleIdentifier</key>
    <string>com.autoortho.siliconmac.beta</string>
    <key>CFBundleVersion</key>
    <string>0.0.1</string>
    <key>CFBundleShortVersionString</key>
    <string>0.0.1-beta</string>
    <key>CFBundleExecutable</key>
    <string>AutoOrthoLauncher</string>
    <key>CFBundleIconFile</key>
    <string>AutoOrtho</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.utilities</string>
</dict>
</plist>
PLIST

cat > "$MACOS_DIR/AutoOrthoLauncher" <<'SH_LAUNCHER'
#!/bin/bash

LOG_DIR="$HOME/Library/Logs/AutoOrthoSiliconMac"
LOG="$LOG_DIR/app-launcher.log"

mkdir -p "$LOG_DIR"

{
  echo
  echo "=== AutoOrtho for Silicon Mac app launcher ==="
  date
  echo "Launcher path: $0"

  MACOS_DIR="$(cd "$(dirname "$0")" && pwd)"
  APP_DIR="$(cd "$MACOS_DIR/../.." && pwd)"
  RESOURCES_DIR="$APP_DIR/Contents/Resources"

  AO_DIR="$RESOURCES_DIR/autoortho"
  WHEELHOUSE="$RESOURCES_DIR/wheelhouse"
  REQUIREMENTS="$RESOURCES_DIR/requirements-mac.txt"

  SUPPORT_DIR="$HOME/Library/Application Support/AutoOrthoSiliconMac"
  RUNTIME_DIR="$SUPPORT_DIR/runtime"
  VENV_DIR="$RUNTIME_DIR/venv"
  RUNTIME_PYTHON="$VENV_DIR/bin/python"

  echo "APP_DIR=$APP_DIR"
  echo "RESOURCES_DIR=$RESOURCES_DIR"
  echo "AO_DIR=$AO_DIR"
  echo "WHEELHOUSE=$WHEELHOUSE"
  echo "REQUIREMENTS=$REQUIREMENTS"
  echo "SUPPORT_DIR=$SUPPORT_DIR"
  echo "RUNTIME_PYTHON=$RUNTIME_PYTHON"

  if [ ! -d "$AO_DIR" ]; then
    echo "ERROR: Missing bundled autoortho folder at $AO_DIR"
    exit 1
  fi

  mkdir -p "$RUNTIME_DIR"

  # If an older/bad runtime exists, make sure it is Python 3.12.
  # The bundled wheelhouse is built for CPython 3.12 arm64.
  if [ -x "$RUNTIME_PYTHON" ]; then
    if ! /usr/bin/arch -arm64 "$RUNTIME_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)' 2>/dev/null; then
      echo "Existing runtime is not Python 3.12. Recreating runtime venv..."
      rm -rf "$VENV_DIR"
    fi
  fi

  if [ ! -x "$RUNTIME_PYTHON" ]; then
    echo "Runtime venv not found. Creating Python 3.12 runtime venv..."

    SYSTEM_PYTHON=""

    for candidate in \
      "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12" \
      "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" \
      "/opt/homebrew/bin/python3.12" \
      "/usr/local/bin/python3.12" \
      "$(command -v python3.12 2>/dev/null || true)"
    do
      [ -n "$candidate" ] || continue

      # Do not bootstrap the packaged app runtime from another virtualenv.
      case "$candidate" in
        */venv/*|*/.venv/*)
          echo "Skipping venv Python candidate: $candidate"
          continue
          ;;
      esac

      if [ -x "$candidate" ]; then
        if /usr/bin/arch -arm64 "$candidate" -c 'import sys, platform; raise SystemExit(0 if sys.version_info[:2] == (3, 12) and platform.machine() == "arm64" else 1)' 2>/dev/null; then
          SYSTEM_PYTHON="$candidate"
          break
        else
          echo "Skipping incompatible Python candidate: $candidate"
        fi
      fi
    done

    if [ -z "$SYSTEM_PYTHON" ]; then
      echo "ERROR: Could not find Python 3.12."
      echo "This beta package requires Python 3.12 to create its local runtime."
      echo "Install Python 3.12, then open this app again."
      exit 1
    fi

    echo "SYSTEM_PYTHON=$SYSTEM_PYTHON"
    /usr/bin/arch -arm64 "$SYSTEM_PYTHON" -m venv "$VENV_DIR" || {
      echo "ERROR: Failed to create venv at $VENV_DIR"
      exit 1
    }
  fi

  PYTHON="$RUNTIME_PYTHON"

  echo "PYTHON=$PYTHON"
  /usr/bin/arch -arm64 "$PYTHON" --version

  echo "Installing/verifying Python requirements from bundled wheelhouse..."
  /usr/bin/arch -arm64 "$PYTHON" -m pip install --no-index --find-links "$WHEELHOUSE" -r "$REQUIREMENTS" || {
    echo "ERROR: Failed to install requirements from bundled wheelhouse."
    exit 1
  }

  if [ ! -e "/usr/local/lib/libfuse-t.dylib" ]; then
    echo "WARNING: FUSE-T library not found at /usr/local/lib/libfuse-t.dylib"
    echo "AutoOrtho may not mount until FUSE-T is installed."
  fi

  cd "$AO_DIR" || {
    echo "ERROR: Could not cd to $AO_DIR"
    exit 1
  }

  echo "Launching AutoOrtho GUI..."
  exec /usr/bin/arch -arm64 "$PYTHON" -u autoortho.py -c

} >> "$LOG" 2>&1
SH_LAUNCHER

chmod +x "$MACOS_DIR/AutoOrthoLauncher"
touch "$APP_DIR"

echo "Created $APP_DIR"
