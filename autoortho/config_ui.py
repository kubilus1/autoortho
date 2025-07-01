#!/usr/bin/env python3

import os
import sys
import time
import types
import queue
import pprint
import pathlib
import platform
import threading
import traceback
import subprocess
import configparser
import platform
from packaging import version

import logging
log = logging.getLogger(__name__)

import PySimpleGUI as sg

import downloader
from version import __version__

CUR_PATH = os.path.dirname(os.path.realpath(__file__))

class ConfigUI(object):
   
    status = None
    warnings = []
    errors = []
    show_errs = []
    window = None
    running = False
    ready = None
    splash_w = None

    def __init__(self, cfg):
        self.ready = threading.Event()
        self.ready.clear()
        
        self.start_splash()

        self.cfg = cfg
        self.dl = downloader.OrthoManager(
            self.cfg.paths.scenery_path,
            self.cfg.paths.download_dir,
            noclean = self.cfg.scenery.noclean
        )

        if self.cfg.general.gui:
            sg.theme('DarkAmber')

        self.scenery_q = queue.Queue()

        if platform.system() == 'Windows':
            self.icon_path =os.path.join(CUR_PATH, 'imgs', 'ao-icon.ico')
        else:
            self.icon_path =os.path.join(CUR_PATH, 'imgs', 'ao-icon.png')

    def start_splash(self):
        splash_path = os.path.join(CUR_PATH, 'imgs', 'splash.png')
        self.splash_w = sg.Window(
                'Window Title', [[sg.Image(splash_path, subsample=2)]], 
                transparent_color=sg.theme_background_color(), no_titlebar=True,
                keep_on_top=True, finalize=True
        )
        event, values = self.splash_w.read(timeout=100)
        return


    def setup(self):
        scenery_path = self.cfg.paths.scenery_path
        showconfig = self.cfg.general.showconfig
        maptype = self.cfg.autoortho.maptype_override

        if not os.path.exists(self.cfg.paths.cache_dir):
            os.makedirs(self.cfg.paths.cache_dir)

        self.ui_loop()


    def refresh_scenery(self):
        self.dl.regions = {}
        self.dl.extract_dir = self.cfg.paths.scenery_path
        self.dl.download_dir = self.cfg.paths.download_dir
        self.dl.find_regions()
        for r in self.dl.regions.values():
            latest = r.get_latest_release()
            latest.parse()


    def ui_loop(self):
        # Main GUI loop
       
        scenery_path = self.cfg.paths.scenery_path
        showconfig = self.cfg.general.showconfig
        maptype = self.cfg.autoortho.maptype_override
        maptypes = ['', 'BI', 'NAIP', 'EOX', 'USGS', 'Firefly', 'YNDX']

        sg.theme('DarkAmber')

        #
        # Setup/config tab
        #
        setup = [
            [
                #sg.Column(
                #    [
                #        [sg.Image(os.path.join(CUR_PATH, 'imgs', 'ao-icon.png'))],
                #        [sg.Text('AutoOrtho setup\n')]
                #    ]
                #),
                sg.Image(os.path.join(CUR_PATH, 'imgs', 'banner1.png'), subsample=2),
            ],
            #[sg.Text(f'ver: {__version__}')], 
            #[sg.Image(os.path.join(CUR_PATH, 'imgs', 'flight1.png'), subsample=3)],
            [sg.HorizontalSeparator(pad=5)],
            [
                sg.Text('Scenery install dir:', size=(18,1)), 
                sg.InputText(scenery_path, size=(45,1), key='scenery_path',
                    metadata={'section':self.cfg.paths}), 
                sg.FolderBrowse(key="scenery_b", target='scenery_path', initial_folder=scenery_path)
            ],
            [
                sg.Text('X-Plane install dir:', size=(18,1)), 
                sg.InputText(self.cfg.paths.xplane_path, size=(45,1), key='xplane_path',
                    metadata={'section':self.cfg.paths}), 
                sg.FolderBrowse(key="xplane_b", target='xplane_path', initial_folder=self.cfg.paths.xplane_path)
            ],
            [
                sg.Text('Image cache dir:', size=(18,1)),
                sg.InputText(self.cfg.paths.cache_dir, size=(45,1),
                    key='cache_dir',
                    metadata={'section':self.cfg.paths}),
                sg.FolderBrowse(key="cache_b", target='cache_dir',
                    initial_folder=self.cfg.paths.cache_dir)
            ],
            [
                sg.Text('Temp download dir:', size=(18,1)),
                sg.InputText(self.cfg.paths.download_dir, size=(45,1),
                    key='download_dir',
                    metadata={'section':self.cfg.paths}),
                sg.FolderBrowse(key="download_b", target='download_dir',
                    initial_folder=self.cfg.paths.download_dir)
            ],
            [sg.HorizontalSeparator(pad=5)],
            [sg.Checkbox('Always show config menu', key='showconfig',
                default=self.cfg.general.showconfig,
                metadata={'section':self.cfg.general})],
            [sg.Text('Map type override'), sg.Combo(maptypes,
                default_value=maptype, key='maptype_override',
                metadata={'section':self.cfg.autoortho})],
            [sg.HorizontalSeparator(pad=5)],
            [
                sg.Text('Cache size in GB'),
                sg.Slider(
                    range=(10,500,5),
                    default_value=self.cfg.cache.file_cache_size, 
                    key='file_cache_size',
                    size=(20,15),
                    orientation='horizontal',
                    metadata={'section':self.cfg.cache}
                ),
                sg.Button('Clean Cache')
                #sg.InputText(
                #    self.cfg.cache.file_cache_size, 
                #    key='file_cache_size',
                #    size=(5,1),
                #    metadata={'section':self.cfg.cache}
                #),
            ],
            #[
            #    sg.Checkbox('Cleanup cache on start', key='clean_on_start',
            #        default=self.cfg.cache.clean_on_start,
            #        metadata={'section':self.cfg.cache}
            #    ),
            #],
            [sg.HorizontalSeparator(pad=5)],

        ]

        #
        # Setup scenery tab
        #
        scenery = [
        ]
        self.dl.find_regions()
        for r in self.dl.regions.values():
            latest = r.get_latest_release()
            #latest = r.releases[0]
            latest.parse()
            pending_update = False
            if r.local_rel:
                # We have a local install
                scenery.append([sg.Text(f"{latest.name} current version {r.local_rel.ver}")])
                if version.parse(latest.ver) > version.parse(r.local_rel.ver):
                    pending_update = True
        
            else:
                scenery.append([sg.Text(f"{latest.name}")])
                pending_update = True

            if pending_update:
                scenery.append([sg.Text(f"    Available update ver: {latest.ver}, size: {latest.totalsize/1048576:.2f} MB, downloads: {latest.download_count}", key=f"updates-{r.region_id}"), sg.Button('Install', key=f"scenery-{r.region_id}")])
            else:
                scenery.append([sg.Text(f"    {r.region_id} is up to date!")])
            scenery.append([sg.HorizontalSeparator()])

        #scenery.append([sg.Output(size=(80,10))])
        #scenery.append([sg.Multiline(size=(80,10), key="output")])

        # Hack to push the status bar to the bottom of the window
        #scenery.append([sg.Text(key='-EXPAND-', font='ANY 1', pad=(0,0))])
        #scenery.append([sg.StatusBar("...", size=(74,3), key="status", auto_size_text=True, expand_x=True)])

        #
        # Console logs tab
        #
        logs = [
            [sg.Multiline(
                "",
                key="log",
                size=(80,20),
                autoscroll=True,
                reroute_stdout=True,
                reroute_stderr=True,
                #echo_stdout_stderr=True,
                expand_x=True,
                expand_y=True
                )
            ]
        ]

        scenery_column = sg.Column(scenery, expand_x=True, expand_y=True, scrollable=True, vertical_scroll_only=True)
        layout = [
            [sg.TabGroup(
                [[
                    sg.Tab('Setup', setup), 
                    sg.Tab('Scenery', [[scenery_column]]),
                    sg.Tab('Logs', logs)
                ]])
            ],
            [sg.Text(key='-EXPAND-', font='ANY 1', pad=(0,0))],
            [sg.StatusBar("...", size=(74,3), key="status", auto_size_text=True, expand_x=True)],
            [sg.Button('Run'), sg.Button('Save'), sg.Button('Quit')]
            #[sg.StatusBar("...", size=(80,3), key="status", auto_size_text=True, expand_x=True)],

        ]

        font = ("Helventica", 14)
        self.window = sg.Window(f'AutoOrtho Setup ver {__version__}', layout, font=font,
                finalize=True, icon=self.icon_path)


        #print = lambda *args, **kwargs: window['output'].print(*args, **kwargs)
        self.window['-EXPAND-'].expand(True, True, True)
        self.status = self.window['status']
        self.log = self.window['log']
        
        self.running = True
        close = False

        scenery_t = threading.Thread(target=self.scenery_setup)
        scenery_t.start()

        if self.splash_w is not None:
            # GUI starting, close splash screen
            self.splash_w.close()
        
        self.ready.set()

        try:
            while self.running:
                event, values = self.window.read(timeout=1000)
                #log.info(f'VALUES: {values}')
                #print(f"VALUES {values}")
                #print(f"EVENT: {event}")
                if event == sg.WIN_CLOSED:
                    print("Exiting ...")
                    #print("Not saving changes ...")
                    #self.show_status("Exiting")
                    close = True
                    self.running = False
                elif event == 'Quit':
                    self.show_status("Quiting")
                    print("Quiting ...")
                    close = True
                    self.running = False
                    self.show_status("Quiting")
                elif event == "Run":
                    print("Updating config.")
                    self.show_status("Updating config")
                    self.save()
                    self.cfg.load()
                    self.show_status("Mounting sceneries")
                    self.mount_sceneries(blocking=False)
                    self.show_status("Verifying")
                    self.verify()
                    self.show_status("Running")
                    self.window.minimize()
                elif event == 'Save':
                    print("Updating config.")
                    self.show_status("Updating config")
                    self.save()
                    self.cfg.load()
                    print(self.cfg.paths)
                elif event == 'Clean Cache':
                    self.show_status("Cleaning cache")
                    cbutton = self.window["Clean Cache"]
                    rbutton = self.window["Run"]
                    cbutton.update("Working")
                    cbutton.update(disabled=True)
                    rbutton.update(disabled=True)
                    self.window.refresh()
                    self.clean_cache(
                        self.cfg.paths.cache_dir,
                        int(float(self.cfg.cache.file_cache_size))
                    )
                    sg.popup("Done cleaning cache!")
                    cbutton.update("Clean Cache")
                    cbutton.update(disabled=False)
                    rbutton.update(disabled=False)
                elif event.startswith("scenery-"):
                    self.save()
                    self.cfg.load()
                    button = self.window[event]
                    button.update(disabled=True)
                    regionid = event.split("-")[1]
                    self.scenery_q.put(regionid)
                elif self.show_errs:
                    font = ("Helventica", 14)
                    sg.popup("\n".join(self.show_errs), title="ERROR!", font=font)
                    self.show_errs.clear()

                self.update_logs()
                self.window.refresh()
        finally:
            log.info("GUI exiting...")
            self.stop()
            log.info("Join scenery thread")
            scenery_t.join()
            log.info("Exiting UI")


    def stop(self):
        self.running = False
        self.unmount_sceneries()
        self.window.close()


    def update_logs(self):
        with open(self.cfg.paths.log_file) as h:
            lines = h.readlines()[-25:]
        self.log.update(''.join(lines))


    def scenery_setup(self):
        while self.running:
            try:
                regionid = self.scenery_q.get(timeout=2)
            except:
                continue

            self.scenery_dl = True
            t = threading.Thread(target=self.region_progress, args=(regionid,))
            t.start()
            
            button = self.window[f"scenery-{regionid}"]
            try:
                button.update("Working")
                self.dl.download_dir = self.cfg.paths.download_dir
               
                region = self.dl.regions.get(regionid)
                if not region.install_release():
                    print("Errors detected!")
                    status = downloader.cur_activity.get('status')
                    self.status.update(status)
                    self.show_errs.append(status)
                    button.update("Retry?")
                    button.update(disabled=False)
                    continue
                
                button.update(visible=False)
                updates = self.window[f"updates-{regionid}"]
                updates.update("Updated!")
                self.status.update(f"Done!")

            except Exception as err:
                button.update("ERROR!")
                tb = traceback.format_exc()
                self.status.update(err)
                self.warnings.append(f"Failed to setup scenery {regionid}")
                self.warnings.append(str(err))
                self.show_errs.append(str(tb))
                log.error(tb)
            finally:
                self.scenery_dl = False
            t.join()

    
    def region_progress(self, regionid):
        r = self.dl.regions.get(regionid)
        while self.scenery_dl:
            status = downloader.cur_activity.get('status')
            pcnt_done = downloader.cur_activity.get('pcnt_done', 0)
            MBps = downloader.cur_activity.get('MBps', 0)
            self.status.update(f"{status}")
            time.sleep(1)


    def save(self):
        # Pull info from UI into AOConfig object and save config
        self.ready.clear()
        event, values = self.window.read(timeout=10)
        #print(f"Reading values: {values}")
        #print(f"Reading events: {event}")
        for k,v in values.items():
            metadata = self.window[k].metadata
            if not metadata:
                continue
            
            cfgsection = metadata.get('section')
            if cfgsection:
                cfgsection.__dict__[k] = v 
        self.cfg.save()
        self.ready.set()
        self.refresh_scenery()
        return


    def verify(self):
        self._check_xplane_dir(self.cfg.paths.xplane_path)
        for scenery in self.cfg.scenery_mounts:
            self._check_ortho_dir(scenery.get('root'))

        if not self.cfg.scenery_mounts:
            self.errors.append(f"No installed scenery detcted!")

        msg = []
        if self.warnings:
            msg.append("WARNINGS:")
            msg.extend(self.warnings)
            msg.append("\n")

        for warn in self.warnings:
            log.warning(warn)

        if self.errors:
            msg.append("ERRORS:")
            msg.extend(self.errors)
            msg.append("\nWILL EXIT DUE TO ERRORS")

        for err in self.errors:
            log.error(err)

        font = ("Helventica", 14)
        if msg:
            print(msg)
            if self.cfg.general.gui:
                sg.popup("\n".join(msg), title="WARNING!", font=font)

        if self.errors:
            log.error("ERRORS DETECTED.  Exiting.")
            sys.exit(1)


    def show_status(self, msg):
        log.info(msg)
        self.status.update(msg)
        self.window.refresh()


    def clean_cache(self, cache_dir, size_gb):

        self.show_status(f"Cleaning up cache_dir {cache_dir}.  Please wait ...")

        target_gb = max(size_gb, 10)
        target_bytes = pow(2,30) * target_gb

        cfiles = sorted(pathlib.Path(cache_dir).glob('**/*'), key=os.path.getmtime)
        if not cfiles:
            self.show_status(f"Cache is empty.")
            return

        cache_bytes = sum(file.stat().st_size for file in cfiles)
        cachecount = len(cfiles)
        avgcachesize = cache_bytes/cachecount
        self.show_status(f"Cache has {cachecount} files.  Total size approx {cache_bytes//1048576} MB.")

        empty_files = [ x for x in cfiles if x.stat().st_size == 0 ]
        self.show_status(f"Found {len(empty_files)} empty files to cleanup.")
        for file in empty_files:
            if os.path.exists(file):
                os.remove(file)

        if target_bytes > cache_bytes:
            self.show_status(f"Cache within size limits.")
            return

        to_delete = int(( cache_bytes - target_bytes ) // avgcachesize)

        self.show_status(f"Over cache size limit, will remove {to_delete} files.")
        self.status.update(cfiles[to_delete])
        for file in cfiles[:to_delete]:
            os.remove(file)

        self.status.update(f"Cache cleanup done.")


    def _check_ortho_dir(self, path):
        ret = True

        if not sorted(pathlib.Path(path).glob(f"Earth nav data/*/*.dsf")):
            self.warnings.append(f"Orthophoto dir {path} seems wrong.  This may cause issues.")
            ret =  False

        return ret


    def _check_xplane_dir(self, path):

        if not os.path.isdir(path):
            self.errors.append(f"XPlane install directory '{path}' is not a directory.")
            return False

        if not "Custom Scenery" in os.listdir(path):
            self.errors.append(f"XPlane install directory '{path}' seems wrong.")
            return False

        return True
