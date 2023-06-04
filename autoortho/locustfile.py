import os
import time
import random
import tempfile
from functools import wraps
from locust import User, task

from aoconfig import CFG
import getortho

def stats(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        request_meta = {
            "request_type": "getortho",
            "name": self.name,
            "start_time": time.time(),
            "response_length": 0,  # calculating this for an xmlrpc.client response would be too hard
            "response": None,
            "context": {},  # see HttpUser if you actually want to implement contexts
            "exception": None,
        }
        start_perf_counter = time.perf_counter()
        try:
            request_meta["response"] = fn(self, *args, **kwargs)
            request_meta["response_length"]  = len(request_meta["response"])
        except Exception as e:
            request_meta["exception"] = e
        request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
        self._request_event.fire(**request_meta)  # This is what makes the request actually get logged in Locust
        return request_meta["response"]

    return wrapper


class DDSClient():
    def __init__(self, path, request_event):
        self.path = path
        self.name = "test"
        self._request_event = request_event
        self.tmpdir = tempfile.mkdtemp()
        #CFG.pydds.compressor = "STB"
        #self.row = (random.randint(0, 256) * 16) + 2000
        #self.col = (random.randint(0, 256) * 16) + 3000
        self.row = 20000
        self.col = 10000

    @stats
    def get_mm(self, mm=0):
        tile = getortho.Tile(self.row, self.col, 'BI', 16, cache_dir=self.tmpdir)
        tile.get_mipmap(mm)
        mm_info = tile.dds.mipmap_list[mm]
        #print(f"{mm_info.startpos} --- {mm_info.endpos}")
        ret = tile.read_dds_bytes(mm_info.startpos, mm_info.endpos) 
        return ret

    @stats
    def get_header(self):
        tile = getortho.Tile(self.row, self.col, 'BI', 16, cache_dir=self.tmpdir)
        ret = tile.read_dds_bytes(0, 128) 
        #ret = tile.get_header()
        return ret

    @stats
    def read_mm_0(self):
        #row = (random.randint(0, 256) * 16) + 20000
        #col = (random.randint(0, 256) * 16) + 30000
        row = self.row + 16
        col = self.col + 16
        
        testfile = os.path.join(self.path, f"{row}_{col}_BI16.dds")
        #print(testfile)

        with open(testfile, "rb") as h:
            header = h.read(128)
            data = h.read(16777344)

        return data

    @stats
    def read_mm_4(self):
        #row = (random.randint(0, 256) * 16) + 20000
        #col = (random.randint(0, 256) * 16) + 30000
        row = self.row
        col = self.col
        testfile = os.path.join(self.path, f"{row}_{col}_BI16.dds")

        with open(testfile, "rb") as h:
            #header = h.read(128)
            h.seek(22282368)
            data = h.read(65536)

        return data

    @stats
    def read_header(self):
        row = (random.randint(0, 256) * 16) + 20000
        col = (random.randint(0, 256) * 16) + 30000
        row = self.row
        col = self.col
        testfile = os.path.join(self.path, f"{row}_{col}_BI16.dds")
        with open(testfile, "rb") as h:
            header = h.read(128)

        return header

class DDSRead(User):
    abstract = True

    def __init__(self, environment):
        super().__init__(environment)
        self.client = DDSClient(
                self.path,
                request_event=environment.events.request
        )


class DDSUser(DDSRead):
    #path = "./mount"
    #path = "/home/mkubilus/Software/xplane/autoortho/Custom Scenery/z_autoortho/textures"
    print(CFG.paths)
    path = os.path.join(CFG.paths.scenery_path, 'z_autoortho', 'textures')
    print(f"Testing against {path}")

    @task(1)
    def read_mm0(self):
        self.client.read_mm_0()

    #@task(20)
    def read_header(self):
        self.client.read_header()

    @task(20)
    def read_mm4(self):
        self.client.read_mm_4()

    #@task(1)
    def get_mm0(self):
        self.client.get_mm(0)

    #@task(20)
    def get_header(self):
        self.client.get_header()

    #@task(50)
    def get_mm4(self):
        self.client.get_mm(4)
