#!/usr/bin/env python

import os
import signal
import sys
import time
import platform
import argparse
import threading
import tempfile

import aoconfig
import aostats
import winsetup
import config_ui

import flighttrack
import importlib

from version import __version__

import logging
log = logging.getLogger(__name__)

import geocoder
import ctypes


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

    log.info("------------------------------------")
    if failed:
        log.warning("***************")
        log.warning("***************")
        log.warning("FAILURES DETECTED!!")  
        log.warning("Please review logs and setup.")
        log.warning("***************")
        log.warning("***************")
    else:
        log.info(" Diagnostics done.  All checks passed")
    log.info("------------------------------------\n\n")

def run(root, mountpoint, threading=True):
    global RUNNING
    #aostats.STATS = statsdict
    #import flighttrack
    #flighttrack.ft.running = flight_running

    if threading:
        log.info("Running in multi-threaded mode.")
        nothreads = False
    else:
        log.info("Running in single-threaded mode.")
        nothreads = True

    if platform.system() == 'Windows':
        systemtype, libpath = winsetup.find_win_libs()
        if systemtype == "dokan-FUSE":
            # Windows user mode FS support is kind of a mess, so try a few things.
            log.info("Running in Windows FUSE mode with Dokan.")
            os.environ['FUSE_LIBRARY_PATH'] = libpath
            root = os.path.expanduser(root)
            mountpoint = os.path.expanduser(mountpoint)
            ret = winsetup.setup_dokan_mount(mountpoint)
            if not ret:
                log.error(f"Mount point setup failed for {mountpoint}!")
                RUNNING = False
                return
            log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
            import autoortho_fuse
            from refuse import high
            high._libfuse = ctypes.CDLL(libpath)
            autoortho_fuse.run(
                    autoortho_fuse.AutoOrtho(root), 
                    mountpoint, 
                    nothreads
            )
        elif systemtype == "winfsp-FUSE":
            log.info("Running in Windows FUSE mode with WinFSP.")
            os.environ['FUSE_LIBRARY_PATH'] = libpath
            root = os.path.expanduser(root)
            mountpoint = os.path.expanduser(mountpoint)
            ret = winsetup.setup_winfsp_mount(mountpoint) 
            if not ret:
                log.error(f"Mount point setup failed for {mountpoint}!")
                RUNNING = False
                return
            log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
            import autoortho_fuse
            from refuse import high
            high._libfuse = ctypes.CDLL(libpath)
            autoortho_fuse.run(
                    autoortho_fuse.AutoOrtho(root), 
                    mountpoint, 
                    nothreads
            )
        else:
            log.error(f"Unknown mount type of {systemtype}!")
            time.sleep(5)
            sys.exit(1)
    else:
        log.info("Running in FUSE mode.")
        root = os.path.expanduser(root)
        mountpoint = os.path.expanduser(mountpoint)
    
        if not os.path.exists(mountpoint):
            os.makedirs(mountpoint)
        if not os.path.isdir(mountpoint):
            log.error(f"WARNING: {mountpoint} is not a directory.  Exiting.")
            sys.exit(1)

        log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
        import autoortho_fuse
        autoortho_fuse.run(
                autoortho_fuse.AutoOrtho(root),
                mountpoint, 
                nothreads
        )

def unmount(mountpoint):
    mounted = True
    while mounted:
        print(f"Shutting down {mountpoint}")
        print("Send poison pill ...")
        mounted = os.path.isfile(os.path.join(
            mountpoint,
            ".poison"
        ))
        time.sleep(0.5)


def main():
    log.info(f"AutoOrtho version: {__version__}")

    parser = argparse.ArgumentParser(
        description="AutoOrtho: X-Plane scenery streamer"
    )
    parser.add_argument(
        "root",
        help = "Root directory of orthophotos",
        nargs="?"
    )
    parser.add_argument(
        "mountpoint",
        help = "Directory within X-Plane 11 custom scenery folder to mount",
        nargs="?"
    )
    parser.add_argument(
        "-c",
        "--configure",
        default=False,
        action="store_true",
        help = "Run the configuration setup again."
    )
    parser.add_argument(
        "-H",
        "--headless",
        default=False,
        action="store_true",
        help = "Run in headless mode."
    )

    args = parser.parse_args()

    CFG = aoconfig.CFG
    cfgui = config_ui.ConfigUI(CFG)
    if (not CFG.ready) or args.configure or (CFG.general.showconfig and not args.headless):
        cfgui.setup(headless = args.headless)

    if not args.root or not args.mountpoint:
        cfgui.verify()
    else:
        root = args.root
        mountpoint = args.mountpoint
        print("root:", root)
        print("mountpoint:", mountpoint)


    stats = aostats.AOStats()

    if not CFG.scenery_mounts:
        log.warning(f"No installed sceneries detected.  Exiting.")
        sys.exit(0)

    #if CFG.cache.clean_on_start:
    #    aoconfig.clean_cache(CFG.paths.cache_dir, int(float(CFG.cache.file_cache_size)))

    import flighttrack
    ftrack = threading.Thread(
        target=flighttrack.run,
        daemon=True
    )
    ftrack.start()
    
    stats.start()
   
    global RUNNING
    RUNNING = True
    do_threads = True
    if do_threads:
        mount_threads = []
        for scenery in CFG.scenery_mounts:
            t = threading.Thread(
                target=run,
                daemon=False,
                args=(
                    scenery.get('root'), 
                    scenery.get('mount'), 
                    CFG.fuse.threading
                )
            )
            t.start()
            mount_threads.append(t)
        
        try:
            def handle_sigterm(sig, frame):
                raise(SystemExit)

            signal.signal(signal.SIGTERM, handle_sigterm)
            
            time.sleep(1)
            # Check things out
            diagnose(CFG)

            while RUNNING:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            RUNNING = False
            pass
        finally:
            log.info("Shutting down ...")
            for scenery in CFG.scenery_mounts:
                unmount(scenery.get('mount'))
            for t in mount_threads:
                t.join(5)
                print(f"Thread {t.ident} exited.")
    else:
        scenery = CFG.scenery_mounts[0]
        run(
            scenery.get('root'), 
            scenery.get('mount'), 
            CFG.fuse.threading
        )
        
    stats.stop()
    flighttrack.ft.stop()


if __name__ == '__main__':
    main()
