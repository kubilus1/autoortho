import os
import sys
import time
import types
import queue
import pathlib
import platform
import threading
import subprocess
import configparser


import logging
logging.basicConfig()
log = logging.getLogger('log')

import PySimpleGUI as sg
#print = sg.Print

import downloader

CUR_PATH = os.path.dirname(os.path.realpath(__file__))

class AOConfig(object):
   
    status = None

    warnings = []
    errors = []

    config = configparser.ConfigParser(strict=False, allow_no_value=True, comment_prefixes='/')
    conf_file = os.path.join(os.path.expanduser("~"), (".autoortho"))

    _defaults = """
[general]
# Use GUI config at startup
gui = True
# Show config setup at startup everytime
showconfig = True

[paths]
# Ortho photos path
orthos_path =
# X-Plane Custom Scenery path
scenery_path =

[autoortho]
# Override map type with a different source
maptype_override =
"""

    def __init__(self, headless=False):
        # Always load initially
        self.ready = self.load()
        self.dl = downloader.Downloader(self.paths.scenery_path)

        if headless:
            # Always disable GUI if set on as a CLI switch
            self.gui = False

        if self.gui:
            sg.theme('DarkAmber')

        self.running = True
        self.scenery_q = queue.Queue()


    def _check_ortho_dir(self, path):
        ret = True

        if not sorted(pathlib.Path(path).glob(f"Earth nav data/*/*.dsf")):
            self.warnings.append(f"Orthophoto dir {path} seems wrong.  This may cause issues.")
            ret =  False

        return ret

    def _check_xplane_dir(self, path):
        ret = True

        if os.path.basename(path) != "Custom Scenery":
            self.warnings.append(f"XPlane Custom Scenery directory {path} seems wrong.  This may cause issues.")
            ret = False

        return ret


    def setup(self):

        scenery_path = self.paths.scenery_path
        showconfig = self.showconfig
        maptype = self.autoortho.maptype_override

        maptypes = [None, 'BI', 'NAIP', 'Arc', 'GO2', 'EOX', 'USGS', 'Firefly'] 

        if self.gui:
            sg.theme('DarkAmber')

            setup = [
                [sg.Text('AutoOrtho setup\n')],
                [sg.Image(os.path.join(CUR_PATH, 'imgs', 'flight1.png'), subsample=2)],
                [sg.HorizontalSeparator(pad=5)],
                [sg.Text('X-Plane scenery dir', size=(18,1)), sg.InputText(scenery_path, key='scenery'), sg.FolderBrowse(target='scenery', initial_folder=scenery_path)],
                [sg.HorizontalSeparator(pad=5)],
                [sg.Checkbox('Always show config menu', key='showconfig', default=self.showconfig)],
                [sg.Text('Map type override'), sg.Combo(maptypes, default_value=maptype, key='maptype')],
                [sg.HorizontalSeparator(pad=5)],
            ]

            scenery = [
            ]
            self.dl.find_releases()
            for r in self.dl.regions.values():
                scenery.append([sg.Text(f"{r.info_dict.get('name', r)} current version {r.local_version}")])
                if r.pending_update:
                    scenery.append([sg.Text(f"    Available update ver: {r.latest_version}, size: {r.size/1048576:.2f} MB, downloads: {r.download_count}", key=f"updates-{r.region_id}"), sg.Button('Install', key=f"scenery-{r.region_id}")])
                else:
                    scenery.append([sg.Text(f"    {r.region_id} is up to date!")])
                scenery.append([sg.HorizontalSeparator()])

            #scenery.append([sg.Output(size=(80,10))])
            #scenery.append([sg.Multiline(size=(80,10), key="output")])
            scenery.append([sg.Text(key='-EXPAND-', font='ANY 1', pad=(0,0))])
            scenery.append([sg.StatusBar("...", size=(74,3), key="status", auto_size_text=True, expand_x=True)])

            logs = [
            ]

            layout = [
                [sg.TabGroup(
                    [[sg.Tab('Setup', setup), sg.Tab('Scenery', scenery)]])
                ],
                #[sg.StatusBar("...", size=(80,3), key="status", auto_size_text=True, expand_x=True)],
                [sg.Button('Fly'), sg.Button('Save'), sg.Button('Quit')]

            ]

            font = ("Helventica", 14)
            self.window = sg.Window('AutoOrtho Setup', layout, font=font, finalize=True)


            #print = lambda *args, **kwargs: window['output'].print(*args, **kwargs)
            self.window['-EXPAND-'].expand(True, True, True)
            self.status = self.window['status']

            t = threading.Thread(target=self.scenery_setup)
            t.start()

            close = False

            while True:
                event, values = self.window.read(timeout=100)
                #log.info(f'VALUES: {values}')
                #print(f"VALUES {values}")
                #print(f"EVENT: {event}")
                if event == sg.WIN_CLOSED:
                    print("Not saving changes ...")
                    close = True
                    break
                elif event == 'Quit':
                    print("Quiting ...")
                    close = True
                    break
                elif event == "Fly":
                    print("Updating config.")
                    print(values)
                    scenery_path = values.get('scenery', scenery_path)
                    showconfig = values.get('showconfig', showconfig)
                    maptype = values.get('maptype', maptype)

                    # if not self._check_ortho_dir(orthos_path):
                    #     sg.popup(f"Orthophoto dir {orthos_path} seems wrong.  This may cause issues.")

                    # if not self._check_xplane_dir(scenery_path):
                    #     sg.popup(f"XPlane Custom Scenery directory {scenery_path} seems wrong.  This may cause issues.")

                    break
                elif event == 'Save':
                    print("Updating config.")
                    print(values)
                    scenery_path = values.get('scenery', scenery_path)
                    showconfig = values.get('showconfig', showconfig)
                    maptype = values.get('maptype', maptype)
                    
                    self.dl.extract_dir = scenery_path
                    self.dl.find_releases
                    self.config['paths']['scenery_path'] = scenery_path
                    self.config['general']['showconfig'] = str(showconfig)
                    self.config['autoortho']['maptype_override'] = maptype
                    self.save()
                    self.load()
                elif event.startswith("scenery-"):
                    button = self.window[event]
                    button.update(disabled=True)
                    regionid = event.split("-")[1]
                    self.scenery_q.put(regionid)

                self.window.refresh()

            print("Exiting ...")
            self.running = False
            t.join()
            self.window.close()

            if close:
                sys.exit(0)

        else:

            log.info("-"*28)
            log.info(f"Running setup!")
            log.info("-"*28)
            scenery_path = input(f"Enter path to X-Plane 11 custom_scenery directory ({scenery_path}) : ") or scenery_path

        
        self.config['paths']['scenery_path'] = scenery_path
        self.config['general']['showconfig'] = str(showconfig)
        self.config['autoortho']['maptype_override'] = maptype

        self.save()
        self.load()

    def scenery_setup(self):

        while self.running:
            try:
                regionid = self.scenery_q.get(timeout=2)
            except:
                continue

            self.scenery_dl = True
            t = threading.Thread(target=self.region_progress, args=(regionid,))
            t.start()
            try:
                button = self.window[f"scenery-{regionid}"]
                button.update("Working")
                
                self.dl.download_region(regionid)
                self.dl.extract(regionid)
                self.dl.cleanup(regionid)
                
                button.update(visible=False)
                updates = self.window[f"updates-{regionid}"]
                updates.update("Updated!")

            except Exception as err:
                self.status.update(err)
            finally:
                self.scenery_dl = False
            t.join()

    
    def region_progress(self, regionid):
        r = self.dl.regions.get(regionid)
        while self.scenery_dl:
            status = r.cur_activity.get('status')
            pcnt_done = r.cur_activity.get('pcnt_done', 0)
            MBps = r.cur_activity.get('MBps', 0)
            self.status.update(f"{status}")
            time.sleep(1)
        

    def verify(self):
        self._check_xplane_dir(self.paths.scenery_path)

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
            if self.gui:
                sg.popup("\n".join(msg), title="WARNING!", font=font)

        if self.errors:
            log.error("ERRORS DETECTED.  Exiting.")
            sys.exit(1)


    def load(self):
        self.config.read_string(self._defaults)
        if os.path.isfile(self.conf_file):
            print(f"Config file found {self.conf_file} reading...") 
            log.info(f"Config file found {self.conf_file} reading...") 
            self.config.read(self.conf_file)
            ret = True
        else:
            print("No config file found. Using defaults...")
            log.info("No config file found. Using defaults...")
            ret = False

        config_dict = {sect: dict(self.config.items(sect)) for sect in
                self.config.sections()}

        self.paths = types.SimpleNamespace(**config_dict.get('paths'))
        self.autoortho = types.SimpleNamespace(**config_dict.get('autoortho'))
        #self.general = types.SimpleNamespace(**config_dict.get('general'))
        self.gui = self.config.getboolean('general', 'gui')
        self.showconfig = self.config.getboolean('general', 'showconfig')

        return ret


    def save(self):
        config_dict = {sect: dict(self.config.items(sect)) for sect in
                self.config.sections()}

        print(config_dict)
        with open(self.conf_file, 'w') as h:
            self.config.write(h)
        log.info(f"Wrote config file: {self.conf_file}")
        print(f"Wrote config file: {self.conf_file}")


    def prepdirs(self):
        z_autoortho_path = os.path.join(self.paths.scenery_path, 'z_autoortho')
        if not os.path.exists(z_autoortho_path):
            os.makedirs(z_autoortho_path)

        self.root = os.path.join(z_autoortho_path, '_textures')
        self.mountpoint = os.path.join(z_autoortho_path, 'textures')
        return



if __name__ == "__main__":

    aoc = AOConfig()
    aoc.setup()
    aoc.verify()
