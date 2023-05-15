#!/usr/bin/env python3

import os
#from PIL import Image
from aoimage import AoImage as Image

#import conv
import pydds
import subprocess
#from wand import image as wand_image


TESTIMG = os.path.join("testfiles", "test_tile2.jpg")
TESTIMG_small = os.path.join("testfiles", "test_tile_small.jpg")
testimg = Image.open(TESTIMG)
testimg_rgba = testimg.convert('RGBA')
smallimg = Image.open(TESTIMG_small)
smallimg_rgba = smallimg.convert('RGBA')
#wand_img = wand_image.Image(filename=TESTIMG)
#testimg.convert('RGBA')
#smallimg.convert('RGBA')

import timeit

#def test_conv(inimg, outfile):
#    conv.conv(inimg, outfile) 

def test_pydds(inimg, outfile, mmstart, mmend, ispc, fmt='BC3', clen=0):
    #print(f"TESTING {inimg} {outfile} {mmstart} {mmend} {ispc}")
    dds = pydds.DDS(4096, 4096, ispc=ispc, dxt_format=fmt)
    #inimg = inimg.convert('RGBA')
    dds.gen_mipmaps(inimg, mmstart, mmend, clen)

def test_nvcompress(inimg, outfile, mm=True):
    testimg.save('/tmp/temp.jpg', "JPEG")

    if mm:
        CMD = f"nvcompress -bc3 -fast /tmp/temp.jpg {outfile}"
    else:
        CMD = f"nvcompress -bc3 -fast -nomips/tmp/temp.jpg {outfile}"

    subprocess.check_call(
        CMD,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )

def test_scale(inimg, factor):
    inimg.scale(factor)


def test_wand(inimg, outfile):
    inimg.compress = 'dxt5'
    inimg.save(filename=outfile)


def main():
    NUMRUNS=30

    #t = timeit.timeit("test_conv(testimg, 'out.dds')", setup='from __main__ import test_conv, testimg', number=NUMRUNS)
    #print(f"SOIL2: {t}")
    #t = timeit.timeit("test_pydds(testimg, 'out.dds')", setup='from __main__ import test_pydds, testimg', number=NUMRUNS)
    #print(f"PYDDS WRITEOUT: total {t}  per {t/NUMRUNS}")

    
    tests = [
        ("AOIMAGE SCALE 2", "test_scale(smallimg_rgba, 2)"),
        ("AOIMAGE SCALE 4", "test_scale(smallimg_rgba, 4)"),
        ("AOIMAGE SCALE 8", "test_scale(smallimg_rgba, 8)"),
        ("AOIMAGE SCALE 16", "test_scale(smallimg_rgba, 16)"),
        ("PYDDS MM0 PART", "test_pydds(testimg_rgba, 'out.dds', 0, 99, True, clen=1048576)"),
        ("PYDDS MM1 PART", "test_pydds(testimg_rgba, 'out.dds', 1, 99, True, clen=1048576)"),
        ("PYDDS MM3 PART", "test_pydds(testimg_rgba, 'out.dds', 3, 99, True, clen=1048576)"),
        ("PYDDS NOMM PART", "test_pydds(testimg_rgba, 'out.dds', 0, 0, True, clen=1048576)"),
        #("PYDDS MM0 STB", "test_pydds(testimg_rgba, 'out.dds', 0, 0, False)"),
        #("PYDDS MM1 STB", "test_pydds(testimg_rgba, 'out.dds', 1, 0, False)"),
        #("PYDDS MM3 STB", "test_pydds(testimg_rgba, 'out.dds', 3, 0, False)"),
        #("PYDDS NOMM STB", "test_pydds(testimg_rgba, 'out.dds', 0, 1, False)"),
        ("PYDDS MM0 ISPC BC1", "test_pydds(testimg_rgba, 'out.dds', 0, 99, True, fmt='BC1')"),
        ("PYDDS MM1 ISPC BC1", "test_pydds(testimg_rgba, 'out.dds', 1, 99, True, fmt='BC1')"),
        ("PYDDS MM3 ISPC BC1", "test_pydds(testimg_rgba, 'out.dds', 3, 99, True, fmt='BC1')"),
        ("PYDDS NOMM ISPC BC1", "test_pydds(testimg_rgba, 'out.dds', 0, 0, True, fmt='BC1')"),
        ("PYDDS MM0 ISPC BC3", "test_pydds(testimg_rgba, 'out.dds', 0, 99, True)"),
        ("PYDDS MM1 ISPC BC3", "test_pydds(testimg_rgba, 'out.dds', 1, 99, True)"),
        ("PYDDS MM3 ISPC BC3", "test_pydds(testimg_rgba, 'out.dds', 3, 99, True)"),
        ("PYDDS NOMM ISPC BC3", "test_pydds(testimg_rgba, 'out.dds', 0, 0, True)"),
        #("NVCOMPRESS", "test_nvcompress(testimg, 'out.dds', True)"),
        #("NVCOMPRESS NOMM", "test_nvcompress(testimg, 'out.dds', False)")
    ]

    for test in tests:
        #print(f"Testing {test[1]} ... for {test[0]}")
        t = timeit.timeit(test[1], setup='from __main__ import test_scale, test_pydds, testimg, testimg_rgba, smallimg, smallimg_rgba, test_nvcompress', number=NUMRUNS)
        print(f"{test[0]}: total {t}  per {t/NUMRUNS}")


    # Wand is super slow, don't bother
    #t = timeit.timeit("test_wand(wand_img, 'out.dds')", setup='from __main__ import test_wand, wand_img', number=NUMRUNS)
    #print(f"WAND: {t}")

if __name__ == "__main__":
    main()
