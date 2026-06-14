#!/bin/bash
set -euo pipefail

AO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$AO_DIR/.." && pwd)"

PACKAGE_PYTHON="$PROJECT_DIR/runtime/venv/bin/python"
SOURCE_TREE_PYTHON="$PROJECT_DIR/venv/bin/python"

if [ -n "${AUTOORTHO_RUNTIME_PYTHON:-}" ] && [ -x "$AUTOORTHO_RUNTIME_PYTHON" ]; then
  PYTHON="$AUTOORTHO_RUNTIME_PYTHON"
elif [ -x "$PACKAGE_PYTHON" ]; then
  PYTHON="$PACKAGE_PYTHON"
elif [ -x "$SOURCE_TREE_PYTHON" ]; then
  PYTHON="$SOURCE_TREE_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "Could not find Python."
  echo "Run the package launcher first:"
  echo "  Start Auto Ortho for Silicon Mac.command"
  echo "That creates runtime/venv for the packaged beta."
  exit 1
fi

FUSE_T_LIB="${FUSE_T_LIB:-/usr/local/lib/libfuse-t.dylib}"
EXT_ROOT="${EXT_ROOT:-$HOME/AutoOrthoMounts}"
LOG_DIR="$HOME/Library/Logs/AutoOrthoSiliconMac"
mkdir -p "$LOG_DIR"
STOP_ON_XPLANE_QUIT="${STOP_ON_XPLANE_QUIT:-1}"
DISCOVERY_JSON="$LOG_DIR/autoortho-mac-fuset-discovery.json"

PIDS=()
MONITOR_PIDS=()

cleanup() {
  echo
  echo "Stopping AutoOrtho FUSE-T and unmounting..."

  for pid in "${PIDS[@]:-}" "${MONITOR_PIDS[@]:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done

  sleep 2

  for pid in "${PIDS[@]:-}" "${MONITOR_PIDS[@]:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  done

  if [ -d "$EXT_ROOT" ]; then
    while IFS= read -r mountpoint; do
      [ -n "$mountpoint" ] || continue
      diskutil unmount force "$mountpoint" 2>/dev/null || true
      umount "$mountpoint" 2>/dev/null || true
    done < <(mount | awk -v root="$EXT_ROOT" '$0 ~ root {print $3}')
  fi

  if mount | grep -q "$EXT_ROOT"; then
    echo "Warning: some AutoOrtho FUSE-T mounts still appear mounted:"
    mount | grep "$EXT_ROOT" || true
  else
    echo "FUSE-T unmounted."
  fi
}

trap cleanup EXIT INT TERM

echo "AutoOrtho for Silicon Mac FUSE-T launcher"
echo "AO_DIR: $AO_DIR"
echo "Python: $PYTHON"
echo "FUSE-T: $FUSE_T_LIB"
echo "Stop on X-Plane quit: $STOP_ON_XPLANE_QUIT"

if [ ! -f "$FUSE_T_LIB" ]; then
  echo "FUSE-T library not found: $FUSE_T_LIB"
  exit 1
fi

cd "$AO_DIR"

echo "Discovering installed AutoOrtho sceneries..."

"$PYTHON" - <<'PY' > "$DISCOVERY_JSON"
import configparser
import json
import os
from pathlib import Path

def find_config_path():
    candidates = [
        Path.home() / ".autoortho",
        Path.home() / ".autoortho-data" / ".autoortho",
        Path.home() / ".autoortho-data" / "autoortho.ini",
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path.home() / ".autoortho"

def get_first_existing(cp, names):
    for section in cp.sections():
        for name in names:
            if cp.has_option(section, name):
                value = cp.get(section, name).strip()
                if value:
                    return os.path.expanduser(value)
    return ""

cfg_path = find_config_path()
cp = configparser.ConfigParser()
cp.read(cfg_path)

xplane_path = get_first_existing(cp, ["xplane_path", "xplane_dir", "xplane"])
scenery_path = get_first_existing(cp, ["scenery_path", "scenery_dir", "custom_scenery"])

if not scenery_path and xplane_path:
    scenery_path = os.path.join(xplane_path, "Custom Scenery")

if not scenery_path:
    scenery_path = os.path.expanduser("~/X-Plane 12/Custom Scenery")

custom_scenery = scenery_path

if xplane_path:
    xplane_exe = os.path.join(xplane_path, "X-Plane.app", "Contents", "MacOS", "X-Plane")
else:
    xplane_root = os.path.dirname(custom_scenery)
    xplane_exe = os.path.join(xplane_root, "X-Plane.app", "Contents", "MacOS", "X-Plane")

source_root = os.path.join(custom_scenery, "z_autoortho", "scenery")

mounts = []
if os.path.isdir(source_root):
    for name in sorted(os.listdir(source_root)):
        root = os.path.join(source_root, name)
        if name.startswith("z_ao_") and os.path.isdir(root):
            mounts.append({
                "root": root,
                "mount": os.path.join(custom_scenery, name),
            })

print(json.dumps({
    "config": str(cfg_path),
    "custom_scenery": custom_scenery,
    "xplane_exe": xplane_exe,
    "source_root": source_root,
    "mounts": mounts,
}, indent=2))
PY

COUNT="$("$PYTHON" -c 'import json,sys; print(len(json.load(open(sys.argv[1])).get("mounts", [])))' "$DISCOVERY_JSON")"
XP_CUSTOM_SCENERY="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("custom_scenery",""))' "$DISCOVERY_JSON")"
XPLANE_EXE="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("xplane_exe",""))' "$DISCOVERY_JSON")"

if [ "$COUNT" = "0" ]; then
  echo "No installed AutoOrtho sceneries found."
  echo "Discovery details:"
  cat "$DISCOVERY_JSON"
  exit 1
fi

if [ -z "$XP_CUSTOM_SCENERY" ] || [ ! -d "$XP_CUSTOM_SCENERY" ]; then
  echo "Could not determine valid X-Plane Custom Scenery folder: $XP_CUSTOM_SCENERY"
  echo "Discovery details:"
  cat "$DISCOVERY_JSON"
  exit 1
fi

echo "Found $COUNT installed scenery mount(s)."
echo "Custom Scenery: $XP_CUSTOM_SCENERY"
echo "X-Plane executable: $XPLANE_EXE"

mkdir -p "$EXT_ROOT"

echo "Stopping old AutoOrtho FUSE-T helpers..."
pkill -f mac_mount_fuset.py 2>/dev/null || true
pkill -f mac_mount_ao_na_fuset.py 2>/dev/null || true

echo "Starting live tile monitor..."
LIVE_TILE_LOG="$LOG_DIR/autoortho-live-tiles.log"
: > "$LIVE_TILE_LOG"

AO_CACHE_DIR="$HOME/.autoortho-data/cache" AO_LIVE_TILE_LOG="$LIVE_TILE_LOG" AO_TILE_MONITOR_INTERVAL="${AO_TILE_MONITOR_INTERVAL:-1.0}" AO_TILE_HEARTBEAT_INTERVAL="${AO_TILE_HEARTBEAT_INTERVAL:-0.75}" "$PYTHON" -u "$AO_DIR/mac_live_tile_monitor.py" >> "$LIVE_TILE_LOG" 2>&1 &
MONITOR_PID="$!"
MONITOR_PIDS+=("$MONITOR_PID")

echo "Live tile monitor PID: $MONITOR_PID"
echo "Live tile log: $LIVE_TILE_LOG"

echo "Starting mounts..."

for idx in $(seq 0 $((COUNT - 1))); do
  ROOT="$("$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1]))['mounts'][$idx]['root'])" "$DISCOVERY_JSON")"
  ORIG_MOUNT="$("$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1]))['mounts'][$idx]['mount'])" "$DISCOVERY_JSON")"
  NAME="$(basename "$ORIG_MOUNT")"
  EXT_MOUNT="$EXT_ROOT/${NAME}_fuset"
  XP_LINK="$XP_CUSTOM_SCENERY/$NAME"
  LOG="$LOG_DIR/autoortho-mac-fuset-$NAME.log"

  echo
  echo "Scenery: $NAME"
  echo "  Source: $ROOT"
  echo "  External mount: $EXT_MOUNT"
  echo "  X-Plane link: $XP_LINK"

  diskutil unmount force "$EXT_MOUNT" 2>/dev/null || true
  umount "$EXT_MOUNT" 2>/dev/null || true

  rm -rf "$EXT_MOUNT"
  mkdir -p "$EXT_MOUNT"

  rm -f "$XP_LINK"
  rm -rf "$XP_LINK"

  FUSE_T_LIB="$FUSE_T_LIB" "$PYTHON" -u "$AO_DIR/mac_mount_fuset.py" \
    --source-root "$ROOT" \
    --cache-dir "$HOME/.autoortho-data/cache" \
    --mountpoint "$EXT_MOUNT" \
    --volname "$NAME" \
    --fuset-lib "$FUSE_T_LIB" \
    > "$LOG" 2>&1 &

  PID=$!
  PIDS+=("$PID")

  READY=0
  for i in $(seq 1 45); do
    if ! kill -0 "$PID" 2>/dev/null; then
      echo "Mount process for $NAME exited early."
      tail -n 120 "$LOG"
      exit 1
    fi

    if mount | grep -q "$EXT_MOUNT"; then
      READY=1
      break
    fi

    if [ -d "$EXT_MOUNT/terrain" ] || [ -d "$EXT_MOUNT/textures" ]; then
      READY=1
      break
    fi

    sleep 1
  done

  if [ "$READY" != "1" ]; then
    echo "FUSE-T mount did not become ready for $NAME."
    tail -n 120 "$LOG"
    exit 1
  fi

  ln -s "$EXT_MOUNT" "$XP_LINK"

  echo "  Ready."
done

echo
echo "All AutoOrtho FUSE-T mounts are ready."
echo "You may now launch X-Plane."
if [ "$STOP_ON_XPLANE_QUIT" = "1" ]; then
  echo "AutoOrtho will stop automatically after X-Plane closes."
else
  echo "AutoOrtho will stay running after X-Plane closes."
fi
echo "Press Ctrl+C here to stop manually."

XPLANE_PID=""

while true; do
  ALIVE=0
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      ALIVE=1
      break
    fi
  done

  if [ "$ALIVE" != "1" ]; then
    echo "All AutoOrtho mount processes exited."
    break
  fi

  XPLANE_PID="$(ps ax -o pid= -o command= | XPLANE_EXE="$XPLANE_EXE" "$PYTHON" -c 'import os,sys
target = os.path.realpath(os.environ.get("XPLANE_EXE", ""))
for line in sys.stdin:
    parts = line.strip().split(None, 1)
    if len(parts) != 2:
        continue
    pid, cmd = parts
    if os.path.realpath(cmd) == target:
        print(pid)
        break
')"

  if [ -n "$XPLANE_PID" ]; then
    echo "X-Plane detected with PID $XPLANE_PID. Watching for shutdown..."
    break
  fi

  sleep 3
done

while true; do
  ALIVE=0
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      ALIVE=1
      break
    fi
  done

  if [ "$ALIVE" != "1" ]; then
    echo "All AutoOrtho mount processes exited."
    break
  fi

  if [ -n "$XPLANE_PID" ] && ! kill -0 "$XPLANE_PID" 2>/dev/null; then
    if [ "$STOP_ON_XPLANE_QUIT" = "1" ]; then
      echo "X-Plane has closed. Stopping AutoOrtho."
      exit 0
    else
      echo "X-Plane has closed. Leaving AutoOrtho running because STOP_ON_XPLANE_QUIT=0."
      XPLANE_PID=""
    fi
  fi

  sleep 5
done
