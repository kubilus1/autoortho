#!/usr/bin/env python

import os
import signal
import sys
import time
import platform
import argparse
import threading

import aoconfig
import aostats
import winsetup
import config_ui

import flighttrack
#import multiprocessing

import logging
log = logging.getLogger(__name__)

def run(root, mountpoint, threading=True):
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
            winsetup.setup_dokan_mount(mountpoint) 
            log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
            import autoortho_fuse
            autoortho_fuse.run(
                    autoortho_fuse.AutoOrtho(root), 
                    mountpoint, 
                    nothreads
            )
        elif systemtype == "winfsp-FUSE":
            log.info("Running in Windows FUSE mode with WinFSP.")
            root = os.path.expanduser(root)
            mountpoint = os.path.expanduser(mountpoint)
            winsetup.setup_winfsp_mount(mountpoint) 
            log.info(f"AutoOrtho:  root: {root}  mountpoint: {mountpoint}")
            import autoortho_fuse
            autoortho_fuse.run(
                    autoortho_fuse.AutoOrtho(root), 
                    mountpoint, 
                    nothreads
            )
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

            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            for scenery in CFG.scenery_mounts:
                mounted = True
                while mounted:
                    print(f"Shutting down {scenery.get('mount')}")
                    print("Send poison pill ...")
                    mounted = os.path.isfile(os.path.join(
                        scenery.get('mount'),
                        ".poison"
                    ))
                    time.sleep(0.5)

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
