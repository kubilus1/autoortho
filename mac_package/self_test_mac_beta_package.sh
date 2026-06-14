#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
AO_DIR="$APP_DIR/autoortho"
RUNTIME_DIR="$APP_DIR/runtime"
VENV_DIR="$RUNTIME_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
WHEELHOUSE="$APP_DIR/wheelhouse"
REQ="$APP_DIR/requirements-mac.txt"

fail() {
  echo "FAIL: $1"
  exit 1
}

pass() {
  echo "PASS: $1"
}

echo "Auto Ortho for Silicon Mac package self-test"
echo "Package folder: $APP_DIR"
echo

[ -d "$AO_DIR" ] || fail "Missing autoortho folder"
pass "autoortho folder exists"

[ -f "$AO_DIR/autoortho.py" ] || fail "Missing autoortho.py"
pass "autoortho.py exists"

[ -f "$AO_DIR/config_ui.py" ] || fail "Missing config_ui.py"
pass "config_ui.py exists"

[ -f "$AO_DIR/start_autoortho_mac_fuset.sh" ] || fail "Missing FUSE-T launcher"
pass "FUSE-T launcher exists"

[ -x "$AO_DIR/start_autoortho_mac_fuset.sh" ] || fail "FUSE-T launcher is not executable"
pass "FUSE-T launcher is executable"

[ -f "$AO_DIR/mac_mount_fuset.py" ] || fail "Missing mac_mount_fuset.py"
pass "generic FUSE-T mount helper exists"

[ -f "$AO_DIR/aoimage/aoimage.dylib" ] || fail "Missing aoimage.dylib"
pass "aoimage.dylib exists"

[ -f "$AO_DIR/lib/darwin_arm/libispc_texcomp.dylib" ] || fail "Missing libispc_texcomp.dylib"
pass "libispc_texcomp.dylib exists"

[ -f "$AO_DIR/lib/darwin_arm/libstbdxt.dylib" ] || fail "Missing libstbdxt.dylib"
pass "libstbdxt.dylib exists"

[ -d "$WHEELHOUSE" ] || fail "Missing wheelhouse folder"
pass "wheelhouse exists"

[ -f "$REQ" ] || fail "Missing requirements-mac.txt"
pass "requirements-mac.txt exists"

WHEEL_COUNT="$(find "$WHEELHOUSE" -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name '*.zip' \) | wc -l | tr -d ' ')"
[ "$WHEEL_COUNT" != "0" ] || fail "wheelhouse is empty"
pass "wheelhouse has $WHEEL_COUNT package file(s)"

if [ ! -x "$PYTHON" ]; then
  echo
  echo "Local runtime does not exist yet. Creating test runtime..."
  mkdir -p "$RUNTIME_DIR"

  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV_DIR"
  else
    fail "python3 not found; cannot create runtime"
  fi

  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install --no-index --find-links "$WHEELHOUSE" -r "$REQ"
fi

[ -x "$PYTHON" ] || fail "runtime Python was not created"
pass "runtime Python exists"

"$PYTHON" - <<'PY'
import importlib
mods = [
    "requests",
    "PIL",
    "PySimpleGUI",
    "refuse",
]
for mod in mods:
    importlib.import_module(mod)
print("PASS: required Python imports work")
PY

"$PYTHON" - <<'PY'
from pathlib import Path
required = [
    Path("autoortho.py"),
    Path("config_ui.py"),
    Path("start_autoortho_mac_fuset.sh"),
    Path("mac_mount_fuset.py"),
    Path("aoimage/aoimage.dylib"),
    Path("lib/darwin_arm/libispc_texcomp.dylib"),
    Path("lib/darwin_arm/libstbdxt.dylib"),
]
missing = [str(p) for p in required if not p.exists()]
if missing:
    raise SystemExit("FAIL: missing inside autoortho folder: " + ", ".join(missing))
print("PASS: autoortho required files present from Python")
PY

echo
echo "Checking FUSE-T install status..."
if [ -f "/usr/local/lib/libfuse-t.dylib" ]; then
  pass "FUSE-T library exists"
else
  echo "WARN: FUSE-T library not found at /usr/local/lib/libfuse-t.dylib"
  echo "      Package can still be shared, but users must install FUSE-T before Run works."
fi

echo
echo "Self-test complete."
