#!/usr/bin/env python3

import os
from PIL import Image
#import conv
import pydds
import subprocess
#from wand import image as wand_image


TESTIMG = os.path.join("testfiles", "test_tile2.jpg")
TESTIMG_small = os.path.join("testfiles", "test_tile_small.jpg")
testimg = Image.open(TESTIMG)
smallimg = Image.open(TESTIMG_small)
#wand_img = wand_image.Image(filename=TESTIMG)


import timeit

#def test_conv(inimg, outfile):
#    conv.conv(inimg, outfile) 

def test_pydds(inimg, outfile):
    pydds.to_dds(inimg, outfile)


def test_pydds_nowrite(img, outfile):
    if img.mode == "RGB":
        img = img.convert("RGBA")
    width, height = img.size
    dds = pydds.DDS(width, height)
    dds.gen_mipmaps(img)
    #dds.dump_header()

def test_pydds_mm(inimg, outfile, mm):
    dds = pydds.DDS(4096, 4096)
    inimg = inimg.convert("RGBA")
    dds.gen_mipmaps(inimg, mm)


def test_pydds_mm3(inimg, outfile):
    dds = pydds.DDS(4096, 4096)
    inimg = inimg.convert("RGBA")
    #dds.gen_mipmaps(inimg, 1)
    #dxtdata = dds.compress(256, 256, inimg.tobytes())
    #dds.mipmaps.append(dxtdata)
    #dds.mipMapCount = 1
    
    # Size of all mipmaps: sum([pow(2,x)*pow(2,x) for x in range(12,1,-1) ])
    #dds.pitchOrLinearSize = 22369616
    #dds.mipMapCount = 11
    #dds.write(outfile)

    #writtensize = pydds.get_size(4096, 4096)
    #with open(outfile, 'ba') as h:
    #    h.write(b'\x00' * (dds.pitchOrLinearSize - writtensize))

    #dds.pitchOrLinearSize = 22369616
    #dds.buffer.seek(128)
    #dds.buffer.write(b'\x00' * dds.pitchOrLinearSize)
    dds.gen_mipmaps(inimg, 3)
    #dds.mipMapCount = 11
    #dds.pitchOrLinearSize = 22369616
    #dds.write(outfile)

def test_nvcompress(inimg, outfile):
    testimg.save('/tmp/temp.jpg', "JPEG")
    subprocess.check_call(
        "nvcompress -bc3 -fast /tmp/temp.jpg %s" % outfile,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )

def test_nvcompress_nomm(inimg, outfile):
    testimg.save('/tmp/temp.jpg', "JPEG")
    subprocess.check_call(
        "nvcompress -bc3 -fast -nomips /tmp/temp.jpg %s" % outfile,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )

def test_pydds_nomm(inimg, outfile):
    dds = pydds.DDS(4096, 4096)
    inimg = inimg.convert("RGBA")
    dds.gen_mipmaps(inimg, 0, 1)


def test_wand(inimg, outfile):
    inimg.compress = 'dxt5'
    inimg.save(filename=outfile)


def main():
    NUMRUNS=15

    #t = timeit.timeit("test_conv(testimg, 'out.dds')", setup='from __main__ import test_conv, testimg', number=NUMRUNS)
    #print(f"SOIL2: {t}")
    t = timeit.timeit("test_pydds(testimg, 'out.dds')", setup='from __main__ import test_pydds, testimg', number=NUMRUNS)
    print(f"PYDDS WRITEOUT: total {t}  per {t/NUMRUNS}")
    t = timeit.timeit("test_pydds_nowrite(testimg, 'out.dds')", setup='from __main__ import test_pydds_nowrite, testimg', number=NUMRUNS)
    print(f"PYDDS MM0: total {t}  per {t/NUMRUNS}")
    t = timeit.timeit("test_pydds_mm(testimg, 'out.dds', 1)", setup='from __main__ import test_pydds_mm, testimg', number=NUMRUNS)
    print(f"PYDDS MM1: total {t}  per {t/NUMRUNS}")
    t = timeit.timeit("test_pydds_mm(testimg, 'out.dds', 3)", setup='from __main__ import test_pydds_mm, testimg', number=NUMRUNS)
    print(f"PYDDS MM3: total {t}  per {t/NUMRUNS}")
    t = timeit.timeit("test_nvcompress(testimg, 'out.dds')", setup='from __main__ import test_nvcompress, testimg', number=NUMRUNS)
    print(f"NVCOMPRESS: total {t}  per {t/NUMRUNS}")
    t = timeit.timeit("test_pydds_nomm(testimg, 'out.dds')", setup='from __main__ import test_pydds_nomm, testimg', number=NUMRUNS)
    print(f"PYDDS NOMM: total {t}  per {t/NUMRUNS}")
    t = timeit.timeit("test_nvcompress_nomm(testimg, 'out.dds')", setup='from __main__ import test_nvcompress_nomm, testimg', number=NUMRUNS)
    print(f"NVCOMPRESS NOMM: total {t}  per {t/NUMRUNS}")
    #t = timeit.timeit("test_wand(wand_img, 'out.dds')", setup='from __main__ import test_wand, wand_img', number=NUMRUNS)
    #print(f"WAND: {t}")

if __name__ == "__main__":
    main()
