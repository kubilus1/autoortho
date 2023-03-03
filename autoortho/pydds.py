#!/usr/bin/env python

import os
import sys
from io import BytesIO
from binascii import hexlify
from ctypes import *
from PIL import Image
import platform
import threading

#from memory_profiler import profile
from aoconfig import CFG

import logging
log = logging.getLogger(__name__)

#_stb = CDLL("/usr/lib/x86_64-linux-gnu/libstb.so")
if platform.system().lower() == 'linux':
    print("Linux detected")
    _stb_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib','linux','lib_stb_dxt.so')
    _ispc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib','linux','libispc_texcomp.so')
elif platform.system().lower() == 'windows':
    print("Windows detected")
    _stb_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib','windows','stb_dxt.dll')
    _ispc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'lib','windows','ispc_texcomp.dll')
else:
    print("System is not supported")
    exit()

_stb = CDLL(_stb_path)
_ispc = CDLL(_ispc_path)

DDSD_CAPS = 0x00000001          # dwCaps/dwCaps2 is enabled. 
DDSD_HEIGHT = 0x00000002                # dwHeight is enabled. 
DDSD_WIDTH = 0x00000004                 # dwWidth is enabled. Required for all textures. 
DDSD_PITCH = 0x00000008                 # dwPitchOrLinearSize represents pitch. 
DDSD_PIXELFORMAT = 0x00001000   # dwPfSize/dwPfFlags/dwRGB/dwFourCC and such are enabled. 
DDSD_MIPMAPCOUNT = 0x00020000   # dwMipMapCount is enabled. Required for storing mipmaps. 
DDSD_LINEARSIZE = 0x00080000    # dwPitchOrLinearSize represents LinearSize. 
DDSD_DEPTH = 0x00800000                 # dwDepth is enabled. Used for 3D (Volume) Texture. 


STB_DXT_NORMAL = 0
STB_DXT_DITHER = 1
STB_DXT_HIGHQUAL = 2


# def do_compress(img):
# 
#     width, height = img.size
# 
#     if (width < 4 or width % 4 != 0 or height < 4 or height % 4 != 0):
#         log.debug("Compressed images must have dimensions that are multiples of 4.")
#         return None
# 
#     if img.mode == "RGB":
#         img = img.convert("RGBA")
#     
#     data = img.tobytes()
# 
#     is_rgba = True
#     blocksize = 16
# 
#     dxt_size = ((width+3) >> 2) * ((height+3) >> 2) * 16
#     outdata = create_string_buffer(dxt_size)
# 
#     _stb.compress_pixels.argtypes = (
#             c_char_p,
#             c_char_p, 
#             c_uint64, 
#             c_uint64, 
#             c_bool)
# 
#     result = _stb.compress_pixels(
#             outdata,
#             c_char_p(data),
#             c_uint64(width), 
#             c_uint64(height), 
#             c_bool(is_rgba))
# 
#     if not result:
#         log.debug("Failed to compress")
# 
#     return (dxt_size, outdata)
#
#def get_size(width, height):
#    return ((width+3) >> 2) * ((height+3) >> 2) * 16


class MipMap(object):
    def __init__(self):
        self.idx = 0
        self.startpos = 0
        self.endpos = 0
        self.length = 0
        self.retrieved = False
        self.databuffer = None
        #self.databuffer = BytesIO()

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


    def __init__(self, width, height, ispc=True):
        self.magic = b"DDS "  
        self.size = 124
        self.flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE
        self.width = width
        self.height = height
        

        #self.reserved1 = b"pydds"
        self.pfSize = 32
        self.pfFlags = 0x4
        self.fourCC = b'DXT5'
        self.blocksize = 16 # DXT5
        self.caps = 0x1000 | 0x400000
        self.mipMapCount = 0
       
        #self.mipmaps = []

        self.header = BytesIO()
                
        self.ispc = ispc        
        self.mipmap_map = {}

        #[pow(2,x)*pow(2,x) for x in range(int(math.log(width,2)),1,-1) ]

        # List of tuples [(byte_position, retrieved_bool)]
        self.mipmap_list = []

        # https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
        # pitchOrLinearSize is the total number of bytes in the top level texture for a compressed texture
        #self.pitchOrLinearSize = ((width+3) >> 2) * ((height+3) >> 2) * self.blocksize 
        self.pitchOrLinearSize = max(1, (width*height >> 4)) * self.blocksize

        self.position = 0

        curbytes = 128
        while True:
            mipmap = MipMap()
            mipmap.idx = self.mipMapCount
            mipmap.startpos = curbytes
            curbytes += max(1, (width*height >> 4)) * self.blocksize
            mipmap.length = curbytes - mipmap.startpos
            mipmap.endpos = mipmap.startpos + mipmap.length 
            self.mipMapCount += 1
            self.mipmap_list.append(mipmap)
 
            if (width == 1) and (height == 1):
                break
 
            if (width > 1):
                width = width >> 1
            if (height > 1):
                height = height >> 1

        # Size of all mipmaps: sum([pow(2,x)*pow(2,x) for x in range(12,1,-1) ])
        self.total_size = curbytes 
        self.dump_header()

        for m in self.mipmap_list:
            log.debug(m)
        #log.debug(self.mipmap_list)
        log.debug(self.pitchOrLinearSize)
        #print(self.pitchOrLinearSize)
        log.debug(self.mipMapCount)

        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.ready.clear()
   
        self.compress_count = 0

    def write(self, filename):
        #self.dump_header()
        with open(filename, 'wb') as h:
            h.write(self)
            log.debug(f"Wrote {h.tell()} bytes")
            for mipmap in self.mipmap_list:
                #if mipmap.retrieved:
                log.debug(f"Writing {mipmap.startpos}")
                h.seek(mipmap.startpos)
                if mipmap.databuffer is not None:
                    h.write(mipmap.databuffer.getbuffer())
                log.debug(f"Wrote {h.tell()-mipmap.startpos} bytes")

            # Make sure we complete the full file size
            mipmap = self.mipmap_list[-1]
            if not mipmap.retrieved:
                #h.seek(self.pitchOrLinearSize+126)
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
           
            #if mipmap.databuffer is None:
            #    continue

            if mipmap.endpos > self.position >= mipmap.startpos:
                #
                # Requested read starts before end of this mipmap and before or equal to the starting position
                #
                log.debug(f"PYDDS: We are reading from mipmap {mipmap.idx}")
                
                log.debug(f"PYDDS: {mipmap} , Pos: {self.position} , Len: {length}")
                # Get position in mipmap
                mipmap_pos = self.position - mipmap.startpos
                #remaining_mipmap_len = mipmap.length - mipmap_pos
                remaining_mipmap_len = mipmap.endpos - self.position

                log.debug(f"Len: {length}, remain: {remaining_mipmap_len}, mipmap_pos {mipmap_pos}")
                if length <= remaining_mipmap_len: 
                    #
                    # Mipmap has more than enough remaining length for request
                    # ~We have remaining length in current mipmap~
                    #
                    #if mipmap.databuffer is None:
                    #    log.debug(f"PYDDS: No buffer for {mipmap.idx}!")
                    #    #data = b''
                    #    data = b'\x88' * length
                    #    log.debug(f"PYDDS: adding to outdata {remaining_mipmap_len} bytes for {mipmap.idx}.")
                    #else:
                    log.debug("We have a mipmap and adequated remaining length")
                    mipmap.databuffer.seek(mipmap_pos)
                    data = mipmap.databuffer.read(length)
                    ret_len = length - len(data)
                    if ret_len != 0:
                        # This should be impossible
                        log.error(f"PYDDS  Didn't retrieve full length.  Fill empty bytes {ret_len} for {mipmap.idx}")
                        data += b'\xFF' * ret_len
                                
                    outdata += data
                    self.position += length
                    break

                elif length > remaining_mipmap_len:
                    #
                    # Requested length is greater than what's available in this mipmap
                    #
                    log.debug(f"PYDDS: In mipmap {mipmap.idx} not enough length")

                    #if not mipmap.retrieved:
                    if mipmap.databuffer is None:
                        # 
                        # Mipmap not fully retrieved.  Mimpamp buffer may exist for partially retreived mipmap 0, but
                        # we *must* make sure the full size is available.
                        # 
                        #log.warning(f"PYDDS: No buffer for {mipmap.idx}, Attempt to fill {remaining_mipmap_len} bytes")
                        log.debug(f"PYDDS: No buffer for {mipmap.idx}!")
                        #data = b''
                        data = b'\x88' * remaining_mipmap_len
                        log.debug(f"PYDDS: adding to outdata {remaining_mipmap_len} bytes for {mipmap.idx}.")
                    else:    
                        # Mipmap is retrieved
                        mipmap.databuffer.seek(mipmap_pos)
                        data = mipmap.databuffer.read(remaining_mipmap_len)
                    
                    # Make sure we retrieved all the expected data from the mipmap we can.
                    ret_len = remaining_mipmap_len - len(data)
                    if ret_len != 0:
                        log.error(f"PYDDS: ERROR! Didn't retrieve full length of mipmap for {mipmap.idx}!")
                        #log.error(f"PYDDS: Didn't retrieve full length.  Fill empty bytes {ret_len}")
                        # Pretty sure this causes visual corruption
                        #data += b'\x88' * ret_len

                    outdata += data

                    length -= remaining_mipmap_len
                    #self.position += remaining_mipmap_len
                    self.position = mipmap.endpos


        log.debug(f"PYDDS: END READ: At {self.position} returning {len(outdata)} bytes")
        return outdata


    def dump_header(self):
        self.header.seek(0)
        self.header.write(self)

    #@profile 
    def compress(self, width, height, data):
        # Compress width * height of data

        if (width < 4 or width % 4 != 0 or height < 4 or height % 4 != 0):
            log.debug(f"Compressed images must have dimensions that are multiples of 4. We got {width}x{height}")
            return None

        is_rgba = True
        
        dxt_size = ((width+3) >> 2) * ((height+3) >> 2) * self.blocksize
        outdata = create_string_buffer(dxt_size)
        
        #outdata = b'\x00'*dxt_size
        
        #bio.write(b'\x00'*dxt_size)
        #outdata = bio.getbuffer().tobytes()


        if self.ispc:
            s = rgba_surface()
            s.data = c_char_p(data)
            s.width = c_uint32(width)
            s.height = c_uint32(height)
            s.stride = c_uint32(width * 4)
            
            #print("Will do ispc")
            _ispc.CompressBlocksBC3.argtypes = (
                POINTER(rgba_surface),
                c_char_p
            )

            _ispc.CompressBlocksBC3(
                s, outdata
            )
            result = True
        else:
            #print("Will use stb")
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

    #@profile
    def gen_mipmaps(self, img, startmipmap=0, maxmipmaps=0, compress_height=0):
        # img : PIL/Pillow image
        # startmipmap : Mipmap to start compressing
        # maxmipmaps : Maximum mipmap to compress.  0 = all mipmaps
        # compress_height : Optionally limit compression to number of bytes

        #if maxmipmaps <= len(self.mipmap_list):
        #    maxmipmaps = len(self.mipmap_list)

        #if not maxmipmaps:
        #    maxmipmaps = 0

        with self.lock:

            # Size of all mipmaps: sum([pow(2,x)*pow(2,x) for x in range(12,1,-1) ])

            width, height = img.size
            img_width, img_height = img.size
            mipmap = startmipmap

            log.debug(self.mipmap_list)

            while True:
                ratio = pow(2,mipmap)
                desired_width = self.width / ratio
                desired_height = self.height / ratio
                desired_compress_height = compress_height / ratio

                if maxmipmaps and mipmap >= maxmipmaps:
                    break
                
                if mipmap >= len(self.mipmap_list):
                    break

                #if True:
                if not self.mipmap_list[mipmap].retrieved:

                    if mipmap >= 7:
                        # Avoid compressing tiny mipmaps that will likely never be used.
                        #self.mipmap_list[mipmap].databuffer = BytesIO(initial_bytes=dxtdata)
                        self.mipmap_list[mipmap].databuffer = BytesIO(initial_bytes=b'\x00' * self.mipmap_list[mipmap].length)
                        self.mipmap_list[mipmap].retrieved = True
                        continue

                    # Only squares for now
                    reduction_ratio = int(img_width // desired_width)
                    if reduction_ratio < 1:
                        #log.debug("0 ratio. skip")
                        mipmap += 1
                        if maxmipmaps and mipmap >= maxmipmaps:
                            break
                        continue

                    timg = img.reduce(reduction_ratio)

                    imgdata = timg.tobytes()
                    width, height = timg.size
                    log.debug(f"MIPMAP: {mipmap} SIZE: {timg.size}")

                    # that's a crude hack as X Plane >= 12.04 insists of having 13 mipmaps
                    # and the compressors only support >= 4x4
                    # so we copy the first texel of MM10.
                    if width < 4 or height < 4 and self.mipmap_list[10].retrieved:
                        mm10_db = self.mipmap_list[10].databuffer.getbuffer()
                        self.mipmap_list[mipmap].databuffer = BytesIO(initial_bytes=mm10_db[0:self.blocksize])
                        self.mipmap_list[mipmap].retrieved = True
                    else:
                        if desired_compress_height:
                            height = int((desired_compress_height * 16) // (width * self.blocksize))
                            height = max(4, ((height + 3) // 4) * 4) 
                            #print(f"compressing partial height: {height}")

                        try:
                            dxtdata = self.compress(width, height, imgdata)
                        finally:
                            pass
                            timg.close()
                            del(imgdata)
                            imgdata = None
                            timg = None

                        if dxtdata is not None:
                        #    self.mipmap_list[mipmap].databuffer.seek(0)
                        #    self.mipmap_list[mipmap].databuffer.write(dxtdata)
                        #    print(f"DXTLEN: {len(dxtdata)}")
                            self.mipmap_list[mipmap].databuffer = BytesIO(initial_bytes=dxtdata)
                        #    self.mipmap_list[mipmap].databuffer.write(dxtdata)
                        
                            if not compress_height:
                                # If we partially compressed, this is not
                                # fully retrieved
                                self.mipmap_list[mipmap].retrieved = True
                        #    print(f"BUFSIZE: {sys.getsizeof(dxtdata)}")
                        dxtdata = None

                        #print(f"REF: {sys.getrefcount(dxtdata)}")

                mipmap += 1


            self.dump_header()



def to_dds(img, outpath):
    if img.mode == "RGB":
        img = img.convert("RGBA")
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
