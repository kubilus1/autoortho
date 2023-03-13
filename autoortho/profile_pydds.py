#!/usr/bin/env python3

import os
import cProfile
from PIL import Image

import pydds

def testgen(img):
    for i in range(20):
        width, height = img.size
        dds = pydds.DDS(width, height)
        dds.gen_mipmaps(img)

def main():
    
    #inimg = sys.argv[1]
    #outimg = sys.argv[2]
    
    
    TESTIMG = os.path.join("testfiles", "test_tile2.jpg")
    img = Image.open(TESTIMG)
    #img = img.convert("RGBA")
    #width, height = img.size
    #dds = pydds.DDS(width, height)
    profile = cProfile.Profile()
    #profile.runcall(dds.gen_mipmaps, img, 0, 1)
    profile.runcall(testgen, img)
    profile.print_stats()
    #dds.gen_mipmaps(img)

if __name__ == "__main__":
    #cProfile.run("main()")
    main()
