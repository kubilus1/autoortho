#!/usr/bin/env python

import os
import sys
import platform
import argparse
import threading

import aoconfig
import aostats
import flighttrack

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

    if not os.path.exists(CFG.z_autoortho_path):
        os.makedirs(CFG.z_autoortho_path)
    print("root:", root)
    print("mountpoint:", mountpoint)

    stats = aostats.AOStats()
    stats.start()

    ftrack = threading.Thread(
        target=flighttrack.run,
        daemon=True
    )
    ftrack.start()

    winfuse = True
    if platform.system() == 'Windows' and not winfuse:
        log.info("Running in Windows WinFSP mode.")
        import autoortho_winfsp
        autoortho_winfsp.main(root, mountpoint)
    elif platform.system() == 'Windows' and winfuse:
        log.info("Logging in FUSE mode.")
        import autoortho_fuse
        root = os.path.expanduser(root)
        mountpoint = os.path.expanduser(mountpoint)
        nothreads=False
        #if not os.path.exists(mountpoint):
        #    os.makedirs(mountpoint)
        #if not os.path.isdir(mountpoint):
        #    log.error(f"WARNING: {mountpoint} is not a directory.  Exiting.")
        #    sys.exit(1)

        if CFG.fuse.threading:
            log.info("Running in multi-threaded mode.")
            nothreads = False
        else:
            log.info("Running in single-threaded mode.")
            nothreads = True

        log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
        autoortho_fuse.run(
                autoortho_fuse.AutoOrtho(root), 
                mountpoint, 
                nothreads
        )
    else:
        log.info("Logging in FUSE mode.")
        import autoortho_fuse
        root = os.path.expanduser(root)
        mountpoint = os.path.expanduser(mountpoint)
        nothreads=False
        if not os.path.exists(mountpoint):
            os.makedirs(mountpoint)
        if not os.path.isdir(mountpoint):
            log.error(f"WARNING: {mountpoint} is not a directory.  Exiting.")
            sys.exit(1)


        if CFG.fuse.threading:
            log.info("Running in multi-threaded mode.")
            nothreads = False
        else:
            log.info("Running in single-threaded mode.")
            nothreads = True

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
