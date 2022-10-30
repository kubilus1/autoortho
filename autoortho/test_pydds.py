#!/usr/bin/env python3

import os
import ctypes
import platform

import pydds

import pytest
from PIL import Image
TESTPNG=os.path.join('testfiles', 'test_tile.png')


def file_disksize(path):
    if platform.system().lower() == 'windows':
        filesizehigh = ctypes.c_ulonglong(0) # not sure about this... something about files >4gb
        ondisk_size = ctypes.windll.kernel32.GetCompressedFileSizeW(ctypes.c_wchar_p(path),ctypes.pointer(filesizehigh))
    else:
        ondisk_size = os.stat(path).st_blocks*512

    return ondisk_size



def test_dds_conv(tmpdir):
    timg = Image.open(TESTPNG)
    outpath = os.path.join(tmpdir, 'test_tile.dds')
    pydds.to_dds(timg, outpath)
    
    expectedbytes = 22369744
    actualbytes = os.path.getsize(outpath)

    assert expectedbytes == actualbytes
    
    # We should have blocks to cover the full size of the image
    ondisk_size = file_disksize(outpath)
    assert ondisk_size >= expectedbytes


def test_empty_dds(tmpdir):
    outpath = os.path.join(tmpdir, 'test_empty.dds')
    dds = pydds.DDS(4096, 4096)
    dds.write(outpath)
    
    expectedbytes = 22369744
    actualbytes = os.path.getsize(outpath)
    assert expectedbytes == actualbytes

    # Sparse file should have allocated space smaller than filesize
    ondisk_size = file_disksize(outpath)
    assert ondisk_size < expectedbytes


def test_mid_dds(tmpdir):
    outpath = os.path.join(tmpdir, 'test_empty.dds')
    timg = Image.open(TESTPNG)
    dds = pydds.DDS(4096, 4096)
    dds.gen_mipmaps(timg, 4)
    
    for m in dds.mipmap_list:
        if m.idx >= 4:
            assert m.retrieved == True
            assert m.databuffer is not None
        else:
            assert m.retrieved == False
            assert m.databuffer is None

def test_read_mm0(tmpdir):
    outpath = os.path.join(tmpdir, 'test_mm0.dds')
    timg = Image.open(TESTPNG)
    dds = pydds.DDS(4096, 4096)

    dds.gen_mipmaps(timg)

    data = dds.read(1024)
    assert data


def test_read_mid(tmpdir):
    outpath = os.path.join(tmpdir, 'test_read_mid.dds')
    timg = Image.open(TESTPNG)
    dds = pydds.DDS(4096, 4096)

    dds.gen_mipmaps(timg, 4)

    dds.seek(22282368)
    data1 = dds.read(1024)
    assert data1
    assert len(data1) == 1024

    dds.seek(22282240)
    data2 = dds.read(1024)
    assert data2
    assert len(data2) == 1024

    # Since we started at different points, these should be different
    assert data1[:512] != data2[:512]

    # The ends should be identical
    assert data1[0:384] == data2[128:512]

    # The beginning portion should be empty
    assert data2[:128] == b'\x00'*128

    dds.write(outpath)
    expectedbytes = 22369744
    actualbytes = os.path.getsize(outpath)
    assert expectedbytes == actualbytes


#assert False


