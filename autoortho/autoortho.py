#!/usr/bin/env python

import argparse
import ctypes
import logging
import os
import platform
import shutil
import signal
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import aoconfig
import aostats
import config_ui
import winsetup
from version import __version__

log = logging.getLogger(__name__)

import geocoder


class MountError(Exception):
    pass


class AutoOrthoError(Exception):
    pass


@contextmanager
def setupmount(mountpoint, systemtype):
    mountpoint = os.path.expanduser(mountpoint)

    placeholder_path = os.path.join(mountpoint, ".AO_PLACEHOLDER")

    # Stash placeholder
    if os.path.isdir(mountpoint):
        log.info(f"Existing mountpoint detected: {mountpoint}")
        if os.path.lexists(placeholder_path):
            log.info(f"Detected placeholder dir.  Removing: {mountpoint}")
            shutil.rmtree(mountpoint)

    # Setup
    log.info(f"Setting up mountpoint: {mountpoint}")
    if systemtype == "Linux-FUSE":
        if not os.path.exists(mountpoint):
            os.makedirs(mountpoint)
        if not os.path.isdir(mountpoint):
            raise MountError(f"Failed to setup mount point {mountpoint}!")

    elif systemtype == "dokan-FUSE":
        ret = winsetup.setup_dokan_mount(mountpoint)
        if not ret:
            raise MountError(f"Failed to setup mount point {mountpoint}!")

    elif systemtype == "winfsp-FUSE":
        ret = winsetup.setup_winfsp_mount(mountpoint)
        if not ret:
            raise MountError(f"Failed to setup mount point {mountpoint}!")

    else:
        log.error(f"Unknown mount type of {systemtype}!")
        time.sleep(5)
        raise MountError(f"Unknown system type: {systemtype} for mount {mountpoint}")

    yield mountpoint

    # Cleanup
    if os.path.lexists(mountpoint):
        log.info(f"Cleaning up mountpoint: {mountpoint}")
        os.rmdir(mountpoint)

    # Restore placeholder
    log.info(f"Restoring placeholder for mountpoint: {mountpoint}")
    structure = [
        os.path.join(mountpoint, 'Earth nav data'),
        os.path.join(mountpoint, 'terrain'),
        os.path.join(mountpoint, 'textures'),
    ]

    for d in structure:
        os.makedirs(d)

    Path(placeholder_path).touch()
    log.info(f"Mount point {mountpoint} exiting.")


def diagnose(CFG):
    if platform.system() == 'Windows':
        systemtype, libpath = winsetup.find_win_libs()
    else:
        systemtype = "Linux-FUSE"

    location = geocoder.ip("me")

    log.info("Waiting for mounts...")
    for scenery in CFG.scenery_mounts:
        mount = scenery.get('mount')
        ret = False
        for i in range(5):
            time.sleep(i)
            ret = os.path.isdir(os.path.join(mount, 'textures'))
            if ret:
                break
            log.info('.')

    failed = False
    log.info("\n\n")
    log.info("------------------------------------")
    log.info(" Diagnostic check ...")
    log.info("------------------------------------")
    log.info(f"Detected system: {platform.uname()}")
    log.info(f"Detected location {location.address}")
    log.info(f"Detected installed scenery:")
    for scenery in CFG.scenery_mounts:
        root = scenery.get('root')
        mount = scenery.get('mount')
        log.info(f"    {root}")
        ret = os.path.isdir(os.path.join(mount, 'textures'))
        log.info(f"        Mounted? {ret}")
        if not ret:
            failed = True

    log.info(f"Checking maptypes:")
    import getortho
    for maptype in CFG.autoortho.maptypes:
        with tempfile.TemporaryDirectory() as tmpdir:
            c = getortho.Chunk(2176, 3232, maptype, 13, cache_dir=tmpdir)
            ret = c.get()
            if ret:
                log.info(f"    Maptype: {maptype} OK!")
            else:
                log.warning(f"    Maptype: {maptype} FAILED!")
                failed = True

    log.info(f"Checking DDS file compression:")
    dds_compressor = CFG.pydds.compressor.upper()
    if dds_compressor != "ISPC" and platform.system().lower() == 'darwin':
        log.warning(f"    {dds_compressor} FAILED! Not supported on MacOS, use ISPC instead!")
        failed = True
    else:
        log.info(f"    {dds_compressor} OK!")

    log.info("------------------------------------")
    if failed:
        log.warning("***************")
        log.warning("***************")
        log.warning("FAILURES DETECTED!!")
        log.warning("Please review logs and setup.")
        log.warning("***************")
        log.warning("***************")
        return False
    else:
        log.info(" Diagnostics done.  All checks passed")
        return True
    log.info("------------------------------------\n\n")


class AOMount:
    mounts_running = False

    def __init__(self, cfg):
        self.cfg = cfg
        self.mount_threads = []

    def mount_sceneries(self, blocking=True):
        if not self.cfg.scenery_mounts:
            log.warning(f"No installed sceneries detected.  Exiting.")
            return

        self.mounts_running = True
        for scenery in self.cfg.scenery_mounts:
            t = threading.Thread(
                target=self.domount,
                daemon=False,
                args=(
                    scenery.get('root'),
                    scenery.get('mount'),
                    self.cfg.fuse.threading
                )
            )
            t.start()
            self.mount_threads.append(t)

        if not blocking:
            log.info("Running mounts in non-blocking mode.")
            time.sleep(1)
            diagnose(self.cfg)
            return

        try:
            def handle_sigterm(sig, frame):
                raise (SystemExit)

            signal.signal(signal.SIGTERM, handle_sigterm)

            time.sleep(1)
            # Check things out
            diagnose(self.cfg)

            while self.mounts_running:
                time.sleep(1)

        except (KeyboardInterrupt, SystemExit) as err:
            self.running = False
            log.info(f"Exiting due to {err}")
        finally:
            log.info("Shutting down ...")
            self.unmount_sceneries()

    def unmount_sceneries(self):
        log.info("Unmounting ...")
        self.mounts_running = False
        for scenery in self.cfg.scenery_mounts:
            self.unmount(scenery.get('mount'))

        log.info("Wait on threads...")
        for t in self.mount_threads:
            t.join(5)
            log.info(f"Thread {t.ident} exited.")
        log.info("Unmount complete")

    def domount(self, root, mountpoint, threading=True):

        if threading:
            log.info("Running in multi-threaded mode.")
            nothreads = False
        else:
            log.info("Running in single-threaded mode.")
            nothreads = True

        root = os.path.expanduser(root)

        try:
            if platform.system() == 'Windows':
                systemtype, libpath = winsetup.find_win_libs()
                with setupmount(mountpoint, systemtype) as mount:
                    log.info(f"AutoOrtho:  root: {root}  mountpoint: {mount}")
                    import autoortho_fuse
                    from refuse import high
                    high._libfuse = ctypes.CDLL(libpath)
                    autoortho_fuse.run(
                        autoortho_fuse.AutoOrtho(root),
                        mount,
                        nothreads
                    )
            else:
                with setupmount(mountpoint, "Linux-FUSE") as mount:
                    log.info("Running in FUSE mode.")
                    log.info(f"AutoOrtho:  root: {root}  mountpoint: {mount}")
                    import autoortho_fuse
                    autoortho_fuse.run(
                        autoortho_fuse.AutoOrtho(root),
                        mount,
                        nothreads
                    )

        except Exception as err:
            log.error(f"Exception detected when running FUSE mount: {err}.  Exiting...")
            time.sleep(5)

    def unmount(self, mountpoint):
        mounted = True
        while mounted:
            print(f"Shutting down {mountpoint}")
            print("Send poison pill ...")
            mounted = os.path.isfile(os.path.join(
                mountpoint,
                ".poison"
            ))
            time.sleep(0.5)


class AOMountUI(config_ui.ConfigUI, AOMount):
    def __init__(self, *args, **kwargs):
        self.mount_threads = []
        super().__init__(*args, **kwargs)


def main():
    log.info(f"AutoOrtho version: {__version__}")

    parser = argparse.ArgumentParser(
        description="AutoOrtho: X-Plane scenery streamer"
    )
    parser.add_argument(
        "root",
        help="Root directory of orthophotos",
        nargs="?"
    )
    parser.add_argument(
        "mountpoint",
        help="Directory within X-Plane 11 custom scenery folder to mount",
        nargs="?"
    )
    parser.add_argument(
        "-c",
        "--configure",
        default=False,
        action="store_true",
        help="Run the configuration setup again."
    )
    parser.add_argument(
        "-H",
        "--headless",
        default=False,
        action="store_true",
        help="Run in headless mode."
    )

    args = parser.parse_args()

    CFG = aoconfig.CFG
    if args.configure or (CFG.general.showconfig and not args.headless):
        # Show cfgui at start
        run_headless = False
    else:
        # Don't show cfgui
        run_headless = True

    stats = aostats.AOStats()

    import flighttrack
    ftrack = threading.Thread(
        target=flighttrack.run,
        daemon=True
    )

    # Start helper threads
    ftrack.start()
    stats.start()

    # Run things
    if args.root and args.mountpoint:
        # Just mount specific requested dirs
        root = args.root
        mountpoint = args.mountpoint
        print("root:", root)
        print("mountpoint:", mountpoint)
        aom = AOMount(CFG)
        aom.domount(
            root,
            mountpoint,
            CFG.fuse.threading
        )
    elif run_headless:
        log.info("Running headless")
        aom = AOMount(CFG)
        aom.mount_sceneries()
    else:
        log.info("Running CFG UI")
        cfgui = AOMountUI(CFG)
        cfgui.setup()

    stats.stop()
    flighttrack.ft.stop()

    log.info("AutoOrtho exit.")


if __name__ == '__main__':
    main()
