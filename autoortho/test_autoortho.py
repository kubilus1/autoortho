#!/usr/bin/env python3

import os
import time
import pytest
import shutil
import autoortho
from pathlib import Path
import threading
import subprocess
from fuse import fuse_exit

def runmount(mountdir, cachedir):
    ao = autoortho.AutoOrtho('./testfiles', cachedir)
    #if os.path.isdir(ao.cache_dir):
    #    print("Removing cache dir")
    #    shutil.rmtree(ao.cache_dir)
    #shutil.rmtree(ao.cache_dir)
    #ao.cache_dir = os.path.join(mountdir, "cache")
    autoortho.FUSE(ao, mountdir, nothreads=True, foreground=True, allow_other=True)
    print("Exiting FUSE mount")
    print("Shutting down mount fixture")
    #if os.path.isdir(ao.cache_dir):
    #    print("Removing cache dir")
    #    shutil.rmtree(ao.cache_dir)

@pytest.fixture
def mount(tmpdir):
    mountdir = str(os.path.join(tmpdir, 'mount'))
    os.makedirs(mountdir)
    cachedir = os.path.join(tmpdir, 'cache')
    #time.sleep(2)
    t = threading.Thread(daemon=True, target=runmount, args=(mountdir, cachedir))
    t.start()
    time.sleep(1)
    
    yield mountdir

    #fuse_exit()
    #ao.destroy('/')
    
    files = os.listdir(mountdir)
    print(files)
    #shutil.rmtree(f"{mountdir}/.pytest_cache")
    #time.sleep(1)
    subprocess.check_call(f"umount {mountdir}", shell=True)
    time.sleep(1)


def test_stuff():
    assert 1 == 1

def _test_autoortho(mount):
    things = os.listdir(mount)
    print(things)
    
    rc = subprocess.call(
        f"identify {mount}/3232_2176_Null13.dds",
        shell=True
    )

    assert rc == 0


def _test_read_header(mount):
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

def _test_read_mip0(mount):
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

    assert True == False

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
