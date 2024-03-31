#!/usr/bin/env python

import os
import sys
from ctypes import *
import platform

import logging
log = logging.getLogger(__name__)

class AOImageException(Exception):
    pass

class AoImage(Structure):
    _fields_ = [
        ('_data', c_uint64),    # ctypes pointers are tricky when changed under the hud so we treat it as number
        #('_data', POINTER(c_uint64)),    # ctypes pointers are tricky when changed under the hud so we treat it as number
        ('_width', c_uint32),
        ('_height', c_uint32),
        ('_stride', c_uint32),
        ('_channels', c_uint32),
        ('_errmsg', c_char*80)  #possible error message to be filled by the C routines
    ]

    def __init__(self):
        self._data = 0
        #self._data = cast('\x00', POINTER(c_uint64))
        self._width = 0
        self._height = 0
        self._stride = 0
        self._channels = 0
        self._errmsg = b'';

    def __del__(self):
        _aoi.aoimage_delete(self)

    def __repr__(self):
        return f"ptr:  width: {self._width} height: {self._height} stride: {self._stride} channels: {self._channels}"

    def close(self):
        _aoi.aoimage_delete(self)
        
    def convert(self, mode):
        """
        Not really needed as AoImage always loads as RGBA
        """
        assert mode == "RGBA", "Sorry, only conversion to RGBA supported"
        new = AoImage()
        if not _aoi.aoimage_2_rgba(self, new):
            log.debug(f"AoImage.reduce_2 error: {new._errmsg.decode()}")
            return None

        return new

    def reduce_2(self, steps = 1):
        """
        Reduce image by factor 2.
        """
        assert steps >= 1, "useless reduce_2" # otherwise we must do a useless copy

        half = self
        while steps >= 1:
            orig = half
            half = AoImage()
            if not _aoi.aoimage_reduce_2(orig, half):
                log.debug(f"AoImage.reduce_2 error: {half._errmsg.decode()}")
                raise AOImageException(f"AoImage.reduce_2 error: {half._errmsg.decode()}")
                #return None

            steps -= 1

        return half

    def scale(self, factor=2):
        scaled = AoImage()
        orig = self
        if not _aoi.aoimage_scale(orig, scaled, factor):
            log.debug(f"AoImage.scale error: {new._errmsg.decode()}")
            return None
        
        return scaled

    def write_jpg(self, filename, quality = 90):
        """
        Convenience function to write jpeg.
        """   
        if not _aoi.aoimage_write_jpg(filename.encode(), self, quality):
            log.debug(f"AoImage.new error: {new._errmsg.decode()}")
    
    def tobytes(self):
        """
        Not really needed, high overhead. Use data_ptr instead.
        """      
        buf = create_string_buffer(self._width * self._height * self._channels)
        _aoi.aoimage_tobytes(self, buf)
        return buf.raw

    def data_ptr(self):
        """
        Return ptr to image data. Valid only as long as the object lives.
        """
        return self._data

    def paste(self, p_img, pos):
        _aoi.aoimage_paste(self, p_img, pos[0], pos[1])
        return True

    def copy(self, height_only = 0):
        new = AoImage()
        if not _aoi.aoimage_copy(self, new, height_only):
            log.error(f"AoImage.copy error: {self._errmsg.decode()}")
            return None

        return new

    def crop(self, c_img, pos):
        _aoi.aoimage_crop(self, c_img, pos[0], pos[1])
        return True

    def desaturate(self, saturation = 1.0):
        assert 0.0 <= saturation and saturation <= 1.0
        if saturation == 1.0 or saturation is None:
            return self

        if not _aoi.aoimage_desaturate(self, saturation):
            log.error(f"AoImage.desaturate error: {self._errmsg.decode()}")
            return None
        return self

    @property
    def size(self):
        return self._width, self._height

## factories
def new(mode, wh, color):
    #print(f"{mode}, {wh}, {color}")
    assert(mode == "RGBA")
    new = AoImage()
    if not _aoi.aoimage_create(new, wh[0], wh[1], color[0], color[1], color[2]):
        log.debug(f"AoImage.new error: {new._errmsg.decode()}")
        return None

    return new


def load_from_memory(mem, datalen=None):
    if not datalen:
        datalen = len(mem)
    new = AoImage()
    if not _aoi.aoimage_from_memory(new, mem, datalen):
        log.error(f"AoImage.load_from_memory error: {new._errmsg.decode()}")
        return None

    return new

def open(filename):
    new = AoImage()
    if not _aoi.aoimage_read_jpg(filename.encode(), new):
        log.debug(f"AoImage.open error for {filename}: {new._errmsg.decode()}")
        return None

    return new

# init code
if platform.system().lower() == 'linux':
    _aoi_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'aoimage.so')
elif platform.system().lower() == 'windows':
    _aoi_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'aoimage.dll')
elif platform.system().lower() == 'darwin':
    _aoi_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'aoimage.dylib')
else:
    log.error("System is not supported")
    exit()

_aoi = CDLL(_aoi_path)
_aoi.aoimage_read_jpg.argtypes = (c_char_p, POINTER(AoImage))
_aoi.aoimage_write_jpg.argtypes = (c_char_p, POINTER(AoImage), c_int32)
_aoi.aoimage_2_rgba.argtypes = (POINTER(AoImage), POINTER(AoImage))
_aoi.aoimage_reduce_2.argtypes = (POINTER(AoImage), POINTER(AoImage))
_aoi.aoimage_scale.argtypes = (POINTER(AoImage), POINTER(AoImage), c_uint32)
_aoi.aoimage_delete.argtypes = (POINTER(AoImage),)
_aoi.aoimage_create.argtypes = (POINTER(AoImage), c_uint32, c_uint32, c_uint32, c_uint32, c_uint32)
_aoi.aoimage_tobytes.argtypes = (POINTER(AoImage), c_char_p)
_aoi.aoimage_from_memory.argtypes = (POINTER(AoImage), c_char_p, c_uint32)
_aoi.aoimage_copy.argtypes = (POINTER(AoImage), POINTER(AoImage), c_uint32)
_aoi.aoimage_paste.argtypes = (POINTER(AoImage), POINTER(AoImage), c_uint32, c_uint32)
_aoi.aoimage_crop.argtypes = (POINTER(AoImage), POINTER(AoImage), c_uint32, c_uint32)
_aoi.aoimage_desaturate.argtypes = (POINTER(AoImage), c_float)

def main():
    logging.basicConfig(level = logging.DEBUG)
    width = 16
    height = 16
    black = new('RGBA', (256*width,256*height), (0,0,0))
    log.info(f"{black}")
    log.info(f"black._data: {black._data}")
    log.info(f"black.data_ptr(): {black.data_ptr()}")
    black.write_jpg("black.jpg")
    w, h = black.size
    black = None
    log.info(f"black done, {w} {h}")

    green = new('RGBA', (256*width,256*height), (0,230,0))
    log.info(f"green {green}")
    green.write_jpg("green.jpg")

    log.info("Trying nonexistent jpg")
    img = open("../testfiles/non_exitent.jpg")

    log.info("Trying non jpg")
    img = open("main.c")

    img = open("../testfiles/test_tile2.jpg")
    log.info(f"AoImage.open {img}")

    img.copy().desaturate(0.1).write_jpg("desaturated.jpg")

    img2 = img.reduce_2()
    log.info(f"img2: {img2}")

    img2.write_jpg("test_tile_2.jpg")

    img3 = open("../testfiles/test_tile_small.jpg")
    big = img3.scale(16)
    big.write_jpg('test_tile_big.jpg')

    cropimg = new('RGBA', (256,256), (0,0,0))
    img.crop(cropimg, (256,256))
    cropimg.write_jpg("crop.jpg")

    green.paste(img2, (1024, 1024))
    green.write_jpg("test_tile_p.jpg")

    img4 = img.reduce_2(2)
    log.info(f"img4 {img4}")


    img.paste(img4, (0, 2048))
    img.write_jpg("test_tile_p2.jpg")





if __name__ == "__main__":
    main()
