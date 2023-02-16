import sys
from ctypes import *

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

    def read(self, fn):
        fh = open(fn, "rb")
        #len = fh.readinto(self)
        print(len)
 
        print(f"size:\t{self.size}")
        print(f"height:\t{self.height}")
        print(f"width:\t{self.width}")
        print(f"pitchOrLinearSize:\t{self.pitchOrLinearSize}")
        print(f"fourCC:\t{self.fourCC}")
        print(f"mipMapCount:\t{self.mipMapCount}")
        print(f"depth:\t{self.depth}")
        
dds = DDS()
dds.read(sys.argv[1])