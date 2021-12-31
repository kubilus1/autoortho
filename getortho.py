#!/usr/bin/env python3

import os
import sys
import time
import subprocess
from io import BytesIO
import threading
from urllib.request import urlopen, Request
from queue import Queue, PriorityQueue
import tempfile


import logging
logging.basicConfig()
log = logging.getLogger('log')
log.setLevel(logging.INFO)

from PIL import Image


def do_url(url, headers={}):
    req = Request(url, headers=headers)
    resp = urlopen(req, timeout=5)
    return resp.read()

MAPID = "s2cloudless-2020_3857"
MATRIXSET = "g"

##

import socket
import struct

##


class GetOrtho(object):

    serverlist=['a','b','c','d']
    chunk_work_queue = PriorityQueue()
    tile_work_queue = Queue()
    WORKING=True
    chunk_workers = []
    tile_workers = []
    active_tiles = []
    tile_lock = threading.Lock()
    tile_condition = threading.Condition()

    chunk_condition = threading.Condition()
    active_chunks = []


    def __init__(self, chunk_threads=16, tile_threads=4, dds_convert=True):
        self.dds_convert = dds_convert
 
        log.info("Starting ortho worker threads.")
        for t in range(chunk_threads):
            server = self.serverlist[t%4]
            t = threading.Thread(target=self.chunk_worker, args=(server))
            t.start()
            self.chunk_workers.append(t)
        #for t in chunk_workers:
        #    t.join()

        for t in range(tile_threads):
            t = threading.Thread(target=self.tile_worker)
            t.start()
            self.tile_workers.append(t)


    def _gtile_to_quadkey(self, til_x, til_y, zoomlevel):
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


    def chunk_worker(self, server):
        while self.WORKING:
            try:
                priority, (col, row, zoom, maptype, chunks) = self.chunk_work_queue.get()
                self.get_chunk(server, col, row, zoom, maptype, chunks)
            except Exception as err:
                log.warning("Something went wrong.  IDK")
                log.warning(err)

    def tile_worker(self):
        while self.WORKING:
            col, row, zoom, quick_zoom, maptype, outfile, priority = self.tile_work_queue.get()
            log.info(f"Tile worker, got work {outfile}")
            try:
                if quick_zoom:
                    self.get_quick_tile(col, row, zoom, quick_zoom, maptype=maptype, outfile=outfile)
                else:
                    self.get_tile(col, row, zoom, maptype=maptype, outfile=outfile, priority=priority)
            except Exception as err:
                log.error(err)

    def get_chunk(self, server, col, row, zoom, maptype, chunks):
        log.debug(f"Getting {col} {row} {zoom} {maptype}") 
        if maptype == "Null":
            maptype = "EOX"

        chunk_id = f"{col}_{row}_{zoom}_{maptype}"
        with self.chunk_condition:
            while chunk_id in self.active_chunks:
                log.error(f"{chunk_id} Chunk already being worked on!")
                self.chunk_condition.wait()
            self.active_chunks.append(chunk_id)
        

        server_num = self.serverlist.index(server) 
        quadkey = self._gtile_to_quadkey(col, row, zoom)


        # Hack override maptype
        #maptype = "ARC"

        MAPTYPES = {
            "EOX": f"https://{server}.s2maps-tiles.eu/wmts/?layer={MAPID}&style=default&tilematrixset={MATRIXSET}&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix={zoom}&TileCol={col}&TileRow={row}",
            "BI": f"http://r{server_num}.ortho.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=136",
            "GO2": f"http://mt{server_num}.google.com/vt/lyrs=s&x={col}&y={row}&z={zoom}",
            "ARC": f"http://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{row}/{col}",
            "USGS": f"https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{zoom}/{row}/{col}"
        }
        url = MAPTYPES[maptype]

        try:
            chunks[f"{row}-{col}-{zoom}"] = do_url(
                url,
                {
                    "user-agent": "curl/7.68.0"
                }
            )
        except:
            log.warning(f"Failed to get chunk {row} {col} {zoom} on server {server}.  Return to queue...")
            # chunks.pop(f"{row}-{col}-{zoom}")
            with self.chunk_condition:
                if chunk_id in self.active_chunks:
                    self.active_chunks.remove(chunk_id)
                    self.chunk_condition.notify_all()

            self.chunk_work_queue.put((1, (col, row, zoom, maptype, chunks)))
            return False

        with self.chunk_condition:
            if chunk_id in self.active_chunks:
                self.active_chunks.remove(chunk_id)
                self.chunk_condition.notify_all()

        return True

    def get_chonk(self, tilecol, tilerow, zoom, width=16, height=16, maptype="EOX", priority=0):
        CHUNKS = {}
        REQLIST = []

        for col in range(tilecol, tilecol+width):
            for row in range(tilerow, tilerow+height):
                self.chunk_work_queue.put((priority, (col, row, zoom, maptype, CHUNKS)))


        while len(CHUNKS.keys()) < (width*height):
            time.sleep(0.1)

        log.debug("Done getting chonk")
        #log.debug(CHUNKS.keys())
        return CHUNKS


    def get_quick_tile(self, tilecol, tilerow, zoom, quick_zoom=12, width=16, height=16, maptype="EOX", priority=1, outfile=None):
        zoom_diff = min((zoom - quick_zoom), 3)
        quick_col = int(tilecol/pow(2,zoom_diff))
        quick_row = int(tilerow/pow(2,zoom_diff))
        quick_width = int(width/pow(2,zoom_diff))
        quick_height = int(height/pow(2,zoom_diff))

        if not outfile:
            outfile = f"{tilerow}-{tilecol}-{maptype}-{zoom}.dds"

        try:
            self.get_tile(quick_col, quick_row, quick_zoom, quick_width, quick_height, maptype=maptype, outfile=outfile, priority=priority)
        except Exception as err:
            log.error(err)
        #self.get_fake_tile(0,0,0,outfile=outfile)


    def get_background_tile(self, tilecol, tilerow, zoom, quick_zoom=0, width=16, height=16, maptype="EOX", outfile=None, priority=10):
        self.tile_work_queue.put((tilecol, tilerow, zoom, quick_zoom, maptype, outfile, priority))

    def get_fake_tile(self, tilecol, tilerow, zoom, width=16, height=16, maptype="EOX", outfile=None):
        subprocess.call(
            #f"convert {tempfile} {outfile}",
            f"nvcompress -bc1 -fast smile.png {outfile}",
            shell=True
        )

    

    def get_tile(self, tilecol, tilerow, zoom, width=16, height=16, maptype="EOX", outfile=None, priority=5):
        if not outfile:
            outfile = f"{tilerow}-{tilecol}-{maptype}-{zoom}.dds"
        
        #wait_for_tile = False
        #tile_id = f"{tilerow}-{tilecol}-{maptype}-{zoom}" 
        # with self.tile_lock:
        #     if tile_id not in self.active_tiles:
        #         self.active_tiles.append(tile_id)
        #     else:
        #         wait_for_tile = True 

        # if wait_for_tile: 
        #     log.info(f"{tile_id} already being retrieved.  Waiting...")
        #     while tile_id in self.active_tiles:
        #         time.sleep(0.1)
        #     log.info(f"{tile_id} done.  Exiting.")
        #     return


        wait_for_tile = False
        with self.tile_condition:
            if outfile not in self.active_tiles:
                 self.active_tiles.append(outfile)
            else:
                while outfile in self.active_tiles:
                    wait_for_tile = True
                    log.info(f"{outfile} already being retrieved.  Waiting...")
                    self.tile_condition.wait()

        if wait_for_tile:
            log.info(f"Done waiting for other process to retreive {outfile}.  Exiting.")
            return

        log.info(f"Retrieving tile {tilerow} x {tilecol} x {zoom} ....")
        start_time = time.time()


        CHUNKS = self.get_chonk(tilecol, tilerow, zoom, width, height, maptype, priority)

        new_im = Image.new('RGB', (256*width,256*height), (250,250,250))
        for col in range(width):
            for row in range(height):
                img_data = CHUNKS[f"%s-%s-{zoom}" % (
                    tilerow+row,
                    tilecol+col
                )]
                img = Image.open(BytesIO(img_data))
                new_im.paste(img, (256*col,256*row))
                #log.debug(f"Pasting at {col},{row}")

        
        #new_im.show()
        #tempfile =  f"{tilerow}-{tilecol}-{zoom}.jpg"
        if self.dds_convert:
            with tempfile.NamedTemporaryFile(suffix=".jpg") as t:
                #new_im.resize((4096,4096))
                new_im.save(t.name, "JPEG")
                subprocess.check_call(
                    #f"convert {tempfile} {outfile}",
                    f"nvcompress -bc3 -fast {t.name} {outfile}",
                    shell=True
                )
        else:
            new_im.save(outfile, "JPEG")

        end_time = time.time()
        log.info(f"Retrieved tile {outfile} : {tilerow} x {tilecol} x {zoom} in %s seconds" % (end_time - start_time))
        #new_im.save(outfile, "DDS")
        
        #with self.tile_lock:
        #    self.active_tiles.remove(tile_id)

        with self.tile_condition:
            if outfile in self.active_tiles:
                self.active_tiles.remove(outfile)
            self.tile_condition.notify_all()

if __name__ == "__main__":
    go = GetOrtho()
    go.get_tile(2080, 3056, 13)
