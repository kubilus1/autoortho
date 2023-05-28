import os
import time
import threading
import collections

from aoconfig import CFG
import logging
log = logging.getLogger(__name__)

STATS={}


def set_stat(stat, value):
    STATS[stat] = value

def inc_stat(stat, amount=1):
    STATS[stat] = STATS.get(stat, 0) + amount


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
            time.sleep(10)
            #s = {k:v for k,v in self.__dict__.items() if not k.startswith('_')}
            log.info(f"STATS: ID: {STATS}")


class StatTracker(object):

    def __init__(self, start=None, end=None, default=-1, maxlen=None):
        self.fetch_times = {}
        self.averages = {}
        self.counts = {}
        self.maxlen = 25

        if maxlen:
            self.maxlen = maxlen

        if start is not None and end is not None:
            if end < start:
                inc = -1
            else:
                inc = 1

            for i in range(start, end, inc):
                self.averages[i] = default
                self.counts[i] = default


    def set(self, key, value):
        self.counts[key] = self.counts.get(key, 0) + 1
        self.fetch_times.setdefault(key, collections.deque(maxlen=self.maxlen)).append(value)
        self.averages[key] = round(sum(self.fetch_times.get(key))/len(self.fetch_times.get(key)), 3)
