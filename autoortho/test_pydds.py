#!/usr/bin/env python3

import os
import ctypes
import platform

import pydds

import pytest
#from PIL import Image
from aoimage import AoImage as Image
#TESTPNG=os.path.join('testfiles', 'test_tile.png')
TESTJPG=os.path.join('testfiles', 'test_tile2.jpg')


def file_disksize(path):
    if platform.system().lower() == 'windows':
        filesizehigh = ctypes.c_ulonglong(0) # not sure about this... something about files >4gb
        ondisk_size = ctypes.windll.kernel32.GetCompressedFileSizeW(ctypes.c_wchar_p(path),ctypes.pointer(filesizehigh))
    else:
        ondisk_size = os.stat(path).st_blocks*512

    return ondisk_size

def test_mm0(tmpdir):
    timg = Image.open(TESTJPG)
    dds = pydds.DDS(4096, 4096)
    dds.gen_mipmaps(timg, 0, 0)

    assert dds.mipmap_list[0].retrieved == True
    assert dds.mipmap_list[1].retrieved == False

    dds.write(os.path.join(tmpdir, "out.dds"))


def test_dds_conv(tmpdir):
    timg = Image.open(TESTJPG)
    outpath = os.path.join(tmpdir, 'test_tile.dds')
    pydds.to_dds(timg, outpath)
    
    expectedbytes = 11184952 
    actualbytes = os.path.getsize(outpath)

    assert expectedbytes == actualbytes
    
    # We should have blocks to cover the full size of the image
    ondisk_size = file_disksize(outpath)
    assert ondisk_size >= expectedbytes


def test_empty_dds(tmpdir):
    outpath = os.path.join(tmpdir, 'test_empty.dds')
    dds = pydds.DDS(4096, 4096)
    dds.write(outpath)
   
    # suspicious
    expectedbytes = 11184952 
    actualbytes = os.path.getsize(outpath)
    assert expectedbytes == actualbytes

    # Windows doesn't support sparse files well, unfortunately.
    if not platform.system().lower() == 'windows':
        # Sparse file should have allocated space smaller than filesize
        ondisk_size = file_disksize(outpath)
        assert ondisk_size < expectedbytes


def test_mid_dds(tmpdir):
    outpath = os.path.join(tmpdir, 'test_empty.dds')
    timg = Image.open(TESTJPG)
    dds = pydds.DDS(4096, 4096)
    #if timg.mode == "RGB":
    #    timg = timg.convert("RGBA")
    
    dds.gen_mipmaps(timg, 4)
  
    for m in dds.mipmap_list:
        if m.idx >= 4:
            print(m)
            assert m.retrieved == True
            assert m.databuffer is not None
        else:
            assert m.retrieved == False
            assert m.databuffer is None

def test_read_mm0(tmpdir):
    outpath = os.path.join(tmpdir, 'test_mm0.dds')
    timg = Image.open(TESTJPG)
    dds = pydds.DDS(4096, 4096)

    #if timg.mode == "RGB":
    #    timg = timg.convert("RGBA")
    dds.gen_mipmaps(timg)

    data = dds.read(1024)
    assert data


def test_read_mid(tmpdir):
    outpath = os.path.join(tmpdir, 'test_read_mid.dds')
    timg = Image.open(TESTJPG)
    dds = pydds.DDS(4096, 4096)
    #if timg.mode == "RGB":
    #    timg = timg.convert("RGBA")

    dds.gen_mipmaps(timg, 4)

    for m in dds.mipmap_list:
        print(m)

    mm4start = dds.mipmap_list[4].startpos
    dds.seek(mm4start)
    data1 = dds.read(1024)
    assert data1
    assert len(data1) == 1024

    dds.seek(mm4start - 128)
    data2 = dds.read(1024)
    assert data2
    assert len(data2) == 1024

    # Since we started at different points, these should be different
    assert data1[:512] != data2[:512]

    # The ends should be identical
    assert data1[0:384] == data2[128:512]

    # The beginning portion should be empty
    assert data2[:128] == b'\x88'*128

    dds.write(outpath)
    expectedbytes = 11184952 
    actualbytes = os.path.getsize(outpath)
    assert expectedbytes == actualbytes


def test_mm0_dxt1(tmpdir):
    outpath = os.path.join(tmpdir, 'test_mm0.dds')
    timg = Image.open(TESTJPG)
    dds = pydds.DDS(4096, 4096, dxt_format='BC1')

    #if timg.mode == "RGB":
    #    timg = timg.convert("RGBA")
    dds.gen_mipmaps(timg)

    data = dds.read(1024)
    assert data
    
    outpath = os.path.join(tmpdir, 'test.dds')
    dds.write(outpath)

    for m in dds.mipmap_list:
        print(m)

#assert False

def test_gen_mipmap_len(tmpdir):
    outpath = os.path.join(tmpdir, 'test_mm_len.dds')
    timg = Image.open(TESTJPG)
    dds = pydds.DDS(4096, 4096, dxt_format="BC1")
    
    dds.gen_mipmaps(timg, compress_bytes=131072)
    outpath = os.path.join(tmpdir, 'test.dds')
    dds.write(outpath)

    # Check we have retrieved requested data
    dds.seek(131056)
    data = dds.read(16)
    assert data
    assert data != b'\xFF'*16
    assert data != b'\x00'*16

    # For other data verify it has not been processed
    dds.seek(262144)
    data = dds.read(16)
    assert data
    assert data == b'\xFF'*16

    with open(outpath, 'rb') as h:
        h.seek(131072)
        data = h.read(16)
        assert data
        assert data != b'\xFF'*16
        assert data != b'\x00'*16

        h.seek(262144)
        data = h.read(16)
        assert data
        assert data == b'\x00'*16
