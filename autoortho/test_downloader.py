#!/usr/bin/env python3

import os
import json
import zipfile
import pytest
import platform

import downloader
downloader.TESTMODE = True

def test_setup(tmpdir):
    pass

def test_list(tmpdir):
    d = downloader.Downloader(os.path.join(tmpdir, 'Custom Scenery'))
    d.region_list = ['test']
    d.find_releases()
    assert d.regions != {}

def test_fetch(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    dl_dir = os.path.join(tmpdir, 'downloads')
    d = downloader.Downloader(scenery_dir, dl_dir)

    d.region_list = ['test']
    d.find_releases()
    assert d.regions != {}

    r = d.regions.get('test')
    assert len(r.ortho_urls) == 1
    assert len(r.overlay_urls) == 1
    
    r.download()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip.00', 'z_test_00.zip']

    r.extract()
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

def test_bad_zip(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    dl_dir = os.path.join(tmpdir, 'downloads')
    d = downloader.Downloader(scenery_dir, dl_dir)

    d.region_list = ['test']
    d.find_releases()
   
    # First download the test region
    r = d.regions.get('test')
    r.download()
    downloads = os.listdir(dl_dir)
    downloads.sort()

    # Verify we have what we want
    assert downloads == ['y_test_overlays.zip.00', 'z_test_00.zip']
    
    # Corrupt the zip at the beginning
    with open(os.path.join(dl_dir, 'z_test_00.zip'), 'wb') as h:
        #h.seek(-8, 2)
        h.write(b'ZZZxxx000ZZZ')
    
    # This should fail, but preserve the good download
    r.extract()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip']
   
    # Redownload
    r.download()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip', 'y_test_overlays.zip.00', 'z_test_00.zip']
   
    # Corrup a zip at the end
    with open(os.path.join(dl_dir, 'z_test_00.zip'), 'rb+') as h:
        h.seek(-128, 2)
        h.write(b'ZZZxxx000ZZZ')

    r.extract()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip']

    # Redownload
    r.download()
    # One last extract
    r.extract()
    
    downloads = os.listdir(dl_dir)
    downloads.sort()

    # Clean download dir
    assert downloads == []
    
    # Proper dirs
    extracts = os.listdir(scenery_dir)
    extracts.sort()
    assert extracts == [
            'yAutoOrtho_Overlays', 'z_autoortho', 'z_test_00'
    ]
