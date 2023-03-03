import os
import time
import threading
from aoconfig import CFG
import logging
log = logging.getLogger(__name__)

STATS={}

class AOStats(object):
    def __init__(self):
        log.info("Creating stats object")
        #global STATS
        #STATS=self.
        self.running = False
        self._t = threading.Thread(daemon=True, target=self.show)

    def start(self):
        log.info("Starting stats thread")
        self.running = True
        self._t.start()

    def stop(self):
        log.info("Stopping stats thread")
        self.running = False
        self._t.join()

    def show(self):
        while self.running:
            time.sleep(5)
            #s = {k:v for k,v in self.__dict__.items() if not k.startswith('_')}
            log.info(f"STATS: ID: {STATS}")
