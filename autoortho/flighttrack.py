#!/usr/bin/env python3

import os
import time
import socket
import threading
from aoconfig import CFG
import logging
log = logging.getLogger(__name__)

from flask import Flask, render_template, url_for, request, jsonify

from xp_udp import DecodePacket, RequestDataRefs

from aostats import STATS
#STATS = {'count': 71036, 'chunk_hit': 66094, 'mm_counts': {0: 19, 1: 39, 2: 97, 3: 294, 4: 2982}, 'mm_averages': {0: 0.56, 1: 0.14, 2: 0.04, 3: 0.01, 4: 0.0}, 'chunk_miss': 4942, 'bytes_dl': 65977757}

RUNNING=True

app = Flask(__name__)

class FlightTracker(object):
    
    lat = -1
    lon = -1
    alt = -1
    hdg = -1
    spd = -1
    t = None

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP

        self.sock.settimeout(5.0)
        self.connected = False

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.t = threading.Thread(target=self._udp_listen)
        self.t.start()

    def get_info(self):
        RequestDataRefs(self.sock)
        data, addr = self.sock.recvfrom(1024)
        values = DecodePacket(data)
        lat = values[0][0]
        lon = values[1][0]
        alt = values[3][0]
        hdg = values[4][0]
        spd = values[6][0]

        return (lat, lon, alt, hdg, spd)

    def _udp_listen(self):
        log.debug("Listen!")
        RequestDataRefs(self.sock)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
            except socket.timeout:
                if self.connected:
                    # We are transitioning states
                    log.info("FT: Flight disconnected.")
                    self.start_time = time.time()

                self.connected = False
                log.debug("Socket timeout.  Reset.")
                RequestDataRefs(self.sock)
                time.sleep(2)
                continue
            except ConnectionResetError: 
                log.debug("Connection reset.")
                time.sleep(2)
                continue
            except Exception as err:
                log.debug(f"Some other error {err}")
                time.sleep(5)
                continue

            if not self.connected:
                # We are transitioning states
                log.info("FT: Flight is starting.")
                delta = time.time() - self.start_time
                log.info(f"FT: Time to start was {round(delta/60, 2)} minutes.")
                STATS['minutes_to_start'] = round(delta/60, 2)

            self.connected = True

            values = DecodePacket(data)
            lat = values[0][0]
            lon = values[1][0]
            alt = values[3][0]
            hdg = values[4][0]
            spd = values[6][0]

            log.debug(f"Lat: {lat}, Lon: {lon}, Alt: {alt}")
            
            self.alt = alt
            self.lat = lat
            self.lon = lon
            self.hdg = hdg
            self.spd = spd

            time.sleep(0.5)

        log.info("UDP listen thread exiting...")

    def stop(self):
        log.info("FlightTracker shutdown requested.")
        self.running=False
        if self.t:
            self.t.join()
        log.info("FlightTracker exiting.")

ft = FlightTracker()

@app.route('/get_latlon')
def get_latlon():
    lat = ft.lat
    lon = ft.lon
    #lat, lon, alt, hdg, spd = ft.get_info()
    log.debug(f"{lat} X {lon}")
    return jsonify({"lat":lat,"lon":lon})

@app.route("/")
def index():
    return render_template(
        "index.html"
    )

@app.route("/map")
def map():
    return render_template(
        "map.html"
    )

@app.route("/stats")
def stats():
    #graphs = [ x for x in STATS.keys() ]
    return render_template(
        "stats.html",
        graphs=STATS
    )

@app.route("/metrics")
def metrics():
    return STATS

def run():
    app.run(host='0.0.0.0', debug=True, threaded=True, use_reloader=False)


def main():
    ft.start()
    try:
        app.run(host='0.0.0.0', debug=True, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Shutdown requested.")
    finally:
        print("App exiting...")
        ft.stop()
    print("Done!")

if __name__ == "__main__":
    main()
