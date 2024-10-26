#!/usr/bin/env python

import logging
import math
import os
import platform
import sys
import threading
from ctypes import *
from io import BytesIO

from aoimage import AoImage as Image

log = logging.getLogger(__name__)

if platform.system().lower() == 'linux':
    print("Linux detected")
    _stb_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', 'linux', 'lib_stb_dxt.so')
    _ispc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', 'linux', 'libispc_texcomp.so')
elif platform.system().lower() == 'windows':
    print("Windows detected")
    _stb_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', 'windows', 'stb_dxt.dll')
    _ispc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', 'windows', 'ispc_texcomp.dll')
elif platform.system().lower() == 'darwin':
    # Note, issues with STB so disabled for macos
    # _stb_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib','darwin_arm','libstbdxt.dylib')
    _ispc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', 'darwin_arm', 'libispc_texcomp.dylib')
else:
    print("System is not supported")
    exit()

if hasattr(sys, '_MEIPASS'):
    # Running from PyInstaller bundle, load the .dylib from the bundle directory
    _ispc_path = os.path.join(sys._MEIPASS, "libispc_texcomp.dylib")

if platform.system().lower() == 'darwin':
    _stb = None
else:
    _stb = CDLL(_stb_path)

_ispc = CDLL(_ispc_path)

DDSD_CAPS = 0x00000001  # dwCaps/dwCaps2 is enabled.
DDSD_HEIGHT = 0x00000002  # dwHeight is enabled.
DDSD_WIDTH = 0x00000004  # dwWidth is enabled. Required for all textures.
DDSD_PITCH = 0x00000008  # dwPitchOrLinearSize represents pitch.
DDSD_PIXELFORMAT = 0x00001000  # dwPfSize/dwPfFlags/dwRGB/dwFourCC and such are enabled.
DDSD_MIPMAPCOUNT = 0x00020000  # dwMipMapCount is enabled. Required for storing mipmaps.
DDSD_LINEARSIZE = 0x00080000  # dwPitchOrLinearSize represents LinearSize.
DDSD_DEPTH = 0x00800000  # dwDepth is enabled. Used for 3D (Volume) Texture.

STB_DXT_NORMAL = 0
STB_DXT_DITHER = 1
STB_DXT_HIGHQUAL = 2


class MipMap(object):
    def __init__(self, idx=0, startpos=0, endpos=0, length=0, retrieved=False, databuffer=None):
        self.idx = idx
        self.startpos = startpos
        self.endpos = endpos
        self.length = length
        self.retrieved = retrieved
        self.databuffer = databuffer
        # self.databuffer = BytesIO()

    def __repr__(self):
        return f"MipMap({self.idx}, {self.startpos}, {self.endpos}, {self.length}, {self.retrieved}, {self.databuffer})"


class rgba_surface(Structure):
    _fields_ = [
        ('data', c_char_p),
        ('width', c_uint32),
        ('height', c_uint32),
        ('stride', c_uint32)
    ]


class DDS(Structure):
    _fields_ = [
        ('magic', c_char * 4),
        ('size', c_uint32),
        ('flags', c_uint32),
        ('height', c_uint32),
        ('width', c_uint32),
        ('pitchOrLinearSize', c_uint32),
        ('depth', c_uint32),
        ('mipMapCount', c_uint32),
        ('reserved1', c_char * 44),
        ('pfSize', c_uint32),
        ('pfFlags', c_uint32),
        ('fourCC', c_char * 4),
        ('rgbBitCount', c_uint32),
        ('rBitMask', c_uint32),
        ('gBitMask', c_uint32),
        ('bBitMask', c_uint32),
        ('aBitMask', c_uint32),
        ('caps', c_uint32),
        ('caps2', c_uint32),
        ('reservedCaps', c_uint32 * 2),
        ('reserved2', c_uint32)
    ]

    def __init__(self, width, height, ispc=True, dxt_format="BC1"):
        self.magic = b"DDS "
        self.size = 124
        self.flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE
        self.width = width
        self.height = height

        # self.reserved1 = b"pydds"
        self.pfSize = 32
        self.pfFlags = 0x4

        if dxt_format == 'BC3':
            self.fourCC = b'DXT5'
            self.blocksize = 16
        else:
            self.fourCC = b'DXT1'
            self.blocksize = 8

        self.caps = 0x1000 | 0x400000
        self.mipMapCount = 0

        # self.mipmaps = []

        self.header = BytesIO()

        self.ispc = ispc
        self.dxt_format = dxt_format
        self.mipmap_map = {}

        # [pow(2,x)*pow(2,x) for x in range(int(math.log(width,2)),1,-1) ]

        # List of tuples [(byte_position, retrieved_bool)]
        self.mipmap_list = []

        # https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
        # pitchOrLinearSize is the total number of bytes in the top level texture for a compressed texture
        self.pitchOrLinearSize = max(1, (width * height >> 4)) * self.blocksize
        self.position = 0

        curbytes = 128
        while (width >= 1) and (height >= 1):
            mipmap = MipMap()
            mipmap.idx = self.mipMapCount
            mipmap.startpos = curbytes
            curbytes += max(1, (width * height >> 4)) * self.blocksize
            mipmap.length = curbytes - mipmap.startpos
            mipmap.endpos = mipmap.startpos + mipmap.length
            self.mipmap_list.append(mipmap)
            width = width >> 1
            height = height >> 1
            self.mipMapCount += 1

        # Size of all mipmaps: sum([pow(2,x)*pow(2,x) for x in range(12,1,-1) ])
        # self.pitchOrLinearSize = curbytes
        self.total_size = curbytes
        self.dump_header()

        # The smallest effective MM we can have is a size 4x4 block.  However
        # XPlane expects MM down to theoretical 1x1.  Therefore the smallest
        # real MM is the len of our list - 3
        self.smallest_mm = len(self.mipmap_list) - 3

        for m in self.mipmap_list:
            log.debug(m)

        # log.debug(self.mipmap_list)
        log.debug(self.pitchOrLinearSize)
        # print(self.pitchOrLinearSize)
        log.debug(self.mipMapCount)

        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.ready.clear()

        self.compress_count = 0

    def write(self, filename):
        # self.dump_header()
        with open(filename, 'wb') as h:
            h.write(self)
            log.debug(f"Wrote {h.tell()} bytes")
            for mipmap in self.mipmap_list:
                # if mipmap.retrieved:
                log.debug(f"Writing {mipmap.startpos}")
                h.seek(mipmap.startpos)
                if mipmap.databuffer is not None:
                    h.write(mipmap.databuffer.getbuffer())
                log.debug(f"Wrote {h.tell() - mipmap.startpos} bytes")

            # Make sure we complete the full file size
            mipmap = self.mipmap_list[-1]
            if not mipmap.retrieved:
                h.seek(self.total_size - 2)
                h.write(b'x\00')

    def tell(self):
        return self.position

    def seek(self, offset):
        log.debug(f"SEEK: {offset}")
        self.position = offset

    def read(self, length):
        log.debug(f"PYDDS: READ: {self.position} {length} bytes")

        outdata = b''

        if self.position < 128:
            log.debug("Read the header")
            outdata = self.header.getvalue()
            self.position = 128
            length -= 128

        for mipmap in self.mipmap_list:

            # if mipmap.databuffer is None:
            #    continue

            if mipmap.endpos > self.position >= mipmap.startpos:
                #
                # Requested read starts before end of this mipmap and before or equal to the starting position
                #
                log.debug(f"PYDDS: We are reading from mipmap {mipmap.idx}")

                log.debug(f"PYDDS: {mipmap} , Pos: {self.position} , Len: {length}")
                # Get position in mipmap
                mipmap_pos = self.position - mipmap.startpos
                # remaining_mipmap_len = mipmap.length - mipmap_pos
                remaining_mipmap_len = mipmap.endpos - self.position

                log.debug(f"Len: {length}, remain: {remaining_mipmap_len}, mipmap_pos {mipmap_pos}")
                if length <= remaining_mipmap_len:
                    #
                    # Mipmap has more than enough remaining length for request
                    # ~We have remaining length in current mipmap~
                    #
                    if mipmap.databuffer is None:
                        log.warning(f"PYDDS: No buffer for {mipmap.idx}!")
                        # data = b''
                        data = b'\x88' * length
                        log.warning(f"PYDDS: adding to outdata {remaining_mipmap_len} bytes for {mipmap.idx}.")
                    else:
                        log.debug("We have a mipmap and adequated remaining length")
                        mipmap.databuffer.seek(mipmap_pos)
                        data = mipmap.databuffer.read(length)
                        ret_len = length - len(data)
                        if ret_len != 0:
                            # This should be impossible
                            log.error(
                                f"PYDDS  Didn't retrieve full length.  Fill empty bytes.  This is not good! mmpos: {mipmap_pos} retlen: {ret_len} reqlen: {length} mm:{mipmap.idx}")
                            data += b'\xFF' * ret_len

                    outdata += data
                    self.position += length
                    break

                elif length > remaining_mipmap_len:
                    #
                    # Requested length is greater than what's available in this mipmap
                    #
                    log.debug(f"PYDDS: In mipmap {mipmap.idx} not enough length")

                    # if not mipmap.retrieved:
                    if mipmap.databuffer is None:
                        # 
                        # Mipmap not fully retrieved.  Mimpamp buffer may exist for partially retreived mipmap 0, but
                        # we *must* make sure the full size is available.
                        # 
                        # log.warning(f"PYDDS: No buffer for {mipmap.idx}, Attempt to fill {remaining_mipmap_len} bytes")
                        log.warning(f"PYDDS: No buffer for {mipmap.idx}!")
                        # data = b''
                        data = b'\x88' * remaining_mipmap_len
                        log.warning(f"PYDDS: adding to outdata {remaining_mipmap_len} bytes for {mipmap.idx}.")
                    else:
                        # Mipmap is retrieved
                        mipmap.databuffer.seek(mipmap_pos)
                        data = mipmap.databuffer.read(remaining_mipmap_len)

                    # Make sure we retrieved all the expected data from the mipmap we can.
                    ret_len = remaining_mipmap_len - len(data)
                    if ret_len != 0:
                        log.error(f"PYDDS: ERROR! Didn't retrieve full length of mipmap for {mipmap.idx}!")
                        log.error(f"PYDDS: Didn't retrieve full length.  Fill empty bytes {ret_len}")
                        # Pretty sure this causes visual corruption
                        data += b'\x88' * ret_len

                    outdata += data

                    length -= remaining_mipmap_len
                    # self.position += remaining_mipmap_len
                    self.position = mipmap.endpos

        log.debug(f"PYDDS: END READ: At {self.position} returning {len(outdata)} bytes")
        return outdata

    def dump_header(self):
        self.header.seek(0)
        self.header.write(self)

    # @profile
    def compress(self, width, height, data):
        # Compress width * height of data

        if (width < 4 or width % 4 != 0 or height < 4 or height % 4 != 0):
            log.debug(f"Compressed images must have dimensions that are multiples of 4. We got {width}x{height}")
            return None

        # outdata = b'\x00'*dxt_size

        # bio.write(b'\x00'*dxt_size)
        # outdata = bio.getbuffer().tobytes()

        if self.ispc and self.dxt_format == "BC3":
            dxt_size = ((width + 3) >> 2) * ((height + 3) >> 2) * self.blocksize
            outdata = create_string_buffer(dxt_size)
            # print(f"LEN: {len(outdata)}")
            s = rgba_surface()
            s.data = c_char_p(data)
            s.width = c_uint32(width)
            s.height = c_uint32(height)
            s.stride = c_uint32(width * 4)

            # print("Will do ispc")
            _ispc.CompressBlocksBC3.argtypes = (
                POINTER(rgba_surface),
                c_char_p
            )

            _ispc.CompressBlocksBC3(
                s, outdata
            )
            result = True
        elif self.ispc and self.dxt_format == "BC1":
            # print("BC1")
            blocksize = 8
            dxt_size = ((width + 3) >> 2) * ((height + 3) >> 2) * self.blocksize
            outdata = create_string_buffer(dxt_size)
            # print(f"LEN: {len(outdata)}")

            s = rgba_surface()
            s.data = c_char_p(data)
            s.width = c_uint32(width)
            s.height = c_uint32(height)
            s.stride = c_uint32(width * 4)

            # print("Will do ispc")
            _ispc.CompressBlocksBC1.argtypes = (
                POINTER(rgba_surface),
                c_char_p
            )

            _ispc.CompressBlocksBC1(
                s, outdata
            )
            result = True
        else:
            is_rgba = True
            # print("Will use stb")
            blocksize = 16
            dxt_size = ((width + 3) >> 2) * ((height + 3) >> 2) * blocksize
            outdata = create_string_buffer(dxt_size)

            # print(f"LEN: {len(outdata)}")
            _stb.compress_pixels.argtypes = (
                c_char_p,
                c_char_p,
                c_uint64,
                c_uint64,
                c_bool)

            result = _stb.compress_pixels(
                outdata,
                c_char_p(data),
                c_uint64(width),
                c_uint64(height),
                c_bool(is_rgba))

        if not result:
            log.debug("Failed to compress")

        self.compress_count += 1
        return outdata

    # @profile
    def gen_mipmaps(self, img, startmipmap=0, maxmipmaps=99, compress_bytes=0):
        # img : PIL/Pillow image
        # startmipmap : Mipmap to start compressing
        # maxmipmaps : Maximum mipmap to compress.  99 = all mipmaps
        # compress_bytes : Optionally limit compression to number of bytes

        # if maxmipmaps <= len(self.mipmap_list):
        #    maxmipmaps = len(self.mipmap_list)

        # if not maxmipmaps:
        #    maxmipmaps = 8

        with self.lock:
            # print(f"gen_mipmaps: MIPMAP: {startmipmap} input SIZE: {img.size}")

            # Size of all mipmaps: sum([pow(2,x)*pow(2,x) for x in range(12,1,-1) ])

            # if not maxmipmaps:
            # maxmipmaps = len(self.mipmap_list)

            width, height = img.size
            mipmap = startmipmap
            # I believe XP only references up to MM8, so might be able to trim
            # this down more
            # maxmipmaps == 0 indicates we want all mipmaps so set to len
            # of our mipmap_list
            if maxmipmaps > self.smallest_mm:
                log.debug(f"Setting maxmipmaps to {self.smallest_mm}")
                maxmipmaps = self.smallest_mm

            log.debug(self.mipmap_list)

            # Initial reduction of image size before mipmap processing 
            steps = 0
            if mipmap > 0:
                desired_width = self.width >> mipmap
                while width > desired_width:
                    width >>= 1
                    compress_bytes >>= 2
                    steps += 1

            if steps > 0:
                # img = img.reduce(pow(2, steps))
                img = img.reduce_2(steps)

            while True:
                if True:
                    # if not self.mipmap_list[mipmap].retrieved:
                    imgdata = img.data_ptr()
                    width, height = img.size
                    log.debug(f"MIPMAP: {mipmap} SIZE: {img.size}")

                    if compress_bytes:
                        # Get how many rows we need to process for requested number of bytes
                        height = math.ceil((compress_bytes * 16) / (width * self.blocksize))
                        # Make the rows a factor of 4
                        height = max(4, ((height + 3) // 4) * 4)
                        log.debug(f"Doing partial compress of {compress_bytes} bytes.  Height: {height}")
                        compress_bytes >>= 2

                    try:
                        dxtdata = self.compress(width, height, imgdata)
                    except:
                        log.warning("dds compress failed")

                    if dxtdata is not None:
                        self.mipmap_list[mipmap].databuffer = BytesIO(initial_bytes=dxtdata)
                        if not compress_bytes:
                            self.mipmap_list[mipmap].retrieved = True

                        # we are already at 4x4 so push result forward to
                        # remaining MMs
                        if mipmap == self.smallest_mm:
                            log.debug(f"At MM {mipmap}.  Set the remaining MMs..")
                            for mm in self.mipmap_list[self.smallest_mm:]:
                                mm.databuffer = BytesIO(initial_bytes=dxtdata)
                                mm.retrieved = True
                                mipmap += 1

                    dxtdata = None

                if mipmap >= maxmipmaps:  # (maxmipmaps + 1) or mipmap >= self.smallest_mm:
                    # We've hit or max requested or possible mipmaps
                    break

                mipmap += 1
                # Halve the image
                img = img.reduce_2()

            self.dump_header()


def to_dds(img, outpath):
    # if img.mode == "RGB":
    #    img = img.convert("RGBA")
    width, height = img.size

    dds = DDS(width, height)
    dds.gen_mipmaps(img)
    dds.write(outpath)


def main():
    inimg = sys.argv[1]
    outimg = sys.argv[2]
    img = Image.open(inimg)

    to_dds(img, outimg)


if __name__ == "__main__":
    main()
