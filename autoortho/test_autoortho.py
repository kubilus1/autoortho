#!/usr/bin/env python3

import os
import re
import time
import pytest
import shutil
import hashlib
import platform
from pathlib import Path
import threading
import subprocess
import random
import string
import tempfile

import autoortho
import aostats
from aoconfig import CFG

import logging
#logging.basicConfig()
log = logging.getLogger('log')
#log.setLevel(logging.DEBUG)
log.setLevel(logging.INFO)

from contextlib import contextmanager

@contextmanager
def pushd(new_dir):
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)

@pytest.fixture
def scenery_dir(tmpdir):
    scenery_dir = os.path.join(tmpdir, 'Custom Scenery')
    structure = [
        os.path.join(scenery_dir, 'z_autoortho', 'z_ao_test', 'Earth nav data'),
        os.path.join(scenery_dir, 'z_autoortho', 'z_ao_test', 'terrain'),
        os.path.join(scenery_dir, 'z_autoortho', 'z_ao_test', 'textures'),
    ]

    for d in structure:
        os.makedirs(d)

    return os.path.join(scenery_dir, 'z_autoortho', 'z_ao_test')

#@pytest.fixture(scope="module")
#def mount(tmpdir_factory):
#@pytest.mark.parametrize("prefer_winfsp", [True, False])
if platform.system() == "Windows":
    mount_params = [False, True]
else:
    mount_params = [False]

@pytest.fixture(params=mount_params)
def mount(tmpdir, request, scenery_dir):

    #tmpdir = tmpdir_factory.mktemp("mount")

    mountdir = str(os.path.abspath(os.path.join(tmpdir, 'mount')))
    cachedir = str(os.path.join(tmpdir, 'cache'))
    #rootdir = os.path.abspath('./testfiles')
    rootdir = scenery_dir

    prefer_winfsp = request.param
    
    if not prefer_winfsp:
        log.info(f"SETTING UP {mountdir}")
        os.makedirs(mountdir)
    else:
        if os.path.lexists(mountdir):
            os.rmdir(mountdir)
        log.info(f"NOT SETTING UP {mountdir}")

    os.makedirs(cachedir)
    CFG.paths.cache_dir = cachedir
    CFG.windows.prefer_winfsp = prefer_winfsp 

    try:
        t = threading.Thread(
            daemon = True,
            target = autoortho.run,
            args = (rootdir, mountdir)
        )

        t.start()
        time.sleep(1)

        yield mountdir

    finally:
        log.debug(f"Unmount {mountdir}")
        autoortho.unmount(mountdir)
        t.join(1)



def _test_stuff():
    assert 1 == 1


def _test_read_dsf(mount):
    dsf_file = './testfiles/dsftest/+00-051.dsf'
    ter_dir = './testfiles/dsftest/' 

    with open(dsf_file, encoding='utf-8', errors='ignore') as h:
        ter_files = re.findall("terrain\W?\d+[-_]\d+[-_]\D*\d+\w*\.ter", h.read())


    dds_full_paths = set()
    log.info(f"DSF: found {len(ter_files)} terrain files.  Parsing ...")
    for t in ter_files:
        ter_path = os.path.join(ter_dir, t) 
        #log.debug(f"Checking {ter_path}...")
        with open(ter_path) as h:
            dds_files = re.findall("\S*/\d+[-_]\d+[-_]\D*\d+.dds", h.read())
            log.info(f"Found: {dds_files}")
            for dds in dds_files:
                dds_full_paths.add(
                    os.path.join(mount, os.path.basename(dds))
                ) 

    print(dds_full_paths)
    print(len(dds_full_paths))

    #CFG.pydds.compressor = "STB"
    for dds in dds_full_paths:
        rc = subprocess.call(
            f"identify {dds}",
            shell=True
        )

    log.info(f"FINAL STATS: ID: {aostats.STATS}")
    #assert True == False


def test_autoortho(mount):
    print(mount)

    things = os.listdir(mount)
    print(things)
    
    rc = subprocess.call(
        f"identify {mount}/3232_2176_Null13.dds",
        shell=True
    )

    assert rc == 0

def test_read_header(mount):
    things = os.listdir(mount)
  
    testfile = f"{mount}/24832_12416_BI16.dds"

    stat = os.stat(testfile)
    size = stat.st_size

    blocksize = 16384

    blocks = size//blocksize
    remainder = size%blocksize

    with open(testfile, "rb") as h:
        header = h.read(blocksize)

    rc = subprocess.call(
        f"identify {testfile}", 
        shell=True
    )

    assert rc == 0

def test_read_mip0(mount):
    things = os.listdir(mount)
  
    testfile = f"{mount}/24832_12416_BI16.dds"

    stat = os.stat(testfile)
    size = stat.st_size

    blocksize = 16384

    blocks = size//blocksize
    remainder = size%blocksize

    with open(testfile, "rb") as h:
        data = h.read(blocksize)
        data = h.read(blocksize)

    #assert True == False

    rc = subprocess.call(
        f"identify {testfile}", 
        shell=True
    )

    assert rc == 0

def test_read_mip1(mount, tmpdir):
    things = os.listdir(mount)
  
    testfile = f"{mount}/24832_12416_BI16.dds"

    stat = os.stat(testfile)
    size = stat.st_size

    blocksize = 4096

    blocks = size//blocksize
    remainder = size%blocksize

    mipmapsize = 4194304
    
    with open(testfile, "rb") as h:
        data = h.read(128)
        print(data)
        print(f"DATA LEN: {len(data)}")
        h.seek(16777344)
        data = h.read(mipmapsize)
        print(f"DATA LEN: {len(data)}")

    with open(testfile, "rb") as read_h:
        with open(f"{tmpdir}/testmip1.dds", 'wb') as write_h:
            write_h.write(read_h.read(128))
            read_h.seek(16777344)
            write_h.seek(16777344)
            write_h.write(read_h.read(mipmapsize))
            write_h.seek(22369870)
            write_h.write(b'x\00')

    rc = subprocess.call(
        f"identify -verbose {testfile}", 
        shell=True
    )
    assert rc == 0
    
    rc = subprocess.call(
        f"identify {tmpdir}/testmip1.dds", 
        shell=True
    )
    assert rc == 0

    #assert True == False

def _test_mip_4_read(mount, tmpdir):
    global ao
    testfile = os.path.join(mount, "24832_12416_BI16.dds")
    with open(testfile, "rb") as h:
        time.sleep(0.5)
        log.info("-"*32)
        log.info("First read the header:")
        header = h.read(128)



        time.sleep(0.5)
        log.info("-"*32)
        log.info("Now seek to mipmap4")
        h.seek(22282368)
        time.sleep(1)
        log.info("-"*32)
        log.info("Tell:")
        pos = h.tell()
        log.debug(f"TEST TELL(): {pos}")
        time.sleep(1)
        log.info("-"*32)
        log.info("Read mipmap 4")
        data1 = h.read(65536)
        print(data1[0:20])
        time.sleep(0.5)
        log.info("-"*32)
        log.info("Close")
        time.sleep(0.5)

    log.info(f"Tiles: {len(ao.tc.tiles)}")
    for k,v in ao.tc.tiles.items():
        log.info(f"{k} {v}")
        log.info(f"Chunks: {len(v.chunks)}")
        log.info(v.dds.mipmap_list)


#     with open(testfile, "rb") as h:
#         data = h.read(101000)
#         print(data[100000:20])
#         print(data[129:149])
# 
#     assert len(testdata) == len(data)
#     assert testdata[100000:100020] == data[100000:100020]
#     assert testdata[0:128] == data[0:128]
#     assert testdata[128:150] == data[128:150]
# 
#     assert hashlib.md5(testdata).hexdigest() == hashlib.md5(data).hexdigest()
    #assert True == False
    



def test_middle_read(mount, tmpdir):
    testfile = os.path.join(mount, "24832_12416_BI16.dds")
    # rc = subprocess.call(
    #     f"identify -verbose {testfile}", 
    #     shell=True
    # )
    # assert rc == 0
    
    #with open(testfile, "rb") as h:
    #    header = h.read(128)
    #    data = h.read(1000)

    with open(testfile, "rb") as h:
        header = h.read(128)
        h.seek(100000)
        log.debug(f"TEST TELL(): {h.tell()}")
        data1 = h.read(1000)
        print(data1[0:20])
        log.debug("TEST MIDDLE: SEEK(128)")
        h.seek(128)
        log.debug(f"TEST TELL(): {h.tell()}")
        data0 = h.read(99872)
        print(data0[0:20])

    testdata = header + data0 + data1

    with open(testfile, "rb") as h:
        data = h.read(101000)
        print(data[100000:20])
        print(data[129:149])

    assert len(testdata) == len(data)
    assert testdata[100000:100020] == data[100000:100020]
    assert testdata[0:128] == data[0:128]
    assert testdata[128:150] == data[128:150]

    assert hashlib.md5(testdata).hexdigest() == hashlib.md5(data).hexdigest()
    #assert True == False

def test_multi_read(mount, tmpdir):
    testfile = f"{mount}/24832_12416_BI16.dds"
    header1 = "aaa"
    header2 = "zzz"
    with open(testfile, "rb") as h:
        header1 = h.read(128)
        print(header1)

        with open(testfile, "rb") as h2:
            header2 = h2.read(128)
            print(header2)


    assert header1 == header2
    #assert True == False

def test_read_dds_relative(mount):
    header = ''
    with pushd(os.path.join(mount, 'terrain')):
        log.info(f"MOUNT: {mount}")
        testfile = f"../textures/24832_12416_BI16.dds"

        with open(testfile, "rb") as h:
            header = h.read(128)
        log.info("MOUNT: DONE!")

    assert header[:3] == b'\x44\x44\x53'

def test_read_dds_abs(mount):
    header = ''
   
    print("STARTING!")
    with pushd(mount):
        log.info(f"CWD: {os.getcwd()}")
    log.info(f"CWD: {os.getcwd()}")

    #with pushd(os.path.join(mount, 'terrain')):
    log.info(f"MOUNT: {mount}")
    testfile = f"{mount}/textures/24832_12416_BI16.dds"
    print("Mount: {mount}")

    with open(testfile, "rb") as h:
        print(f"Opened: {testfile}.  About to read...")
        header = h.read(128)
        print(f"Read header. {len(header)} bytes")
    log.info("MOUNT: DONE!")
    print("Mount done.")

    assert header[:3] == b'\x44\x44\x53'


    with pushd(os.path.join(mount, 'terrain')):
        log.info(f"MOUNT: {mount}")
        testfile = f"{mount}/textures/24832_12432_BI16.dds"

        with open(testfile, "rb") as h:
            header = h.read(128)
        log.info("MOUNT: DONE!")

        assert header[:3] == b'\x44\x44\x53'
        log.info(f"CWD: {os.getcwd()}")


    log.info(f"CWD: {os.getcwd()}")

@pytest.mark.parametrize("prefer_winfsp", [True, False])
def test_mount_restore(tmpdir, scenery_dir, prefer_winfsp):
    mountdir = str(os.path.abspath(os.path.join(tmpdir, 'mount')))
    cachedir = str(os.path.join(tmpdir, 'cache'))
    rootdir = scenery_dir


    t = threading.Thread(
        daemon = True,
        target = autoortho.run,
        args = (rootdir, mountdir)
    )

    t.start()
    time.sleep(1)

    assert os.path.isdir(os.path.join(mountdir, "textures"))

    log.debug(f"Unmount {mountdir}")
    autoortho.unmount(mountdir)
    t.join(1)

    assert os.path.lexists(os.path.join(mountdir, ".AO_PLACEHOLDER"))
