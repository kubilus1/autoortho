#!/usr/bin/env python3

import os
import json
import zipfile
import pytest
import platform

import downloader


def test_setup(tmpdir):
    pass

def test_list(tmpdir):
    d = downloader.Downloader(os.path.join(tmpdir, 'Custom Scenery'))
    d.find_releases()
    assert d.regions != {}

def test_fetch(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    dl_dir = os.path.join(tmpdir, 'downloads')
    d = downloader.Downloader(scenery_dir, dl_dir)
    d.region_list = ['test']
    d.find_releases()
    assert d.regions != {}

    na = d.regions.get('test')
    assert len(na.ortho_urls) == 1
    assert len(na.overlay_urls) == 1
    
    d.download_region('test')
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip.00', 'z_test_00.zip']

    d.extract('test')
    extracts = os.listdir(scenery_dir)
    extracts.sort()
    assert extracts == [
            'yAutoOrtho_Overlays', 'z_autoortho', 'z_test_00'
    ]

    orthodetails = os.listdir(os.path.join(scenery_dir, "z_autoortho"))
    orthodetails.sort()


    if platform.system() == "Windows":
        assert orthodetails == ['_textures', 'test_info.json']
    else:
        assert orthodetails == ['_textures', 'test_info.json', 'textures']
        assert os.path.islink(os.path.join(scenery_dir, "z_test_00", "textures"))

