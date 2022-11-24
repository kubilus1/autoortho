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
#logging.basicConfig()
logging.basicConfig(filename='autoortho.log')
log = logging.getLogger('log')
if os.environ.get('AO_DEBUG'):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

import psutil
from PIL import Image

MEMTRACE = False

# Use ispc for compression instead of stb
ISPC = True


#from memory_profiler import profile

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
mm_fetch_times = {}
mm_averages = {
    0:-1,
    1:-1,
    2:-1,
    3:-1,
    4:-1
}
mm_counts = {}
zl_counts = {}

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
        
        self.count = 0
        self.queue = PriorityQueue()
        self.workers = []
        self.WORKING = True
        self.localdata = threading.local()

        for i in range(num_workers):
            t = threading.Thread(target=self.worker, args=(i,), daemon=True)
            t.start()
            self.workers.append(t)

        self.stat_t = t = threading.Thread(target=self.show_stats, daemon=True)
        self.stat_t.start()


    def stop(self):
        self.WORKING = False
        for t in self.workers:
            t.join()
        self.stat_t.join()

    def worker(self, idx):
        self.localdata.idx = idx
        while self.WORKING:
            try:
                obj, args, kwargs = self.queue.get(timeout=5)
                #log.debug(f"Got: {obj} {args} {kwargs}")
            except Empty:
                #log.debug(f"timeout, continue")
                #log.info(f"Got {self.counter}")
                continue

            self.count += 1

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

    def show_stats(self):
        while self.WORKING:
            log.info(f"{self.__class__.__name__} got: {self.count}")
            time.sleep(10)
        log.info(f"Exiting {self.__class__.__name__} stat thread.  Got: {self.count} total")


class ChunkGetter(Getter):
    def get(self, obj, *args, **kwargs):
        if obj.ready.is_set():
            log.info(f"{obj} already retrieved.  Exit")
            return True

        kwargs['idx'] = self.localdata.idx
        #log.debug(f"{obj}, {args}, {kwargs}")
        return obj.get(*args, **kwargs)

chunk_getter = ChunkGetter(32)

#class TileGetter(Getter):
#    def get(self, obj, *args, **kwargs):
#        log.debug(f"{obj}, {args}, {kwargs}")
#        return obj.get(*args)
#
#tile_getter = TileGetter(8)

log.info(f"chunk_getter: {chunk_getter}")
#log.info(f"tile_getter: {tile_getter}")


class Chunk(object):
    col = -1
    row = -1
    source = None
    chunk_id = ""
    priority = 0
    width = 256
    height = 256
    cache_dir = 'cache'

    ready = None
    data = None
    img = None

    serverlist=['a','b','c','d']

    def __init__(self, col, row, maptype, zoom, priority=0):
        self.col = col
        self.row = row
        self.zoom = zoom
        self.maptype = maptype
        
        # Hack override maptype
        #self.maptype = "BI"

        if not priority:
            self.priority = zoom
        self.chunk_id = f"{col}_{row}_{zoom}_{maptype}"
        self.ready = threading.Event()
        self.ready.clear()
        if maptype == "Null":
            self.maptype = "EOX"

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.cache_path = os.path.join(self.cache_dir, f"{self.chunk_id}.jpg")

    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return f"Chunk({self.col},{self.row},{self.maptype},{self.zoom},{self.priority})"

    def get_cache(self):
        if os.path.isfile(self.cache_path):
            with open(self.cache_path, 'rb') as h:
                self.data = h.read()
            return True
        else:
            return False

    def save_cache(self):
        with open(self.cache_path, 'wb') as h:
            h.write(self.data)

    def get(self, idx=0):
        #log.debug(f"Getting {self}") 

        if self.get_cache():
            self.ready.set()
            return True

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
        except Exception as err:
            log.warning(f"Failed to get chunk {self} on server {server}. Err: {err}")
            return False
       
        if resp.status != 200:
            log.warning(f"Failed with status {resp.status} to get chunk {self} on server {server}.")
            return False
    
        try:
            #self.img = Image.open(resp).convert("RGBA")
            #self.img.load()
            self.data = resp.read()
        finally:
            resp.close()

        self.save_cache()
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
    min_zoom = 11
    cache_dir = './cache'
    width = 16
    height = 16

    priority = -1
    #tile_condition = None
    tile_lock = None
    ready = None 

    chunks = None
    cache_file = None
    dds = None

    refs = 0

    def __init__(self, col, row, maptype, zoom, min_zoom=0, priority=0, cache_dir='./cache'):
        self.row = int(row)
        self.col = int(col)
        self.maptype = maptype
        self.zoom = int(zoom)
        self.chunks = {}
        self.cache_file = (-1, None)
        self.ready = threading.Event()
        self.tile_lock = threading.RLock()
        #self.tile_condition = threading.Condition()
        if min_zoom:
            self.min_zoom = int(min_zoom)

        if cache_dir:
            self.cache_dir = cache_dir
        
        # Hack override maptype
        #self.maptype = "BI"

        #self._find_cached_tiles()
        self.ready.clear()
        
        #self._find_cache_file()

        if not priority:
            self.priority = zoom

        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.dds = pydds.DDS(self.width*256, self.height*256, ispc=ISPC)
        self.id = f"{row}_{col}_{maptype}_{zoom}"


    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return f"Tile({self.col}, {self.row}, {self.maptype}, {self.zoom}, {self.min_zoom}, {self.cache_dir})"

    def _create_chunks(self, quick_zoom=0):
        col, row, width, height, zoom, zoom_diff = self._get_quick_zoom(quick_zoom)

        with self.tile_lock:
            if not self.chunks.get(zoom):
                self.chunks[zoom] = []

                for r in range(row, row+height):
                    for c in range(col, col+width):
                        chunk = Chunk(c, r, self.maptype, zoom, priority=self.priority)
                        self.chunks[zoom].append(chunk)

    def _find_cache_file(self):
        #with self.tile_condition:
        with self.tile_lock:
            for z in range(self.zoom, (self.min_zoom-1), -1):
                cache_file = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{z}.dds")
                if os.path.exists(cache_file):
                    log.info(f"Found cache for {cache_file}...")
                    self.cache_file = (z, cache_file)
                    self.ready.set()
                    return

        #log.info(f"No cache found for {self}!")


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
        #with self.tile_condition:
        with self.tile_lock:
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


    def find_mipmap_pos(self, offset):
        for m in self.dds.mipmap_list:
            if offset < m.endpos:
                return m.idx


    def get_bytes(self, offset, length):

        mipmap = self.find_mipmap_pos(offset)
        log.info(f"Get_bytes for mipmap {mipmap} ...")
        if mipmap > 4:
            # Just get the entire mipmap
            self.get_mipmap(4)
            return True

        # Exit if already retrieved
        if self.dds.mipmap_list[mipmap].retrieved:
            log.info(f"We already have mipmap {mipmap} for {self}")
            return True

        mm = self.dds.mipmap_list[mipmap]
        if length >= mm.length:
            self.get_mipmap(mipmap)
            return True
        
        log.info(f"Retrieving {length} bytes from mipmap {mipmap} offset {offset}")

        bytes_per_row = 1048576 >> mipmap
        rows_per_mipmap = 16 >> mipmap

        # how deep are we in a mipmap
        mm_offset = max(0, offset - self.dds.mipmap_list[mipmap].startpos)
        log.info(f"MM_offset: {mm_offset}  Offset {offset}.  Startpos {self.dds.mipmap_list[mipmap]}")

        # Calculate which row 'offset' is in
        startrow = mm_offset >> (20 - mipmap)
        # Calculate which row 'offset+length' is in
        endrow = (mm_offset + length) >> (20 - mipmap)
       
        log.info(f"Startrow: {startrow} Endrow: {endrow}")
        
        new_im = self.get_img(mipmap, startrow, endrow)
        if not new_im:
            log.debug("No updates, so no image generated")
            return True

        self.ready.clear()
        #log.info(new_im.size)
        try:
            self.dds.gen_mipmaps(new_im, mipmap, 1)
        finally:
            new_im.close()

        # We haven't fully retrieved so unset flag
        self.dds.mipmap_list[mipmap].retrieved = False
        self.ready.set()

        return True

    def read_dds_bytes(self, offset, length):
        log.debug(f"READ DDS BYTES: {offset} {length}")
        
        mm_idx = self.find_mipmap_pos(offset)
        mipmap = self.dds.mipmap_list[mm_idx]
        
        if offset == 0:
            # If offset = 0, read the header
            log.debug("TILE: Read header")
            self.get_bytes(0, length)
        elif offset < 131072:
            # How far into mipmap 0 do we go before just getting the whole thing
            log.debug("TILE: Middle of mipmap 0")
            self.get_bytes(0, length + offset)
        elif (offset + length) < mipmap.endpos:
            # Total length is within this mipmap.  Make sure we have it.
            log.debug(f"TILE: Detected middle read for mipmap {mipmap.idx}")
            if not mipmap.retrieved:
                log.debug(f"TILE: Retrieve {mipmap.idx}")
                self.get_mipmap(mipmap.idx)
        else:
            # We already know we start before the end of this mipmap
            # We must extend beyond the length.
            
            # Get bytes prior to this mipmap
            self.get_bytes(offset, length)

            # Get the entire next mipmap
            self.get_mipmap(mm_idx + 1)

        # Seek and return data
        self.dds.seek(offset)
        return self.dds.read(length)



    def _read_dds_bytes(self, offset, length):
        log.debug(f"READ DDS BYTES: {offset} {length}")
        with self.tile_lock:
            if offset == 0:
                # If offset = 0, read the header
                log.debug("TILE: Read header")
                self.get_bytes(0, length)
            #elif offset < 16777344:
            #elif offset < 65536:
            #elif offset < 16777000:
            elif offset < 131072:
                # How far into mipmap 0 do we go before just getting the whole thing
                log.debug("TILE: Middle of mipmap 0")
                self.get_bytes(0, length + offset)
            else:
                log.debug("TILE: Read full mipmap ...")
                # For first mipmap.startpos in range of offset and offset + length, get mipmap and return data
                for mipmap in self.dds.mipmap_list:
                    log.debug(f"TILE: mip start: {mipmap.startpos}, mip end: {mipmap.endpos}, offset: {offset}, len: {length}")
                    if mipmap.startpos <= offset and (offset + length) < mipmap.endpos:
                        # Offset seek is in middle of mipmap.  Check if retrieval needed"
                        #
                        # The requested offset is equal to or after this mipmap's starting position
                        # AND the offset + length is before the end.
                        #
                        # This should be a read in the middle of a mipmap somewhere.  Fetch if needed.
                        #

                        log.debug(f"TILE: Detected middle read for mipmap {mipmap.idx}")
                        if not mipmap.retrieved:
                            log.debug(f"TILE: Retrieve {mipmap.idx}")
                            self.get_mipmap(mipmap.idx)
                        break
                    elif offset <= mipmap.startpos < (offset + length):
                        # Offset is before mipmap start, length is after start.  Check if retrieval is needed
                        #
                        # The requested offset is equal to or before this mipmap's starting position
                        # AND the offset + length is after the starting position.
                        #
                        # This indicates a read that starts before this mimap and continues somewhere into this
                        # mipmap.  Fetch if needed.


                        #log.debug(f"TILE: Detected spanning read for {self} mipmap {mipmap.idx}. Get prior mipmap")
                        #log.info(f"TILE: Retrieve mipmap {mipmap.idx - 1}")
                        #self.get_mipmap(mipmap.idx-1)
                        log.debug(f"TILE: Detected spanning read for {self} mipmap {mipmap.idx}. Get mipmap")

                        # Get bytes prior to this mipmap
                        self.get_bytes(offset, length)

                        # Get the entire current mipmap
                        if not mipmap.retrieved:
                            self.get_mipmap(mipmap.idx)
                        # if not mipmap.retrieved:
                        #     log.info(f"TILE: Retrieve {mipmap.idx}")
                        #     self.get_mipmap(mipmap.idx)
                        # else:
                        #     log.info(f"TILE: Already retrieved")
                        #     log.info(self.dds.mipmap_list)
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


    def get_img(self, mipmap, startrow=0, endrow=None):
        #
        # Get an image for a particular mipmap
        #

        zoom = self.zoom - mipmap
        log.info(f"Default zoom: {self.zoom}, Requested Mipmap: {mipmap}, Requested mipmap zoom: {zoom}")
        col, row, width, height, zoom, mipmap = self._get_quick_zoom(zoom)
        log.debug(f"Will use:  Zoom: {zoom},  Mipmap: {mipmap}")

    
        log.debug(self.dds.mipmap_list)
        if self.dds.mipmap_list[mipmap].retrieved:
            log.info(f"We already have mipmap {mipmap} for {self}")
            return

        startchunk = 0
        endchunk = None
        # Determine start and end chunk
        chunks_per_row = 16 >> mipmap
        if startrow:
            startchunk = startrow * chunks_per_row
        if endrow is not None:
            endchunk = (endrow * chunks_per_row) + chunks_per_row


        self._create_chunks(zoom)
        chunks = self.chunks[zoom][startchunk:endchunk]
        log.info(f"Start chunk: {startchunk}  End chunk: {endchunk}  Chunklen {len(self.chunks[zoom])}")

        #if True:
        with self.tile_lock:
            log.info(f"TILE: {self} : Retrieve mipmap for ZOOM: {zoom} MIPMAP: {mipmap}")
            data_updated = False
            for chunk in chunks:
                if not chunk.ready.is_set():
                    chunk_getter.submit(chunk)
                    data_updated = True

            # We've already determined this mipmap is not marked as 'retrieved' so we should create 
            # a new image, regardless here.
            #if not data_updated:
            #    log.info("No updates to chunks.  Exit.")
            #    return False

            #outfile = os.path.join(self.cache_dir, f"{self.row}_{self.col}_{self.maptype}_{self.zoom}_{self.zoom}.dds")
            #new_im = Image.new('RGBA', (256*width,256*height), (250,250,250))
            log.info(f"Create new image: Zoom: {self.zoom} | {(256*width, 256*height)}")
            new_im = Image.new('RGBA', (256*width,256*height), (0,0,0))
            #log.info(f"NUM CHUNKS: {len(chunks)}")
            for chunk in chunks:
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
        
        return new_im


    #@profile
    def get_mipmap(self, mipmap=0):
        
        new_im = self.get_img(mipmap)
        if not new_im:
            log.debug("No updates, so no image generated")
            return True

        self.ready.clear()
        start_time = time.time()
        try:
            #with self.tile_lock:
            self.dds.gen_mipmaps(new_im, mipmap) 
        finally:
            new_im.close()

        end_time = time.time()
        self.ready.set()

        zoom = self.zoom - mipmap
        tile_time = end_time - start_time
        mm_counts[mipmap] = mm_counts.get(mipmap, 0) + 1
        mm_fetch_times.setdefault(mipmap, collections.deque(maxlen=25)).append(tile_time)
        mm_averages[mipmap] = sum(mm_fetch_times.get(mipmap))/len(mm_fetch_times.get(mipmap))
        log.info(f"Fetched MM {mipmap} for ZL {zoom} in {tile_time} seconds")
        log.info(f"Average Fetch times: {mm_averages}")
        log.info(f"MM counts: {mm_counts}")

        if mipmap == 0:
            log.debug("Will close all chunks.")
            for z,chunks in self.chunks.items():
                for chunk in chunks:
                    chunk.close()
            self.chunks = {}
                    #del(chunk.data)
                    #del(chunk.img)
        #return outfile
        log.debug("Results:")
        log.debug(self.dds.mipmap_list)
        return True


    def close(self):
        log.info(f"Closing {self}")

        if self.refs > 0:
            log.warning(f"TILE: Trying to close, but has refs: {self.refs}")
            return

        for chunks in self.chunks.values():
            for chunk in chunks:
                chunk.close()
        self.chunks = {}
        


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


class TileCacher(object):
    min_zoom = 13
    max_zoom = 18

    tiles = {}

    hits = 0
    misses = 0

    def __init__(self, cache_dir='.cache', maptype_override=None):
        if MEMTRACE:
            tracemalloc.start()
        self.maptype_override = maptype_override
        self.tc_lock = threading.RLock()
        self.cache_dir = cache_dir
        self.clean_t = threading.Thread(target=self.clean, daemon=True)
        self.clean_t.start()

    def clean(self):
        memlimit = pow(2,30) * 2
        log.info(f"Started tile clean thread.  Mem limit {memlimit}")
        while True:
            process = psutil.Process(os.getpid())
            cur_mem = process.memory_info().rss
            log.info(f"NUM TILES CACHED: {len(self.tiles)}.  TOTAL MEM: {cur_mem//1048576} MB")
            while len(self.tiles) >= 90 and cur_mem > memlimit:
                log.info("Hit cache limit.  Remove oldest 20")
                with self.tc_lock:
                    for i in list(self.tiles.keys())[:20]:
                        t = self.tiles.get(i)
                        if t.refs <= 0:
                            t = self.tiles.pop(i)
                            t.close()
                            t = None
                            del(t)
                cur_mem = process.memory_info().rss
            log.info(f"TILE CACHE:  MISS: {self.misses}  HIT: {self.hits}")


            if MEMTRACE:
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')

                log.info("[ Top 10 ]")
                for stat in top_stats[:10]:
                        log.info(stat)

            time.sleep(15)

    def _get_tile(self, row, col, map_type, zoom):
        if self.maptype_override:
            map_type = self.maptype_override

        idx = f"{row}_{col}_{map_type}_{zoom}"

        log.debug(f"Get_tile: {idx}")
        with self.tc_lock:
            tile = self.tiles.get(idx)
            if not tile:
                self.misses += 1
                tile = Tile(col, row, map_type, zoom, cache_dir =
                    self.cache_dir)
                self.tiles[idx] = tile
            elif tile.refs <= 0:
                # Only in this case would this cache have made a difference
                self.hits += 1

        return tile

