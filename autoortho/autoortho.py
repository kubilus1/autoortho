#!/usr/bin/env python

import os
import sys
import platform
import argparse
import threading

import aoconfig
import aostats
import flighttrack
import winsetup

import logging
log = logging.getLogger(__name__)

def main():

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
    cfgui = aoconfig.ConfigUI(CFG)
    if (not CFG.ready) or args.configure or (CFG.general.showconfig and not args.headless):
        cfgui.setup(headless = args.headless)

    if not args.root or not args.mountpoint:
        cfgui.verify()
        root = CFG.root
        mountpoint = CFG.mountpoint
    else:
        root = args.root
        mountpoint = args.mountpoint

    print("root:", root)
    print("mountpoint:", mountpoint)

    stats = aostats.AOStats()

    ftrack = threading.Thread(
        target=flighttrack.run,
        daemon=True
    )

    if CFG.fuse.threading:
        log.info("Running in multi-threaded mode.")
        nothreads = False
    else:
        log.info("Running in single-threaded mode.")
        nothreads = True

    if platform.system() == 'Windows':
        # Windows user mode FS support is kind of a mess, so try a few things.
        
        wintype, libpath = winsetup.find_win_libs()
        if wintype == "dokan-FUSE":
            log.info("Running in Windows FUSE mode with Dokan.")
            os.environ['FUSE_LIBRARY_PATH'] = libpath
            root = os.path.expanduser(root)
            mountpoint = os.path.expanduser(mountpoint)
            winsetup.setup_dokan_mount(mountpoint) 
            import autoortho_fuse
            stats.start()
            ftrack.start()
            log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
            autoortho_fuse.run(
                    autoortho_fuse.AutoOrtho(root), 
                    mountpoint, 
                    nothreads
            )
        elif wintype == "winfsp-FUSE":
            log.info("Running in Windows FUSE mode with WinFSP.")
            root = os.path.expanduser(root)
            mountpoint = os.path.expanduser(mountpoint)
            winsetup.setup_winfsp_mount(mountpoint) 
            import autoortho_fuse
            stats.start()
            ftrack.start()
            log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
            autoortho_fuse.run(
                    autoortho_fuse.AutoOrtho(root), 
                    mountpoint, 
                    nothreads
            )
        elif wintype == "winfsp-raw":
            log.info("Running in Windows WinFSP mode.")
            root = os.path.expanduser(root)
            mountpoint = os.path.expanduser(mountpoint)
            winsetup.setup_winfsp_mount(mountpoint) 
            import autoortho_winfsp
            stats.start()
            ftrack.start()
            log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
            autoortho_winfsp.main(root, mountpoint)
    else:
        log.info("Running in FUSE mode.")
        import autoortho_fuse
        root = os.path.expanduser(root)
        mountpoint = os.path.expanduser(mountpoint)
        nothreads=False
        if not os.path.exists(mountpoint):
            os.makedirs(mountpoint)
        if not os.path.isdir(mountpoint):
            log.error(f"WARNING: {mountpoint} is not a directory.  Exiting.")
            sys.exit(1)

        stats.start()
        ftrack.start()
        log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
        autoortho_fuse.run(
                autoortho_fuse.AutoOrtho(root), 
                mountpoint, 
                nothreads
        )

    flighttrack.ft.stop()
    stats.stop()


if __name__ == '__main__':
    main()
