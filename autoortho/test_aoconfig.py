import os
import pytest

import aoconfig

@pytest.fixture
def cfg(tmpdir):
    return aoconfig.AOConfig(os.path.join(tmpdir, '.aocfg'))


def test_cfg_init(cfg):
    assert cfg.ready
    assert os.path.isfile(cfg.conf_file)


def test_sections(cfg):
    assert cfg.paths
    assert cfg.paths.cache_dir
    assert cfg.autoortho
    assert cfg.pydds
    assert cfg.fuse
    assert cfg.winfsp
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


def test_save(cfg):

    assert cfg.general.gui == True

    cfg.general.gui = False
    cfg.save()

    lines = []
    with open(cfg.conf_file, 'r') as h:
        lines = h.readlines()

    found = False
    for l in lines:
        if l == "gui = False\n":
            found = True

    assert found

