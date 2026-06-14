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

# macOS Apple Silicon premium blue theme
AO_MAC_THEME = {
    "BACKGROUND": "#07111F",
    "TEXT": "#EAF3FF",
    "INPUT": "#0E1E33",
    "TEXT_INPUT": "#EAF3FF",
    "SCROLL": "#12375A",
    "BUTTON": ("#F7FBFF", "#1677FF"),
    "PROGRESS": ("#1677FF", "#0E1E33"),
    "BORDER": 1,
    "SLIDER_DEPTH": 0,
    "PROGRESS_DEPTH": 0,
}

def apply_ao_mac_theme():
    try:
        sg.theme_add_new("AutoOrthoSiliconBlue", AO_MAC_THEME)
        sg.theme("AutoOrthoSiliconBlue")
        sg.set_options(
            font=("SF Pro Text", 13),
            element_padding=(8, 6),
            margins=(12, 12),
            button_color=("#F7FBFF", "#1677FF"),
            input_elements_background_color="#0E1E33",
            input_text_color="#EAF3FF",
            text_color="#EAF3FF",
            background_color="#07111F",
        )
    except Exception as err:
        print("Theme setup ignored:", repr(err))

apply_ao_mac_theme()

AO_BG = "#07111F"
AO_PANEL = "#0B1829"
AO_INPUT = "#0E1E33"
AO_TEXT = "#EAF3FF"
AO_MUTED = "#A9C7E8"
AO_BLUE = "#1677FF"
AO_BLUE_DARK = "#0A4FA3"
AO_BORDER = "#12375A"
AO_BUTTON = ("#F7FBFF", AO_BLUE)

AO_TITLE_TEXT = "Auto Ortho for Silicon Mac"
AO_SUBTITLE_TEXT = "Kext-free FUSE-T scenery streaming for X-Plane 12"



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
            sg.theme("AutoOrthoSiliconBlue")

        self.scenery_q = queue.Queue()

        if platform.system() == 'Windows':
            self.icon_path =os.path.join(CUR_PATH, 'imgs', 'ao-icon.ico')
        else:
            self.icon_path = os.path.join(CUR_PATH, 'imgs', 'pygui_icon.png')

    def start_splash(self):
        splash_path = os.path.join(CUR_PATH, 'imgs', 'splash_silicon_mac_titled_2x.png')

        # PySimpleGUI's transparent_color option is Windows-only.
        # On macOS it raises:
        #   Transparent color not supported on this platform (windows only)
        # which prevents the config GUI from staying open.
        window_args = {
            'title': 'Window Title',
            'layout': [[sg.Image(splash_path, subsample=2)]],
            'no_titlebar': True,
            'keep_on_top': True,
            'finalize': True,
        }

        if platform.system() == 'Windows':
            window_args['transparent_color'] = sg.theme_background_color()

        self.splash_w = sg.Window(**window_args, background_color=AO_BG)
        event, values = self.splash_w.read(timeout=3000)
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
        global os
        # Main GUI loop
       
        scenery_path = self.cfg.paths.scenery_path
        showconfig = self.cfg.general.showconfig
        maptype = self.cfg.autoortho.maptype_override
        maptypes = ['', 'BI', 'NAIP', 'EOX', 'USGS', 'Firefly'] 

        sg.theme("AutoOrthoSiliconBlue")

        #
        # Setup/config tab
        #
        setup = [
            [
                sg.Frame(
                    '',
                    [
                        [
                            sg.Image(os.path.join(CUR_PATH, 'imgs', 'banner1_gui_small.png'), background_color=AO_PANEL, pad=((4, 10), (6, 6))),
                            sg.Column(
                                [
                                    [
                                        sg.Text(
                                            'AutoOrtho',
                                            font=("SF Pro Display", 24, "bold"),
                                            text_color=AO_TEXT,
                                            background_color=AO_PANEL,
                                            pad=((8, 8), (4, 0)),
                                        )
                                    ],
                                    [
                                        sg.Text(
                                            'FOR X-PLANE',
                                            font=("SF Pro Text", 11, "bold"),
                                            text_color=AO_BLUE,
                                            background_color=AO_PANEL,
                                            pad=((10, 8), (0, 0)),
                                        )
                                    ],
                                    [
                                        sg.Text(
                                            'Apple Silicon Mac Edition',
                                            font=("SF Pro Text", 12),
                                            text_color=AO_MUTED,
                                            background_color=AO_PANEL,
                                            pad=((10, 8), (2, 8)),
                                        )
                                    ],
                                    [
                                        sg.Text(
                                            'FUSE-T streaming • Live tile telemetry',
                                            font=("SF Pro Text", 10),
                                            text_color=AO_MUTED,
                                            background_color=AO_PANEL,
                                            pad=((10, 8), (0, 6)),
                                        )
                                    ],
                                ],
                                background_color=AO_PANEL,
                                pad=((12, 0), (0, 0)),
                            ),
                        ],
                    ],
                    background_color=AO_PANEL,
                    border_width=0,
                    pad=((6, 6), (6, 8)),
                )
            ],
            [sg.HorizontalSeparator(pad=5)],
            [
                sg.Text('Scenery install dir:', size=(11,1), background_color=AO_BG, text_color=AO_TEXT), 
                sg.InputText(scenery_path, size=(24,1), key='scenery_path',
                    metadata={'section':self.cfg.paths}), 
                sg.FolderBrowse("Browse", size=(7,1), key="scenery_b", target='scenery_path', initial_folder=scenery_path)
            ],
            [
                sg.Text('X-Plane install dir:', size=(11,1), background_color=AO_BG, text_color=AO_TEXT), 
                sg.InputText(self.cfg.paths.xplane_path, size=(24,1), key='xplane_path',
                    metadata={'section':self.cfg.paths}), 
                sg.FolderBrowse("Browse", size=(7,1), key="xplane_b", target='xplane_path', initial_folder=self.cfg.paths.xplane_path)
            ],
            [
                sg.Text('Image cache dir:', size=(11,1), background_color=AO_BG, text_color=AO_TEXT),
                sg.InputText(self.cfg.paths.cache_dir, size=(24,1),
                    key='cache_dir',
                    metadata={'section':self.cfg.paths}),
                sg.FolderBrowse("Browse", size=(7,1), key="cache_b", target='cache_dir',
                    initial_folder=self.cfg.paths.cache_dir)
            ],
            [
                sg.Text('Temp download dir:', size=(11,1), background_color=AO_BG, text_color=AO_TEXT),
                sg.InputText(self.cfg.paths.download_dir, size=(24,1),
                    key='download_dir',
                    metadata={'section':self.cfg.paths}),
                sg.FolderBrowse("Browse", size=(7,1), key="download_b", target='download_dir',
                    initial_folder=self.cfg.paths.download_dir)
            ],
            [sg.HorizontalSeparator(pad=5)],
            [sg.Checkbox('Always show config menu', key='showconfig',
                default=self.cfg.general.showconfig,
                metadata={'section':self.cfg.general})],
            [sg.Text('Map type override', background_color=AO_BG, text_color=AO_TEXT), sg.Combo(maptypes,
                default_value=maptype, key='maptype_override',
                metadata={'section':self.cfg.autoortho}, background_color=AO_INPUT, text_color=AO_TEXT, button_background_color=AO_BLUE)],
            [sg.HorizontalSeparator(pad=5)],
            [
                sg.Text('Cache size in GB', background_color=AO_BG, text_color=AO_TEXT),
                sg.Slider(
                    range=(10,500,5),
                    default_value=self.cfg.cache.file_cache_size, 
                    key='file_cache_size',
                    size=(20,15),
                    orientation='horizontal',
                    metadata={'section':self.cfg.cache}
                ),
                sg.Button('Clean Cache', button_color=AO_BUTTON)
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
                scenery.append([sg.Text(f"{latest.name} current version {r.local_rel.ver}", background_color=AO_BG, text_color=AO_TEXT)])
                if version.parse(latest.ver) > version.parse(r.local_rel.ver):
                    pending_update = True
        
            else:
                scenery.append([sg.Text(f"{latest.name}", background_color=AO_BG, text_color=AO_TEXT)])
                pending_update = True

            if pending_update:
                scenery.append([
                    sg.Text(
                        f"    Update {latest.ver} available • {latest.totalsize/1048576:.0f} MB",
                        key=f"updates-{r.region_id}",
                        background_color=AO_BG,
                        text_color=AO_TEXT,
                        expand_x=True,
                    ),
                    sg.Push(background_color=AO_BG),
                    sg.Button('Install', key=f"scenery-{r.region_id}", button_color=AO_BUTTON, size=(10,1)),
                ])
            else:
                scenery.append([sg.Text(f"    {r.region_id} is up to date!", background_color=AO_BG, text_color=AO_TEXT)])
            scenery.append([sg.HorizontalSeparator()])

        #scenery.append([sg.Output(size=(80,10))])
        #scenery.append([sg.Multiline(size=(80,10), key="output", background_color=AO_INPUT, text_color=AO_TEXT)])

        # Hack to push the status bar to the bottom of the window
        #scenery.append([sg.Text(key='-EXPAND-', font='ANY 1', pad=(0,0), background_color=AO_BG, text_color=AO_TEXT)])
        #scenery.append([sg.StatusBar("...", size=(44,3), key="status", auto_size_text=True, expand_x=True)])

        #
        # Console logs tab
        #
        logs = [
            [
                sg.Frame(
                    'Live Tile Telemetry',
                    [
                        [
                            sg.Text(
                                'Streaming cache activity, FUSE-T status, and AutoOrtho runtime logs',
                                font=("SF Pro Text", 10),
                                text_color=AO_MUTED,
                                background_color=AO_PANEL,
                            )
                        ],
                        [
                            sg.Multiline(
                                "",
                                key="log",
                                size=(56,14),
                                autoscroll=True,
                                reroute_stdout=True,
                                reroute_stderr=True,
                                expand_x=True,
                                expand_y=True,
                                background_color=AO_INPUT,
                                text_color=AO_TEXT,
                                font=("Menlo", 11),
                                border_width=0,
                            )
                        ],
                    ],
                    background_color=AO_PANEL,
                    title_color=AO_BLUE,
                    border_width=0,
                    expand_x=True,
                    expand_y=True,
                    pad=((6, 6), (6, 6)),
                )
            ]
        ]

        setup_column = sg.Column(
            setup,
            size=(700, 560),
            background_color=AO_BG,
            pad=(0, 0),
            scrollable=False,
        )

        scenery_column = sg.Column(
            scenery,
            size=(700, 560),
            scrollable=True,
            vertical_scroll_only=True,
            background_color=AO_BG,
            pad=(0, 0),
        )

        layout = [
            [
                sg.Frame(
                    '',
                    [
                        [
                            sg.Column(
                                [
                                    [
                                        sg.Text(
                                            'AutoOrtho for Silicon Mac',
                                            font=("SF Pro Display", 24, "bold"),
                                            text_color=AO_TEXT,
                                            background_color=AO_PANEL,
                                            pad=((0, 8), (0, 0)),
                                        ),
                                        sg.Text(
                                            'BETA',
                                            font=("SF Pro Text", 9, "bold"),
                                            text_color=AO_BG,
                                            background_color=AO_BLUE,
                                            pad=((8, 4), (7, 0)),
                                        ),
                                    ],
                                    [
                                        sg.Text(
                                            'Orthophoto streaming for X-Plane using Apple Silicon and FUSE-T',
                                            font=("SF Pro Text", 11),
                                            text_color=AO_MUTED,
                                            background_color=AO_PANEL,
                                            pad=((0, 8), (0, 0)),
                                        )
                                    ],
                                ],
                                background_color=AO_PANEL,
                                pad=((10, 4), (6, 4)),
                            ),
                            sg.Image(
                                os.path.join(CUR_PATH, 'imgs', 'pygui_icon_header.png'),
                                background_color=AO_PANEL,
                                pad=((4, 4), (4, 4)),
                            ),
                        ],
                    ],
                    background_color=AO_PANEL,
                    border_width=0,
                    pad=((6, 6), (6, 8)),
                )
            ],

            [sg.TabGroup(
                [[
                    sg.Tab('Setup', [[setup_column]], background_color=AO_BG, title_color=AO_TEXT), 
                    sg.Tab('Scenery', [[scenery_column]], background_color=AO_BG, title_color=AO_TEXT),
                    sg.Tab('Logs', logs, background_color=AO_BG, title_color=AO_TEXT)
                ]], tab_background_color=AO_PANEL, selected_title_color=AO_TEXT, selected_background_color=AO_BLUE)
            ],
            [sg.Text(key='-EXPAND-', font='ANY 1', pad=(0,0), background_color=AO_BG, text_color=AO_TEXT)],
            [
                sg.Button('Run', button_color=AO_BUTTON, size=(7,1), key='Run'),
                sg.Button('Save', button_color=AO_BUTTON, size=(7,1), key='Save'),
                sg.Button('Quit', button_color=AO_BUTTON, size=(7,1), key='Quit'),
                sg.Push(background_color=AO_BG),
            ],
            [sg.StatusBar("...", size=(44,3), key="status", auto_size_text=True, expand_x=True)],
            [
                sg.Checkbox(
                    'Stop AutoOrtho when X-Plane quits',
                    key='stop_on_xplane_quit',
                    default=True,
                    background_color=AO_BG,
                    text_color=AO_TEXT,
                    tooltip='When enabled, the Mac FUSE-T launcher automatically stops and unmounts after X-Plane closes.'
                )
            ],
            #[sg.StatusBar("...", size=(80,3), key="status", auto_size_text=True, expand_x=True)],

        ]

        font = ("Helventica", 14)
        self.window = sg.Window(f'AutoOrtho for Silicon Mac ver {__version__}', layout, font=font,
                finalize=True, icon=self.icon_path, background_color=AO_BG, size=(500,800), resizable=True)


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
                event, values = self.window.read(timeout=3000)

                try:
                    event_log_dir = pathlib.Path.home() / "Library" / "Logs" / "AutoOrthoSiliconMac"
                    event_log_dir.mkdir(parents=True, exist_ok=True)
                    with open(event_log_dir / "gui-events.log", "a", buffering=1, errors="replace") as event_log:
                        if event not in (None, "__TIMEOUT__"):
                            event_log.write(f"GUI event: {repr(event)}\n")
                except Exception:
                    pass

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

                    try:
                        _run_debug_dir = pathlib.Path.home() / "Library" / "Logs" / "AutoOrthoSiliconMac"
                        _run_debug_dir.mkdir(parents=True, exist_ok=True)
                        with open(_run_debug_dir / "run-debug.log", "a", buffering=1, errors="replace") as _run_debug:
                            _run_debug.write("RUN handler entered\n")
                    except Exception:
                        pass
                    print("Updating config.")
                    self.show_status("Updating config")
                    self.save()
                    self.cfg.load()

                    if platform.system() == 'Darwin':
                        script_path = os.path.join(CUR_PATH, "start_autoortho_mac_fuset.sh")

                        if not os.path.exists(script_path):
                            msg = (
                                "Config saved, but the Silicon Mac FUSE-T launcher was not found.\n\n"
                                f"Expected:\n{script_path}"
                            )
                            print(msg)
                            sg.popup(msg, title="AutoOrtho macOS Run")
                            self.show_status("Config saved. FUSE-T launcher missing.")
                            continue

                        try:
                            import subprocess
                            import sys
                            from pathlib import Path

                            stop_on_xplane_quit = "1" if values.get("stop_on_xplane_quit", True) else "0"

                            log_dir = Path.home() / "Library" / "Logs" / "AutoOrthoSiliconMac"
                            log_dir.mkdir(parents=True, exist_ok=True)
                            run_log = log_dir / "fuset-run.log"

                            launcher = os.path.join(CUR_PATH, "start_autoortho_mac_fuset.sh")

                            env = os.environ.copy()
                            env["AUTOORTHO_RUNTIME_PYTHON"] = sys.executable
                            env["STOP_ON_XPLANE_QUIT"] = stop_on_xplane_quit

                            with open(run_log, "a", buffering=1, errors="replace") as log:
                                log.write("\n=== AutoOrtho GUI Run clicked ===\n")
                                log.write(f"launcher={launcher}\n")
                                log.write(f"cwd={CUR_PATH}\n")
                                log.write(f"runtime_python={sys.executable}\n")
                                log.write(f"stop_on_xplane_quit={stop_on_xplane_quit}\n")

                                subprocess.Popen(
                                    ["/bin/bash", launcher],
                                    cwd=CUR_PATH,
                                    env=env,
                                    stdout=log,
                                    stderr=subprocess.STDOUT,
                                    start_new_session=True,
                                )

                            stop_msg = (
                                "AutoOrtho will stop automatically after X-Plane closes."
                                if stop_on_xplane_quit == "1"
                                else "AutoOrtho will keep running after X-Plane closes."
                            )

                            msg = (
                                "AutoOrtho Silicon Mac FUSE-T launcher started in the background.\n\n"
                                "Launch X-Plane after the status log shows AutoOrtho FUSE-T is running.\n"
                                f"{stop_msg}\n\n"
                                f"Run log: {run_log}"
                            )
                            print(msg)
                            self.show_status(f"AutoOrtho FUSE-T running. Log: {run_log}")

                            try:
                                self.window.bring_to_front()
                            except Exception:
                                pass
                        except Exception as err:
                            try:
                                _run_debug_dir = pathlib.Path.home() / "Library" / "Logs" / "AutoOrthoSiliconMac"
                                _run_debug_dir.mkdir(parents=True, exist_ok=True)
                                with open(_run_debug_dir / "run-debug.log", "a", buffering=1, errors="replace") as _run_debug:
                                    _run_debug.write(f"RUN handler exception: {repr(err)}\n")
                                    traceback.print_exc(file=_run_debug)
                            except Exception:
                                pass

                            msg = f"Could not start Silicon Mac FUSE-T launcher:\n\n{repr(err)}"
                            print(msg)
                            sg.popup(msg, title="AutoOrtho macOS Run Error")
                            self.show_status("Failed to start FUSE-T launcher.")

                        continue

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
                elif isinstance(event, str) and event.startswith("scenery-"):
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
        try:
            from pathlib import Path
            import glob
            import os

            sections = []

            try:
                log_file = self.cfg.paths.log_file
                if log_file and os.path.exists(log_file):
                    with open(log_file, "r", errors="replace") as f:
                        lines = f.readlines()[-100:]
                    sections.append("=== AutoOrtho log ===\n" + "".join(lines))
            except Exception as err:
                sections.append(f"=== AutoOrtho log ===\nCould not read app log: {repr(err)}\n")

            try:
                live_tile_candidates = [
                    os.path.expanduser("~/Library/Logs/AutoOrthoSiliconMac/autoortho-live-tiles.log"),
                    os.path.expanduser("~/Desktop/autoortho-live-tiles.log"),
                ]
                live_tile_log = next((p for p in live_tile_candidates if os.path.exists(p)), live_tile_candidates[0])

                if os.path.exists(live_tile_log):
                    with open(live_tile_log, "r", errors="replace") as f:
                        lines = f.readlines()[-180:]
                    sections.append("=== Live tile downloads ===\n" + "".join(lines))
                else:
                    sections.append(
                        "=== Live tile downloads ===\n"
                        "No live tile feed yet. Click Run to start the FUSE-T launcher.\n"
                    )
            except Exception as err:
                sections.append(f"=== Live tile downloads ===\nCould not read live tile log: {repr(err)}\n")

            try:
                fuse_logs = sorted(
                    glob.glob(os.path.expanduser("~/Library/Logs/AutoOrthoSiliconMac/autoortho-mac-fuset-*.log"))
                    + glob.glob(os.path.expanduser("~/Desktop/autoortho-mac-fuset-*.log"))
                )
                for fuse_log in fuse_logs[-3:]:
                    name = Path(fuse_log).name
                    with open(fuse_log, "r", errors="replace") as f:
                        lines = f.readlines()[-80:]
                    sections.append(f"=== FUSE-T log: {name} ===\n" + "".join(lines))
            except Exception as err:
                sections.append(f"=== FUSE-T logs ===\nCould not read FUSE-T logs: {repr(err)}\n")

            text = "\n\n".join(sections).strip() or "No logs available yet."
            self.log.update(text)

            try:
                self.log.Widget.see("end")
            except Exception:
                pass

        except Exception as err:
            print("update_logs ignored:", repr(err))



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
