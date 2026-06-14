import os
import time
from pathlib import Path

cache_dir = Path(
    os.environ.get(
        "AO_CACHE_DIR",
        str(Path.home() / ".autoortho-data" / "cache"),
    )
).expanduser()

log_file = Path(
    os.environ.get(
        "AO_LIVE_TILE_LOG",
        str(Path.home() / "Desktop" / "autoortho-live-tiles.log"),
    )
).expanduser()

seen = {}

try:
    scan_interval = float(os.environ.get("AO_TILE_MONITOR_INTERVAL", "1.0"))
except ValueError:
    scan_interval = 1.0

try:
    heartbeat_interval = float(os.environ.get("AO_TILE_HEARTBEAT_INTERVAL", "0.75"))
except ValueError:
    heartbeat_interval = 0.75

scan_interval = max(0.5, scan_interval)
heartbeat_interval = max(0.25, heartbeat_interval)


def scan_recent():
    now = time.time()
    if not cache_dir.exists():
        return []

    events = []

    for path in cache_dir.rglob("*"):
        try:
            if not path.is_file():
                continue
            stat = path.stat()
            mtime = stat.st_mtime
            size = stat.st_size
        except OSError:
            continue

        key = str(path)
        old = seen.get(key)

        if old is None:
            seen[key] = (mtime, size)
            if now - mtime < 120:
                events.append(("new", path, size, mtime))
        elif old != (mtime, size):
            seen[key] = (mtime, size)
            events.append(("updated", path, size, mtime))

    return events


def main():
    log_file.parent.mkdir(parents=True, exist_ok=True)

    total_new = 0
    total_updated = 0
    last_scan = 0.0
    last_heartbeat = 0.0
    spinner = ["|", "/", "-", "\\"]
    spin_i = 0

    with log_file.open("a", buffering=1, errors="replace") as log:
        log.write("\n=== AutoOrtho live tile monitor started ===\n")
        log.write(f"cache_dir={cache_dir}\n")
        log.write(f"scan_interval={scan_interval}\n")
        log.write(f"heartbeat_interval={heartbeat_interval}\n")

        while True:
            now = time.time()

            if now - last_scan >= scan_interval:
                events = scan_recent()
                last_scan = now

                for kind, path, size, mtime in events:
                    try:
                        rel = path.relative_to(cache_dir)
                    except Exception:
                        rel = path

                    if kind == "new":
                        total_new += 1
                    else:
                        total_updated += 1

                    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                    kb = size / 1024 if size else 0
                    log.write(
                        f"{ts} TILE {kind:7s} {kb:9.1f} KB  {rel}\n"
                    )

            if now - last_heartbeat >= heartbeat_interval:
                last_heartbeat = now
                spin = spinner[spin_i % len(spinner)]
                spin_i += 1
                ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
                log.write(
                    f"{ts} STREAM {spin} watching cache | "
                    f"new={total_new} updated={total_updated}\n"
                )

            time.sleep(0.25)


if __name__ == "__main__":
    main()
