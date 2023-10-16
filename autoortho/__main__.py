#!/usr/bin/env python3

import os
import sys
import logging
import logging.handlers
from aoconfig import CFG

def setuplogs():
    log_dir = os.path.join(os.path.expanduser("~"), ".autoortho-data", "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    log_level=logging.DEBUG if os.environ.get('AO_DEBUG') or CFG.general.debug else logging.INFO
    log_formatter = logging.Formatter("%(levelname)s [%(threadName)s] %(name)s: %(message)s")
    log_streamHandler = logging.StreamHandler()
    log_streamHandler.setFormatter(log_formatter)

    log_fileHandler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "autoortho.log"),
        maxBytes=10485760,
        backupCount=5
    )
    log_fileHandler.setFormatter(log_formatter)

    logging.basicConfig(
            #filename=os.path.join(log_dir, "autoortho.log"),
            level=log_level,
            handlers=[
                #logging.FileHandler(filename=os.path.join(log_dir, "autoortho.log")),
                log_fileHandler,
                log_streamHandler if sys.stdout is not None else logging.NullHandler()
            ]
    )
    log = logging.getLogger(__name__)
    log.info(f"Setup logs: {log_dir}, log level: {log_level}")

import autoortho

if __name__ == "__main__":
    setuplogs()
    autoortho.main()
