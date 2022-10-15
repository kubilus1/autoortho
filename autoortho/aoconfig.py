import os
import sys
import types
import pathlib
import platform
import subprocess
import configparser

import logging
logging.basicConfig()
log = logging.getLogger('log')

import PySimpleGUI as sg

CUR_PATH = os.path.dirname(os.path.realpath(__file__))

class AOConfig(object):
   
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

        if headless:
            # Always disable GUI if set on as a CLI switch
            self.gui = False

        if self.gui:
            sg.theme('DarkAmber')


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

        orthos_path = self.paths.orthos_path
        scenery_path= self.paths.scenery_path
        showconfig = self.showconfig
        maptype = self.autoortho.maptype_override

        #maptypes = [None, 'BI', 'Arc', 'EOX', 'GO2', 'USGS'] 
        maptypes = [None, 'BI', 'Arc', 'EOX', 'USGS'] 

        if self.gui:
            sg.theme('DarkAmber')

            layout = [
                [sg.Text('AutoOrtho setup\n')],
                [sg.Image(os.path.join(CUR_PATH, 'imgs', 'flight1.png'), subsample=2)],
                [sg.HorizontalSeparator(pad=5)],
                [sg.Text('Orthophoto dir', size=(15,1)), sg.InputText(orthos_path, key='orthos'), sg.FolderBrowse(target='orthos', initial_folder=orthos_path)],
                [sg.Text('X-Plane scenery dir', size=(15,1)), sg.InputText(scenery_path, key='scenery'), sg.FolderBrowse(target='scenery', initial_folder=scenery_path)],
                [sg.HorizontalSeparator(pad=5)],
                [sg.Checkbox('Always show config menu', key='showconfig', default=self.showconfig)],
                [sg.Text('Map type override'), sg.Combo(maptypes, default_value=maptype, key='maptype')],
                [sg.HorizontalSeparator(pad=5)],
                [sg.Button('Fly'), sg.Button('Quit')]
            ]
            font = ("Helventica", 14)
            window = sg.Window('AutoOrtho Setup', layout, font=font)

            while True:
                event, values = window.read()
                #log.info(f'VALUES: {values}')
                #print(f"VALUES {values}")
                #print(f"EVENT: {event}")
                if event == sg.WIN_CLOSED:
                    print("Not saving changes ...")
                    break
                elif event == 'Quit':
                    print("Quiting ...")
                    sys.exit(0)
                    break
                elif event == "Fly":
                    print("Updating config.")
                    print(values)
                    orthos_path = values.get('orthos', orthos_path)
                    scenery_path = values.get('scenery', scenery_path)
                    showconfig = values.get('showconfig', showconfig)
                    maptype = values.get('maptype', maptype)

                    # if not self._check_ortho_dir(orthos_path):
                    #     sg.popup(f"Orthophoto dir {orthos_path} seems wrong.  This may cause issues.")

                    # if not self._check_xplane_dir(scenery_path):
                    #     sg.popup(f"XPlane Custom Scenery directory {scenery_path} seems wrong.  This may cause issues.")

                    break

            window.close()

        else:

            log.info("-"*28)
            log.info(f"Running setup!")
            log.info("-"*28)
            orthos_path = input(f"Enter path to your OrthoPhoto files ({orthos_path}) : ") or orthos_path
            scenery_path = input(f"Enter path to X-Plane 11 custom_scenery directory ({scenery_path}) : ") or scenery_path

        
        self.config['paths']['orthos_path'] = orthos_path
        self.config['paths']['scenery_path'] = scenery_path
        self.config['general']['showconfig'] = str(showconfig)
        self.config['autoortho']['maptype_override'] = maptype

        self.save()
        self.load()

    def verify(self):
        self._check_ortho_dir(self.paths.orthos_path)
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

        ortho_dirs = os.listdir(self.paths.orthos_path)

        log.info("Preparing directory structures....")

        if platform.system() == 'Windows':
            #if 'Earth nav data' in ortho_dirs:
            dest =  os.path.join(z_autoortho_path, 'Earth nav data')
            if not os.path.exists(dest):
                src = os.path.join(self.paths.orthos_path, 'Earth nav data')
                #subprocess.check_call(f'New-Item -ItemType Junction -Path "{dest}" -Target "{src}"', shell=True)
                subprocess.check_call(f'mklink /J "{dest}" "{src}"', shell=True)

            #if 'terrain' in ortho_dirs:
            dest = os.path.join(z_autoortho_path, 'terrain')
            if not os.path.exists(dest):
                src = os.path.join(self.paths.orthos_path, 'terrain')
                #subprocess.check_call(f'New-Item -ItemType Junction -Path "{dest}" -Target "{src}"', shell=True)
                subprocess.check_call(f'mklink /J "{dest}" "{src}"', shell=True)
                #subprocess.check_call(f'cmd /c mklink /J "{src}" "{dest}"', shell=True)

            # On Windows mount point cannot already exist
            if os.path.exists(os.path.join(z_autoortho_path, 'textures')):
                log.warning("Textures dir already exists.  This will likely break")
                if self.gui:
                    sg.popup("Textures dir already exists.  This will likely break")
        else:
            # On *nix mount point MUST already exist
            
            #if 'Earth nav data' in ortho_dirs:
            if not os.path.exists(os.path.join(z_autoortho_path, 'Earth nav data')):
                os.symlink(
                    os.path.join(self.paths.orthos_path, 'Earth nav data'),
                    os.path.join(z_autoortho_path, 'Earth nav data')
                )

            #if 'terrain' in ortho_dirs:
            src = os.path.join(self.paths.orthos_path, 'terrain')
            dest = os.path.join(z_autoortho_path, 'terrain')

            # Symlink won't work with XP11 due to relative pathing from terrain directory to textures 
            subprocess.check_call(f"rsync -a '{src}' '{z_autoortho_path}'", shell=True)
            
            if not os.path.exists(os.path.join(z_autoortho_path, 'textures')):
                os.makedirs(os.path.join(z_autoortho_path, 'textures'))

        log.info("Diretories are ready!")

        self.root = os.path.join(self.paths.orthos_path, 'textures')
        self.mountpoint = os.path.join(z_autoortho_path, 'textures')
