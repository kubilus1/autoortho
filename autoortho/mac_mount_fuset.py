import argparse
import ctypes
import ctypes.util
import os
import sys
import traceback

def force_fuset_library(fuset_lib):
    if not os.path.exists(fuset_lib):
        raise SystemExit(f"FUSE-T library not found: {fuset_lib}")

    print("Forcing FUSE-T library before importing refuse/autoortho_fuse:", fuset_lib)

    original_find_library = ctypes.util.find_library

    def find_library_override(name):
        if name in ("fuse", "osxfuse", "macfuse", "fuse-t"):
            return fuset_lib
        return original_find_library(name)

    ctypes.util.find_library = find_library_override

    import refuse.high as high
    high._libfuse = ctypes.CDLL(fuset_lib)

    return high


def main():
    parser = argparse.ArgumentParser(description="AutoOrtho macOS FUSE-T mount helper")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--mountpoint", required=True)
    parser.add_argument("--volname", default="AutoOrtho")
    parser.add_argument("--fuset-lib", default="/usr/local/lib/libfuse-t.dylib")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    source_root = os.path.expanduser(args.source_root)
    cache_dir = os.path.expanduser(args.cache_dir)
    mountpoint = os.path.expanduser(args.mountpoint)

    if not os.path.isdir(source_root):
        raise SystemExit(f"Source root does not exist: {source_root}")

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(mountpoint, exist_ok=True)

    force_fuset_library(args.fuset_lib)

    from refuse.high import FUSE
    from autoortho_fuse import AutoOrtho

    print("Starting AutoOrtho macOS FUSE-T direct mount")
    print("FUSE-T library:", args.fuset_lib)
    print("Source root:", source_root)
    print("Cache dir:", cache_dir)
    print("Mountpoint:", mountpoint)
    print("Volume name:", args.volname)

    try:
        ao = AutoOrtho(source_root, cache_dir)

        FUSE(
            ao,
            mountpoint,
            foreground=True,
            nothreads=True,
            debug=args.debug,
            volname=args.volname,
        )
    except Exception as exc:
        print("AutoOrtho macOS FUSE-T mount failed:", type(exc).__name__, repr(exc))
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
