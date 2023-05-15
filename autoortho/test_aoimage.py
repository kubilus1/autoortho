#!/usr/bin/env python3

import os
import ctypes
import platform

import pytest
#from PIL import Image
from aoimage import AoImage

TESTPNG=os.path.join('testfiles', 'test_tile.png')
TESTJPG=os.path.join('testfiles', 'test_tile2.jpg')
TESTSMALLJPG=os.path.join('testfiles', 'test_tile_small.jpg')

def test_aoimage_create(tmpdir):
    img = AoImage.new('RGBA', (4096,4096), (0,0,0))

    data = ctypes.cast(img._data, ctypes.POINTER(ctypes.c_uint8))
    print(type(img._data))
    print(type(data))
    assert data[:16] == [0]*16

    img = AoImage.new('RGBA', (4096,4096), (255,0,0))
    data = ctypes.cast(img._data, ctypes.POINTER(ctypes.c_uint8))
    assert data[:16] == [255,0,0,255]*4
    
    img = AoImage.new('RGBA', (4096,4096), (0,255,0))
    data = ctypes.cast(img._data, ctypes.POINTER(ctypes.c_uint8))
    assert data[:16] == [0,255,0,255]*4


def test_aoimage_open(tmpdir):
    img = AoImage.open(TESTJPG)
    data = ctypes.cast(img._data, ctypes.POINTER(ctypes.c_uint8))
    assert data[:8] != [0]*8


def test_aoimage_reduce(tmpdir):
    img = AoImage.open(TESTJPG)
    small = img.reduce_2(1)

    assert small._width == 2048
    assert small._height == 2048

    small.write_jpg(os.path.join(tmpdir, 'test.jpg'))

def test_aoimage_double(tmpdir):
    img = AoImage.open(TESTSMALLJPG)
    big = img.scale(2)

    assert big._width == 512
    assert big._height == 512

    big.write_jpg(os.path.join(tmpdir, 'test.jpg'))

def test_aoimage_scale4(tmpdir):
    img = AoImage.open(TESTSMALLJPG)
    big = img.scale(4)

    assert big._width == 1024
    assert big._height == 1024

    big.write_jpg(os.path.join(tmpdir, 'test.jpg'))
