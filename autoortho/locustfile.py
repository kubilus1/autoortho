import os
import time
import random
import tempfile
from functools import wraps
import threading
import multiprocessing
import subprocess

from locust import User, task, events

from aoconfig import CFG
import getortho
import autoortho

from contextlib import contextmanager


@contextmanager
def pushd(new_dir):
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)

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
        #request_meta["response"] = fn(self, *args, **kwargs)
        #request_meta["response_length"]  = len(request_meta["response"])
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
    def __init__(self, request_event):
        #self.path = path
        self.row = 24000
        self.col = 12000

        self.name = "test"
        self._request_event = request_event
        self.tmpdir = tempfile.mkdtemp()
        self.mount = '.'
        
        tile = getortho.Tile(self.row, self.col, 'BI', 16, cache_dir=self.tmpdir)
        self.mm4start = tile.dds.mipmap_list[4].startpos
        self.mm4len = tile.dds.mipmap_list[4].length

        return

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
        row = self.row + 16
        col = self.col + 16
        return self.do_read(row, col, 8388672)

    @stats
    def read_mm_0_rand(self):
        row = (random.randint(0, 256) * 16) + self.row
        col = (random.randint(0, 256) * 16) + self.col
        return self.do_read(row, col, 8388672)
    
    @stats
    def read_header(self):
        row = self.row + 16
        col = self.col + 16
        return self.do_read(row, col, 128)

    @stats
    def read_header_rand(self):
        row = (random.randint(0, 256) * 16) + self.row
        col = (random.randint(0, 256) * 16) + self.col
        return self.do_read(row, col, 128)


    def do_read(self, row, col, numbytes, seekbytes=0):
        global mount
        testfile = os.path.join("..", "textures", f"{row}_{col}_BI16.dds")
        with pushd(os.path.join(mount, "terrain")):
            with open(testfile, "rb") as h:
                if seekbytes:
                    h.seek(seekbytes)
                data = h.read(numbytes)

        return data

    @stats
    def read_mm_4(self):
        row = self.row + 16
        col = self.col + 16
        return self.do_read(row, col, self.mm4len, self.mm4start)

    @stats
    def read_mm_4_rand(self):
        row = (random.randint(0, 256) * 16) + self.row
        col = (random.randint(0, 256) * 16) + self.col
        return self.do_read(row, col, self.mm4len, self.mm4start)


class DDSRead(User):
    abstract = True

    def __init__(self, environment):
        super().__init__(environment)
        self.client = DDSClient(
                #self.path,
                request_event=environment.events.request
        )




@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global mount
    tmpdir = tempfile.mkdtemp()
    root = os.path.join(tmpdir, 'root')
    os.makedirs(os.path.join(root, 'textures'))
    os.makedirs(os.path.join(root, 'terrain'))
    mount = os.path.join(tmpdir, 'mount')
    os.makedirs(mount)

    print("A new test is starting")
    print("About to setup AO Mount ...")
    run_ao_popen(root, mount)
    #run_ao_mp(root, mount)
    #run_ao_fork(root, mount)
    print("Done with on_start")
    return

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    global mount
    print("A new test is ending")
    mounted = True
    while mounted:
        print(f"Shutting down {mount}")
        print("Send poison pill ...")
        mounted = os.path.isfile(os.path.join(
            mount,
            ".poison"
        ))
        time.sleep(0.5)



def run_ao_popen(root, mount):
    print(f"Popen.  Root: {root}, Mount: {mount}")
    subprocess.Popen([
        "python3",
        "run_ao_locust.py",
        root,
        mount
    ])
    time.sleep(5)
    print("Return from Popen")

def run_ao_fork(root, mount):
    pid = os.fork()
    if pid > 0:
        print(f"Parent pid {pid}")
        ao_domount(root, mount)
        print("Parend pid done!")
    else:
        print(f"Child pid, return")
        return

def ao_domount(root, mount):
    aom = autoortho.AOMount(CFG)
    aom.domount(
        root, 
        mount, 
    )
    # Blocks forever

def run_ao_mp(root, mount):
    print("Run AO MP")
    mount_p = multiprocessing.Process(
        target=ao_domount,
        args=(
            root,
            mount
        )
    )
    mount_p.start()
    print("AO MP return")
    return
    

    aom = autoortho.AOMount(CFG)
    mount_p = multiprocessing.Process(
        target=aom.domount,
        args=(
            root,
            mount
        )
    )
    print("AO Proc created.  Starting ...")

    mount_p.start()
    print("AO Proc started ...")
    #time.sleep(5)
    #print("AO wait complete ...")
    #return aom


class DDSUser(DDSRead):
    #path = "./mount"
    #path = "/home/mkubilus/Software/xplane/autoortho/Custom Scenery/z_autoortho/textures"
    print(CFG.paths)
    #path = os.path.join(CFG.paths.scenery_path, 'z_autoortho', 'textures')
    #print(f"Testing against {path}")


    @task(1)
    def read_mm0(self):
        self.client.read_mm_0()

    @task(1)
    def read_mm0_rand(self):
        self.client.read_mm_0_rand()

    @task(10)
    def read_header(self):
        self.client.read_header()

    @task(25)
    def read_header_rand(self):
        self.client.read_header_rand()

    @task(10)
    def read_mm4(self):
        self.client.read_mm_4()

    @task(50)
    def read_mm4_rand(self):
        self.client.read_mm_4_rand()

