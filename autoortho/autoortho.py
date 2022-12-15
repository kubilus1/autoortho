#!/usr/bin/env python

import os
import sys
import platform
import argparse
import threading

import logging
#logging.basicConfig()
logging.basicConfig(filename='autoortho.log')
log = logging.getLogger('log')
log.addHandler(logging.StreamHandler())

if os.environ.get('AO_DEBUG'):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

import aoconfig
import aostats

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

    #CFG = aoconfig.AOConfig(headless=args.headless)
    aoconfig.AOConfig(headless=args.headless)
    CFG = aoconfig.CFG
    if (not CFG.ready) or args.configure or CFG.showconfig:
        CFG.setup()

    if not args.root or not args.mountpoint:
        CFG.verify()
        CFG.prepdirs()

        root = CFG.root
        mountpoint = CFG.mountpoint
    else:
        root = args.root
        mountpoint = args.mountpoint

    print("root:", root)
    print("mountpoint:", mountpoint)


    stats = aostats.AOStats()
    stats.start()

    if platform.system() == 'Windows':
        log.info("Running in Windows WinFSP mode.")
        import autoortho_winfsp
        autoortho_winfsp.main(root, mountpoint)
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

    stats.stop()


if __name__ == '__main__':
    main()
