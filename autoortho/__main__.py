#!/usr/bin/env python3

import os
import sys
import zipfile

if os.path.splitext(sys.argv[0])[1] == ".pyz":
    print("PYZ extract it")

    with zipfile.ZipFile(sys.argv[0]) as zf:
        zf.extractall('aozip')

    sys.path.append('./aozip')

import autoortho

if __name__ == "__main__":
    autoortho.main()
