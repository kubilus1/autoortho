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

    assert os.listdir(dl_dir) == ['z_test_00.zip', 'y_test_overlays.zip.00']

    d.extract('test')
    assert os.listdir(scenery_dir) == [
            'yAutoOrtho_Overlays', 'z_test_00', 'z_autoortho'
    ]

    assert os.listdir(os.path.join(scenery_dir, "z_autoortho")) == ['textures', 'test_info.json', '_textures']

    
    print(os.path.islink(os.path.join(scenery_dir, "z_test_00", "textures")))


    

    assert True == False
