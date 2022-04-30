#!/usr/bin/env python3

import os
import sys
import time
import math
import tempfile
import threading
import subprocess
import collections

from io import BytesIO
from urllib.request import urlopen, Request
from queue import Queue, PriorityQueue, Empty

import pydds

import logging
logging.basicConfig()
log = logging.getLogger('log')
log.setLevel(logging.INFO)

from PIL import Image

def do_url(url, headers={}):
    req = Request(url, headers=headers)
    resp = urlopen(req, timeout=5)
    if resp.status != 200:
        raise Exception
    return resp.read()

MAPID = "s2cloudless-2020_3857"
MATRIXSET = "g"

##

import socket
import struct

##

# Track average fetch times
tile_fetch_times = {}
tile_averages = {
    20:-1,
    19:-1,
    18:-1,
    17:-1,
    16:-1,
    15:-1,
    14:-1,
    13:-1,
    12:-1
}

def _gtile_to_quadkey(til_x, til_y, zoomlevel):
    """
    Translates Google coding of tiles to Bing Quadkey coding. 
    """
    quadkey=""
    temp_x=til_x
    temp_y=til_y    
    for step in range(1,zoomlevel+1):
        size=2**(zoomlevel-step)
        a=temp_x//size
        b=temp_y//size
        temp_x=temp_x-a*size
        temp_y=temp_y-b*size
        quadkey=quadkey+str(a+2*b)
    return quadkey

class Getter(object):
    queue = None 
    workers = None
    WORKING = False

    def __init__(self, num_workers):
        
        self.queue = PriorityQueue()
        self.workers = []
        self.WORKING = True
        self.localdata = threading.local()

        for i in range(num_workers):
            t = threading.Thread(target=self.worker, args=(i,), daemon=True)
            t.start()
            self.workers.append(t)

    def stop(self):
        self.WORKING = False
        for t in self.workers:
            t.join()

    def worker(self, idx):
        self.localdata.idx = idx
        while self.WORKING:
            try:
                obj, args, kwargs = self.queue.get(timeout=5)
                #log.debug(f"Got: {obj} {args} {kwargs}")
            except Empty:
                #log.debug(f"timeout, continue")
                continue

            try:
                if not self.get(obj, *args, **kwargs):
                    log.warning(f"Failed getting: {obj} {args} {kwargs}, re-submit.")
                    self.submit(obj, *args, **kwargs)
            except Exception as err:
                log.error(f"ERROR {err} getting: {obj} {args} {kwargs}, re-submit.")
                self.submit(obj, *args, **kwargs)

    def get(obj, *args, **kwargs):
        raise NotImplementedError

    def submit(self, obj, *args, **kwargs):
        self.queue.put((obj, args, kwargs))

class ChunkGetter(Getter):
    def get(self, obj, *args, **kwargs):
        if obj.ready.is_set():
            log.info(f"{obj} already retrieved.  Exit")
            return True

        kwargs['idx'] = self.localdata.idx
        #log.debug(f"{obj}, {args}, {kwargs}")
        return obj.get(*args, **kwargs)

chunk_getter = ChunkGetter(32)

class TileGetter(Getter):
    def get(self, obj, *args, **kwargs):
        log.debug(f"{obj}, {args}, {kwargs}")
        return obj.get(*args)

tile_getter = TileGetter(8)

log.info(f"chunk_getter: {chunk_getter}")
log.info(f"tile_getter: {tile_getter}")


class Chunk(object):
    col = -1
    row = -1
    source = None
    chunk_id = ""
    priority = 0
    width = 256
    height = 256

    ready = None
    data = None
    img = None

    serverlist=['a','b','c','d']

    def __init__(self, col, row, maptype, zoom, priority=0):
        self.col = col
        self.row = row
        self.zoom = zoom
        self.maptype = maptype
        if not priority:
            self.priority = zoom
        self.chunk_id = f"{col}_{row}_{zoom}_{maptype}"
        self.ready = threading.Event()
        self.ready.clear()
        if maptype == "Null":
            self.maptype = "EOX"

    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return f"Chunk({self.col},{self.row},{self.maptype},{self.zoom},{self.priority})"

    def get(self, idx=0):
        #log.debug(f"Getting {self}") 

        server_num = idx%(len(self.serverlist))
        server = self.serverlist[server_num]
        quadkey = _gtile_to_quadkey(self.col, self.row, self.zoom)

        # Hack override maptype
        #maptype = "ARC"

        MAPTYPES = {
            "EOX": f"https://{server}.s2maps-tiles.eu/wmts/?layer={MAPID}&style=default&tilematrixset={MATRIXSET}&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix={self.zoom}&TileCol={self.col}&TileRow={self.row}",
            "BI": f"http://r{server_num}.ortho.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=136",
            "GO2": f"http://mt{server_num}.google.com/vt/lyrs=s&x={self.col}&y={self.row}&z={self.zoom}",
            "ARC": f"http://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{self.zoom}/{self.row}/{self.col}",
            "USGS": f"https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{self.zoom}/{self.row}/{self.col}"
        }
        url = MAPTYPES[self.maptype.upper()]
        #log.debug(f"{self} getting {url}")
        header = {
                "user-agent": "curl/7.68.0"
        }
        try:
            req = Request(url, headers=header)
            resp = urlopen(req, timeout=5)
        except:
            log.warning(f"Failed to get chunk {self} on server {server}.")
            return False
       
        if resp.status != 200:
            log.warning(f"Failed with status {resp.status} to get chunk {self} on server {server}.")
            return False
    
        try:
            #self.img = Image.open(resp).convert("RGBA")
            #self.img.load()
            self.data = resp.read()
        finally:
            pass
            resp.close()

        self.ready.set()
        return True

    def close(self):
        self.data = None
        #self.img.close()
        #del(self.img)


class Tile(object):
    row = -1
    col = -1
    maptype = None
    zoom = -1
    min_zoom = 12
    cache_dir = './cache'
    width = 16
    height = 16

    priority = -1
    tile_condition = None
    tile_lock = None
    ready = None 

    chunks = None
    cache_file = None
    dds = None

    def __init__(self, col, row, maptype, zoom, min_zoom=0, priority=0, cache_dir='./cache'):
        self.row = int(row)
        self.col = int(col)
        self.maptype = maptype
        self.zoom = int(zoom)
        self.chunks = {}
        self.cache_file = (-1, None)
        self.ready = threading.Event()
        self.tile_lock = threading.Lock()
        self.tile_condition = threading.Condition()
        if min_zoom:
            self.min_zoom = int(min_zoom)

        if cache_dir:
            self.cache_dir = cache_dir

        #self._find_cached_tiles()
        self.ready.clear()
        self._find_cache_file()

        if not priority:
            self.priority = zoom

        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.dds = pydds.DDS(self.width*256, self.height*256)

    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return f"Tile({self.col}, {self.row}, {self.maptype}, {self.zoom}, {self.min_zoom}, {self.cache_dir})"

    def _create_chunks(self, quick_zoom=0):
        col, row, width, height, zoom, zoom_diff = self._get_quick_zoom(quick_zoom)

        if not self.chunks.get(zoom):
            self.chunks[zoom] = []

            for r in range(row, row+height):
                for c in range(col, col+width):
                    chunk = Chunk(c, r, self.maptype, zoom, priority=self.priority)
                    self.chunks[zoom].append(chunk)

    def _find_cache_file(self):
        with self.tile_condition:
            for z in range(self.zoom, (self.min_zoom-1), -1):
                cache_file = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{z}.dds")
                if os.path.exists(cache_file):
                    log.info(f"Found cache for {cache_file}...")
                    self.cache_file = (z, cache_file)
                    self.ready.set()
                    return

        log.info(f"No cache found for {self}!")


    def _get_quick_zoom(self, quick_zoom=0):
        if quick_zoom:
            # Max difference in steps this tile can support
            max_diff = min((self.zoom - int(quick_zoom)), 4)
            # Minimum zoom level allowed
            min_zoom = self.zoom - max_diff
            
            # Effective zoom level we will use 
            quick_zoom = max(int(quick_zoom), min_zoom)

            # Effective difference in steps we will use
            zoom_diff = min((self.zoom - int(quick_zoom)), 4)

            col = int(self.col/pow(2,zoom_diff))
            row = int(self.row/pow(2,zoom_diff))
            width = int(self.width/pow(2,zoom_diff))
            height = int(self.height/pow(2,zoom_diff))
            zoom = int(quick_zoom)
        else:
            col = self.col
            row = self.row
            width = self.width
            height = self.height
            zoom = self.zoom
            zoom_diff = 0

        return (col, row, width, height, zoom, zoom_diff)


    def fetch(self, quick_zoom=0, background=False):
        self._create_chunks(quick_zoom)
        col, row, width, height, zoom, zoom_diff = self._get_quick_zoom(quick_zoom)

        for chunk in self.chunks[zoom]:
            chunk_getter.submit(chunk)

        for chunk in self.chunks[zoom]:
            ret = chunk.ready.wait()
            if not ret:
                log.error("Failed to get chunk.")

        return True
   

    def write_cache_tile(self, quick_zoom=0):

        col, row, width, height, zoom, zoom_diff = self._get_quick_zoom(quick_zoom)

        outfile = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{zoom}.dds")

        new_im = Image.new('RGBA', (256*width,256*height), (250,250,250))
        try:
            for chunk in self.chunks[zoom]:
                ret = chunk.ready.wait()
                if not ret:
                    log.error("Failed to get chunk")

                start_x = int((chunk.width) * (chunk.col - col))
                start_y = int((chunk.height) * (chunk.row - row))
                #end_x = int(start_x + chunk.width)
                #end_y = int(start_y + chunk.height)

                new_im.paste(
                    Image.open(BytesIO(chunk.data)).convert("RGBA"),
                    (
                        start_x,
                        start_y
                    )
                )

            self.ready.clear()
            #pydds.to_dds(new_im, outfile)
            self.dds.gen_mipmaps(new_im)
            self.dds.write(outfile)
        except:
            #log.error(f"Error detected for {self} {outfile}, remove possibly corrupted files.")
            #os.remove(outfile)
            raise
        finally:
            log.debug("Done")
            new_im.close()

        log.info(f"Done writing {outfile}")
        self.ready.set()


    def get(self, quick_zoom=0, background=False):
        
        self.ready.clear()
        zoom = int(quick_zoom) if quick_zoom else self.zoom

        #if self.cache_file[0] < zoom:
        log.info(f"Will get tile")
        start_time = time.time()
        with self.tile_condition:
            self.fetch(quick_zoom, background)
            self.write_cache_tile(quick_zoom)
        end_time = time.time()
        tile_time = end_time - start_time
        log.info(f"Retrieved tile cachefile: {self.cache_file} in {tile_time} seconds.")
        tile_fetch_times.setdefault(zoom, collections.deque(maxlen=10)).append(tile_time)
        tile_averages[zoom] = sum(tile_fetch_times.get(zoom))/len(tile_fetch_times.get(zoom))      
        log.info(f"Fetch times: {tile_averages}")

        self._find_cache_file()
        return self.cache_file[1]


    def get_bytes(self, length):
        if self.dds.mipmap_list[0].retrieved:
            log.info(f"We already have mipmap 0 for {self}")
            return True

        numrows = length >> 20 # Divide by 1048576
        #log.debug(f"BYTES: {pydds.get_size(256,256)}")
        if length % 1048576:
            numrows += 1

        numchunks = 16*numrows

        self._create_chunks()
        #outfile = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{self.zoom}.dds")
        
        # Determine height based on number of rows we will retrieve
        height = math.ceil(numchunks/self.width)
        new_im = Image.new('RGBA', (256*self.width,256*height), (250,0,0))

        data_updated = False
        with self.tile_condition:
            for chunk in self.chunks[self.zoom][0:numchunks]:
                if not chunk.ready.is_set():
                    data_updated = True
                    chunk_getter.submit(chunk)

            if not data_updated:
                log.info("No updates to bytes.  Exit.")
                return True

            for chunk in self.chunks[self.zoom][0:numchunks]:
                ret = chunk.ready.wait()
                if not ret:
                    log.error("Failed to get chunk")

                start_x = int((chunk.width) * (chunk.col - self.col))
                start_y = int((chunk.height) * (chunk.row - self.row))
                new_im.paste(
                    #chunk.img, 
                    Image.open(BytesIO(chunk.data)).convert("RGBA"),
                    (
                        start_x,
                        start_y
                    )
                )

            self.ready.clear()

            #new_im = new_im.convert("RGBA")
            log.info(new_im.size)
            try:
                self.dds.gen_mipmaps(new_im, 0, 1)
            finally:
                new_im.close()

            # We haven't fully retrieved so unset flag
            self.dds.mipmap_list[0].retrieved = False
            self.ready.set()

        return True


    def read_dds_bytes(self, offset, length):
        with self.tile_lock:
            if offset == 0:
                # If offset = 0, read the header
                log.debug("TILE: Read header")
                self.get_bytes(length)
            else:
                # For first mipmap.startpos in range of offset and offset + length, get mipmap and return data
                for mipmap in self.dds.mipmap_list:
                    log.debug(f"TILE: mip start: {mipmap.startpos}, mip end: {mipmap.endpos}, offset: {offset}, len: {length}")
                    if mipmap.startpos <= offset and (offset + length) < mipmap.endpos:
                        # Offset seek is in middle of mipmap.  Check if retrieval needed"
                        log.debug(f"TILE: Detected middle read for mipmap {mipmap.idx}")
                        if not mipmap.retrieved:
                            log.debug(f"TILE: Retrieve {mipmap.idx}")
                            self.get_mipmap(mipmap.idx)
                        break
                    elif offset <= mipmap.startpos < (offset + length):
                        # Offset is before mipmap start, length is after start.  Check if retrieval is needed
                        log.debug(f"TILE: Detected spanning read for mipmap {mipmap.idx}")
                        if not mipmap.retrieved:
                            log.debug(f"TILE: Retrieve {mipmap.idx}")
                            self.get_mipmap(mipmap.idx)
                        break


            self.dds.seek(offset)
            return self.dds.read(length)



    def write(self):
        outfile = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{self.zoom}.dds")
        self.ready.clear()
        self.dds.write(outfile)
        self.ready.set()
        return outfile

    def get_header(self):
        outfile = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{self.zoom}.dds")
        
        self.ready.clear()
        self.dds.write(outfile)
        self.ready.set()
        return outfile


    def get_mipmap(self, mipmap=0):
        
        zoom = self.zoom - mipmap
        log.debug(f"Default zoom: {self.zoom}, Requested Mipmap: {mipmap}, Requested mipmap zoom: {zoom}")
        col, row, width, height, zoom, mipmap = self._get_quick_zoom(zoom)
        log.debug(f"Will use:  Zoom: {zoom},  Mipmap: {mipmap}")

        #mipmap = min(mipmap, 4)

        log.debug(self.dds.mipmap_list)
        if self.dds.mipmap_list[mipmap].retrieved:
            log.info(f"We already have mipmap {mipmap} for {self}")
            return

        self._create_chunks(zoom)

        log.info(f"Retrive mipmap for ZOOM: {zoom} MIPMAP: {mipmap}")
        data_updated = False
        for chunk in self.chunks[zoom]:
            if not chunk.ready.is_set():
                chunk_getter.submit(chunk)
                data_updated = True

        if not data_updated:
            log.info("No updates to chunks.  Exit.")
            return True

        #outfile = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{self.zoom}.dds")
        #new_im = Image.new('RGBA', (256*width,256*height), (250,250,250))
        new_im = Image.new('RGBA', (256*width,256*height), (0,0,250))
        for chunk in self.chunks[zoom]:
            ret = chunk.ready.wait()
            if not ret:
                log.error("Failed to get chunk.")

            start_x = int((chunk.width) * (chunk.col - col))
            start_y = int((chunk.height) * (chunk.row - row))
            new_im.paste(
                #chunk.img, 
                Image.open(BytesIO(chunk.data)).convert("RGBA"),
                (
                    start_x,
                    start_y
                )
            )

        self.ready.clear()
        try:
            self.dds.gen_mipmaps(new_im, mipmap) 
        finally:
            new_im.close()

        self.ready.set()
        
        if mipmap == 0:
            log.debug("Will close all chunks.")
            for z,chunks in self.chunks.items():
                for chunk in chunks:
                    chunk.close()
                    #del(chunk.data)
                    #del(chunk.img)
        #return outfile
        return True


    def close(self):
        log.info(f"Closing {self}")

        for chunks in self.chunks.values():
            for chunk in chunks:
                chunk.close()
        


class CacheFile(object):
    file_condition = threading.Condition()
    path = None

    # EMPTY, WRITING, READY
    state = None


class Map(object):

    tiles = []

    def __init__(self, cache_dir="./cache"):
        self.cache_dir = cache_dir

    def get_tiles(self, col, row, maptype, zoom, quick_zoom=0, background=False):
        t = Tile(col, row, maptype, zoom, cache_dir=self.cache_dir) 

        if background:
            tile_getter.submit(t, quick_zoom)
            self.tiles.append(t)
            ret = True
        else:
            ret = t.get(quick_zoom)
        return ret
