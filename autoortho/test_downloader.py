#!/usr/bin/env python3

import os
import json
import zipfile
import pytest
import platform
import shutil
from pathlib import Path

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

import downloader
downloader.TESTMODE = True

@pytest.fixture
def scenery_v1(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    with open(os.path.join('.','testfiles','infofiles','test_info_v1.json')) as h:
        info = json.loads(h.read())
    
    os.makedirs(os.path.join(scenery_dir, 'z_test_00', 'stuff'))
    os.makedirs(os.path.join(scenery_dir, 'z_test_01', 'stuff'))
    os.makedirs(os.path.join(scenery_dir, 'z_autoortho', '_textures'))
    os.makedirs(os.path.join(scenery_dir, 'z_autoortho', 'textures'))
   
    info['ortho_dirs'] = [
            os.path.join(scenery_dir, 'z_test_00'),
            os.path.join(scenery_dir, 'z_test_01'),
            os.path.join(scenery_dir, 'z_test_02'),
    ]

    with open(os.path.join(scenery_dir, 'z_autoortho', 'test_info.json'), 'w') as h:
        h.write(json.dumps(info))

    return scenery_dir


def test_v1_upgrade(scenery_v1):
    assert scenery_v1

    dl_dir = os.path.join(scenery_v1, '..', 'downloads')
    d = downloader.OrthoManager(scenery_v1, dl_dir)
    d.info_cache = os.path.join('.', 'testfiles', '.release_info')

    log.info("Find releases.")
    d.region_list = ['test']
    #d.find_releases()
    d.find_regions()
    region = d.regions.get('test')
    
    #log.info("Download release")
    #rel = region.get_latest_release()
    #rel.download()

    log.info("Install release")
    #rel.install()
    region.install_release()

    extracts = os.listdir(scenery_v1)
    extracts.sort()
    assert extracts == [
            'yAutoOrtho_Overlays', 'z_autoortho'
    ]

    scenery = os.listdir(os.path.join(scenery_v1, "z_autoortho", "scenery"))
    scenery.sort()
    assert scenery == ['z_ao_test']

    orthodetails = os.listdir(os.path.join(scenery_v1, "z_autoortho"))
    orthodetails.sort()
    assert orthodetails == ['scenery', 'test_info.json']

    log.info("Retry find releases")
    d.find_regions()
    region = d.regions.get('test')
    log.info("Retry install")
    region.install_release()


def test_upgrade(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    dl_dir = os.path.join(scenery_dir, '..', 'downloads')
    d = downloader.OrthoManager(scenery_dir, dl_dir)
    d.info_cache = os.path.join('.', 'testfiles', '.release_info')

    log.info("Find releases.")
    d.region_list = ['test']
    d.find_regions()
    region = d.regions.get('test')
    
    log.info("Install release")
    #region.install_release()
    rel = region.get_latest_release()
    rel.ver = "0.0.1"
    rel.download()
    rel.install()

    extracts = os.listdir(scenery_dir)
    extracts.sort()
    assert extracts == [
            'yAutoOrtho_Overlays', 'z_autoortho'
    ]

    scenery = os.listdir(os.path.join(scenery_dir, "z_autoortho", "scenery"))
    scenery.sort()
    assert scenery == ['z_ao_test']

    orthodetails = os.listdir(os.path.join(scenery_dir, "z_autoortho"))
    orthodetails.sort()
    assert orthodetails == ['scenery', 'test_info.json']

    
    log.info("Retry find releases")
    d = downloader.OrthoManager(scenery_dir, dl_dir)
    d.info_cache = os.path.join('.', 'testfiles', '.release_info')

    log.info("Find releases.")
    d.region_list = ['test']
    d.find_regions()
    region = d.regions.get('test')
    log.info("Update install")
    region.install_release()


def test_setup(tmpdir):
    pass

def test_list(tmpdir):
    d = downloader.OrthoManager(os.path.join(tmpdir, 'Custom Scenery'))
    d.info_cache = os.path.join('.', 'testfiles', '.release_info')
    d.region_list = ['test']
    d.find_regions()
    assert d.regions != {}

def test_fetch(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    dl_dir = os.path.join(tmpdir, 'downloads')
    d = downloader.OrthoManager(scenery_dir, dl_dir)
    d.info_cache = os.path.join('.', 'testfiles', '.release_info')

    d.region_list = ['test']
    d.find_regions()
    assert d.regions != {}

    r = d.regions.get('test')
    assert len(r.releases) == 1
    assert r.region_id == "test"
    #assert len(r.ortho_urls) == 2
    #assert len(r.overlay_urls) == 1
   
    rel = r.get_latest_release()
    rel.download()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip', 'z_test_00.zip', 'z_test_00.zip.sha256']
    #assert downloads == ['y_test_overlays.zip.00', 'z_test_00.zip', 'z_test_00.zip.sha256']
    #assert downloads == ['y_test_overlays.zip', 'z_test_00.zip']

    rel.install()
    extracts = os.listdir(scenery_dir)
    extracts.sort()
    assert extracts == [
            'yAutoOrtho_Overlays', 'z_autoortho'
    ]
    #assert extracts == [
    #        'yAutoOrtho_Overlays', 'z_autoortho'
    #]

    scenery = os.listdir(os.path.join(scenery_dir, "z_autoortho", "scenery"))
    scenery.sort()
    assert scenery == ['z_ao_test']

    scenery = os.listdir(os.path.join(scenery_dir, "z_autoortho", "scenery", "z_ao_test"))
    scenery.sort()
    assert scenery == ['Earth nav data', 'ORTHO_SETUP.md', 'terrain', 'textures']

    orthodetails = os.listdir(os.path.join(scenery_dir, "z_autoortho"))
    orthodetails.sort()
    assert orthodetails == ['scenery', 'test_info.json']


def test_bad_zip(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    dl_dir = os.path.join(tmpdir, 'downloads')
    d = downloader.OrthoManager(scenery_dir, dl_dir)
    d.info_cache = os.path.join('.', 'testfiles', '.release_info')

    d.region_list = ['test']
    d.find_regions()
   
    # First download the test region
    r = d.regions.get('test')
    rel = r.get_latest_release()
    rel.download()
    downloads = os.listdir(dl_dir)
    downloads.sort()

    # Verify we have what we want
    assert downloads == ['y_test_overlays.zip', 'z_test_00.zip', 'z_test_00.zip.sha256']
    #assert downloads == ['y_test_overlays.zip.00', 'z_test_00.zip', 'z_test_00.zip.sha256']
    #assert downloads == ['y_test_overlays.zip', 'z_test_00.zip']
    
    log.info("Corrupt at the beginning of file.")
    # Corrupt the zip at the beginning
    with open(os.path.join(dl_dir, 'z_test_00.zip'), 'wb') as h:
        #h.seek(-8, 2)
        h.write(b'ZZZxxx000ZZZ')
    
    # This should fail, but preserve the good download
    rel.install()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip']
  
    log.info("Redownload...")
    # Redownload
    rel.download()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    #assert downloads == ['y_test_overlays.zip', 'y_test_overlays.zip.00', 'z_test_00.zip', 'z_test_00.zip.sha256']
    #assert downloads == ['y_test_overlays.zip', 'y_test_overlays.zip.00', 'z_test_00.zip', 'z_test_00.zip.sha256']
    #assert downloads == ['y_test_overlays.zip']
    assert downloads == ['y_test_overlays.zip', 'z_test_00.zip', 'z_test_00.zip.sha256']

    log.info("Corrupt at the end of file.")
    # Corrupt a zip at the end
    with open(os.path.join(dl_dir, 'z_test_00.zip'), 'rb+') as h:
        h.seek(-128, 2)
        h.write(b'ZZZxxx000ZZZ')

    rel.install()
    downloads = os.listdir(dl_dir)
    downloads.sort()
    assert downloads == ['y_test_overlays.zip']

    log.info("Redownload...")
    # Redownload
    rel.download()
    # One last extract
    rel.install()
    
    downloads = os.listdir(dl_dir)
    downloads.sort()

    # Clean download dir
    assert downloads == []
    
    # Proper dirs
    extracts = os.listdir(scenery_dir)
    extracts.sort()
    assert extracts == [
            'yAutoOrtho_Overlays', 'z_autoortho'
    ]
    #assert extracts == [
    #        'yAutoOrtho_Overlays', 'z_autoortho'
    #]

    scenery = os.listdir(os.path.join(scenery_dir, "z_autoortho", "scenery"))
    scenery.sort()
    assert scenery == ['z_ao_test']


def test_find_regions(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    dl_dir = os.path.join(tmpdir, 'downloads')
    d = downloader.OrthoManager(scenery_dir, dl_dir)
    d.region_list = ['test']
    d.url = "https://api.github.com/repos/kubilus1/autoortho-scenery/releaseszz"
    d.info_cache = os.path.join('.', 'testfiles', '.release_info')

    d.find_regions()
    r = d.regions.get('test')
    assert r

    d.info_cache = 'notafile' 
    d.find_regions()


def test_package_assemble(tmpdir):
    p = downloader.Package(
        'atest',
        'y',
        os.path.join(tmpdir, 'downloads')
    )

    assert p
    
    p.zf.check = lambda : True

    log.info("Test normal download and assembly")
    for i in range(0,3):
        fpath = os.path.join(tmpdir, f"atest.zip.0{i}")
        with open(fpath, 'w') as h:
            h.write(f"{i}")
        url = Path(fpath).as_uri()
        p.remote_urls.append(url)

    p.download()
    p.check()
    assert os.path.isfile(os.path.join(tmpdir, 'downloads', 'atest.zip'))
    assert p.downloaded
    assert p.zf.assembled

    log.info("Test cleanup")
    p.cleanup()
    assert not p.downloaded
    assert not p.zf.assembled
    assert p.zf.files == []

    log.info("Test download with pre-existing")
    for i in range(0,2):
        fpath = os.path.join(tmpdir, 'downloads', f"atest.zip.0{i}")
        with open(fpath, 'w') as h:
            h.write(f"{i}")
    #     p.remote_urls.append(f"file://{fpath}")
    # 

    # p.remote_urls.append(f"file://{(os.path.join(tmpdir, 'atest.zip.03'))}")
    p.download()
    assert os.path.isfile(os.path.join(tmpdir, 'downloads', 'atest.zip'))
    assert p.downloaded
    assert p.zf.assembled


    p.cleanup()
    p.zf.check = lambda : False
    log.info("Test failed download and assembly")
    for i in range(0,3):
        fpath = os.path.join(tmpdir, f"atest.zip.0{i}")
        with open(fpath, 'w') as h:
            h.write(f"{i}")

    p.download()
    p.check()
    assert not os.path.isfile(os.path.join(tmpdir, 'downloads', 'atest.zip'))
    assert not p.downloaded
    assert not p.zf.assembled
