import os
import time
import pytest
import threading

import aoconfig
import config_ui

@pytest.fixture
def cfg(tmpdir):
    return aoconfig.AOConfig(os.path.join(tmpdir, '.aocfg'))



@pytest.fixture
def cfgui(tmpdir):
    cfg = aoconfig.AOConfig(os.path.join(tmpdir, '.aocfg'))
    cfgui = config_ui.ConfigUI(cfg)
    t = threading.Thread(daemon=True, target=cfgui.ui_loop)
    t.start()
    cfgui.ready.wait()

    yield cfgui
    cfgui.stop()
    t.join()


def test_cfg_init(cfg):
    assert cfg.ready
    assert os.path.isfile(cfg.conf_file)


def test_sections(cfg):
    assert cfg.paths
    assert cfg.paths.cache_dir
    assert cfg.autoortho
    assert cfg.pydds
    assert cfg.fuse
    assert cfg.general
    assert cfg.general.gui

    assert type(cfg.fuse.threading) == bool


def test_load(cfg):
    with open(cfg.conf_file, 'w') as h:
        h.write('[test]\n')
        h.write('foo=bar')

    cfg.load()
    assert cfg.test
    assert cfg.test.foo == 'bar'


def find_in_file(filename, line):
    lines = []
    with open(filename, 'r') as h:
        lines = h.readlines()

    found = False
    for l in lines:
        if l == line:
            found = True

    return found    


def test_save(cfg):

    assert cfg.general.gui == True

    cfg.general.gui = False
    cfg.save()

    assert find_in_file(cfg.conf_file, "gui = False\n")


def test_ui(cfgui, tmpdir):
    cachedir = os.path.join(tmpdir, 'cache')
    downloaddir = os.path.join(tmpdir, 'downloads')
    scenerydir = os.path.join(tmpdir, 'scenery')

    # Update config
    cfgui.window["maptype_override"].update("USGS")
    cfgui.window["cache_dir"].update(cachedir)
    cfgui.window["download_dir"].update(downloaddir)
    cfgui.window["scenery_path"].update(scenerydir)
    # Save
    cfgui.window["Save"].click()
    time.sleep(0.1)
    cfgui.ready.wait()
    # Verify
    assert find_in_file(cfgui.cfg.conf_file, "maptype_override = USGS\n")
    assert find_in_file(cfgui.cfg.conf_file, f"cache_dir = {cachedir}\n")
    assert find_in_file(cfgui.cfg.conf_file, f"download_dir = {downloaddir}\n")
    assert find_in_file(cfgui.cfg.conf_file, f"scenery_path = {scenerydir}\n")
    assert cfgui.cfg.autoortho.maptype_override == "USGS"
