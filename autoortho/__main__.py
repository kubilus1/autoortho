#!/usr/bin/env python3

import os
import sys
import logging

log_dir = os.path.join(os.path.expanduser("~"), ".autoortho-data", "logs")
if not os.path.isdir(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
        #filename=os.path.join(log_dir, "autoortho.log"),
        level=logging.DEBUG if os.environ.get('AO_DEBUG') else logging.INFO,
        handlers=[
            logging.FileHandler(filename=os.path.join(log_dir, "autoortho.log")),
            logging.StreamHandler()
        ]
)

import autoortho

if __name__ == "__main__":
    autoortho.main()
