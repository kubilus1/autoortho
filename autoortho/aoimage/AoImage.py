#!/usr/bin/env python

import os
import sys
from ctypes import *
import platform
import threading


import logging
log = logging.getLogger(__name__)

class AoImage(Structure):
    _fields_ = [
        ('_data', c_char_p),
        ('_width', c_uint32),
        ('_height', c_uint32),
        ('_stride', c_uint32),   # up to here it's identical to rgba_surface for ISPC
        ('_channels', c_uint32)
    ]

    def __init__(self):
        self._data = None
        self._width = 0
        self._height = 0
        self._stride = 0
        self._channels = 0
        self._title = "No Title"

    def __del__(self):
        _aoi.aoimage_delete(self)

    def __repr__(self):
        return f"ptr:  width: {self._width} height: {self._height} stride: {self._stride} channels: {self._channels}"


    def close(self):
        _aoi.aoimage_delete(self)
        
    def convert(self, mode):
        assert mode == "RGBA", "Sorry, only conversion to RGBA supported"
        new = AoImage()
        _aoi.aoimage_2_rgba(self, new)
        return new

    def reduce_2(self, steps = 1):
        assert steps >= 1, "useless reduce_2" # otherwise we must do a useless copy

        half = self
        while steps >= 1:
            orig = half
            half = AoImage()
            _aoi.aoimage_reduce_2(orig, half)
            steps -= 1

        return half

    def write_jpg(self, filename, quality = 90):
        result = _aoi.aoimage_write_jpg(filename.encode(), self, quality)

    def tobytes(self):
        buf = create_string_buffer(self._width * self._height * self._channels)
        _aoi.aoimage_tobytes(self, buf)
        return buf.raw

    def data_ptr(self):
        return self._data


    def paste(self, p_img, pos):
        _aoi.aoimage_paste(self, p_img, pos[0], pos[1])
        return None

    @property
    def size(self):
        return self._width, self._height

## factories
def new(mode, wh, color):
    #print(f"{mode}, {wh}, {color}")
    assert(mode == "RGBA")
    new = AoImage()
    result = _aoi.aoimage_create(new, wh[0], wh[1], color[0], color[1], color[2])
    if result:
        return new
    return None

def load_from_memory(mem):
    new = AoImage()
    if not _aoi.aoimage_from_memory(new, mem, len(mem)):
        return None
    return new

def open(filename):
    new = AoImage()
    result = _aoi.aoimage_read_jpg(filename.encode(), new)
    if not result:
        return None
    return new

# init code
if platform.system().lower() == 'linux':
    print("Linux detected")
    _aoi_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'aoimage.so')
elif platform.system().lower() == 'windows':
    print("Windows detected")
    _aoi_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'aoimage.dll')
else:
    print("System is not supported")
    exit()

_aoi = CDLL(_aoi_path)
_aoi.aoimage_read_jpg.argtypes = (c_char_p, POINTER(AoImage))
_aoi.aoimage_read_jpg.argtypes = (c_char_p, POINTER(AoImage))
_aoi.aoimage_write_jpg.argtypes = (c_char_p, POINTER(AoImage), c_int32)
_aoi.aoimage_2_rgba.argtypes = (POINTER(AoImage), POINTER(AoImage))
_aoi.aoimage_reduce_2.argtypes = (POINTER(AoImage), POINTER(AoImage))
_aoi.aoimage_delete.argtypes = (POINTER(AoImage),)
_aoi.aoimage_create.argtypes = (POINTER(AoImage), c_uint32, c_uint32, c_uint32, c_uint32, c_uint32)
_aoi.aoimage_tobytes.argtypes = (POINTER(AoImage), c_char_p)
_aoi.aoimage_from_memory.argtypes = (POINTER(AoImage), c_char_p, c_uint32)
_aoi.aoimage_paste.argtypes = (POINTER(AoImage), POINTER(AoImage), c_uint32, c_uint32)

def main():
    #inimg = sys.argv[1]
    #outimg = sys.argv[2]
    #img = Image.open(inimg)
    width = 16
    height = 16
    black = new('RGBA', (256*width,256*height), (0,0,0))
    print(f"{black}")

    black.write_jpg("black.jpg")
    w, h = black.size
    black = None
    print(f"black done, {w} {h}")

    green = new('RGBA', (256*width,256*height), (0,230,0))
    print(f"green {green}")
    green.write_jpg("green.jpg")

    img = open("../testfiles/test_tile.jpg")
    print(f"AoImage.open {img}")

    img2 = img.reduce_2()
    print(f"img2: {img2}")

    img2.write_jpg("test_tile_2.jpg")

    green.paste(img2, (1024, 1024))
    green.write_jpg("test_tile_p.jpg")

    img4 = img.reduce_2(2)
    print(f"img4 {img4}")


    img.paste(img4, (0, 2048))
    img.write_jpg("test_tile_p2.jpg")

if __name__ == "__main__":
    main()
