#!/usr/bin/env python

import os
import sys
import platform
import argparse

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

    aoc = aoconfig.AOConfig(headless=args.headless)
    if (not aoc.ready) or args.configure or aoc.showconfig:
        aoc.setup()

    aoc.verify()
    aoc.prepdirs()

    root = aoc.root
    mountpoint = aoc.mountpoint


    print("root:", root)
    print("mountpoint:", mountpoint)


    if platform.system() == 'Windows':
        log.info("Running in Windows WinFSP mode.")
        import autoortho_winfsp
        autoortho_winfsp.main(root, mountpoint,
                maptype_override=aoc.autoortho.maptype_override)
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

        #nothreads=True
        nothreads=False

        log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
        autoortho_fuse.run(
                autoortho_fuse.AutoOrtho(root, maptype_override=aoc.autoortho.maptype_override), 
                mountpoint, 
                nothreads
        )

if __name__ == '__main__':
    main()
