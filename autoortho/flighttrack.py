#!/usr/bin/env python3

import logging
import platform
import socket
import threading
import time

from aoconfig import CFG

log = logging.getLogger(__name__)
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from xp_udp import DecodePacket, RequestDataRefs

from aostats import STATS

RUNNING = True

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

if platform.system().lower() == 'darwin':
    local_host = '127.0.0.1'
else:
    local_host = '0.0.0.0'


class FlightTracker(object):
    lat = -1
    lon = -1
    alt = -1
    hdg = -1
    spd = -1
    t = None

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET,  # Internet
                                  socket.SOCK_DGRAM)  # UDP

        self.sock.settimeout(5.0)
        self.connected = False
        self.running = False
        self.num_failures = 0

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.t = threading.Thread(target=self._udp_listen)
        self.t.start()

    def get_info(self):
        RequestDataRefs(self.sock, CFG.flightdata.xplane_udp_port)
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
        RequestDataRefs(self.sock, CFG.flightdata.xplane_udp_port)
        while self.running:
            time.sleep(0.1)
            try:
                data, addr = self.sock.recvfrom(1024)
            except socket.timeout:

                if self.connected:
                    # We were connected but lost a packet.  First just log
                    # this
                    self.num_failures += 1
                    log.debug("We are connected but a packet timed out.  NBD.")

                if self.num_failures > 3:
                    # We are transitioning states
                    log.info("FT: Flight disconnected.")
                    self.start_time = time.time()
                    self.connected = False
                    self.running = False
                    self.num_failures = 0

                    # log.debug("Socket timeout.  Reset.")
                    # RequestDataRefs(self.sock, CFG.flightdata.xplane_udp_port)
                time.sleep(1)
                continue
            except ConnectionResetError:
                log.debug("Connection reset.")
                time.sleep(1)
                continue

            self.num_failures = 0
            if not self.connected:
                # We are transitioning states
                log.info("FT: Flight is starting.")
                delta = time.time() - self.start_time
                log.info(f"FT: Time to start was {round(delta / 60, 2)} minutes.")
                STATS['minutes_to_start'] = round(delta / 60, 2)

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

        log.info("UDP listen thread exiting...")

    def stop(self):
        log.info("FlightTracker shutdown requested.")
        self.running = False
        if self.t:
            self.t.join()
        log.info("FlightTracker exiting.")


ft = FlightTracker()


@socketio.on('connect')
def connect():
    log.info(f'client connected {request.sid}')


@socketio.on('disconnect')
def disconnect():
    log.info(f'client disconnected {request.sid}')


@socketio.on('handle_latlon')
def handle_latlon():
    log.info("Handle lat lon.")
    while True:
        lat = ft.lat
        lon = ft.lon
        # lat, lon, alt, hdg, spd = ft.get_info()
        log.debug(f"emit: {lat} X {lon}")
        socketio.emit('latlon', {"lat": lat, "lon": lon})
        socketio.sleep(2)


@socketio.on("handle_metrics")
def handle_metrics():
    log.info("Handle metrics.")
    while True:
        socketio.emit('metrics', STATS or {"init": 1})
        socketio.sleep(5)


@app.route('/get_latlon')
def get_latlon():
    lat = ft.lat
    lon = ft.lon
    # lat, lon, alt, hdg, spd = ft.get_info()
    log.debug(f"{lat} X {lon}")
    return jsonify({"lat": lat, "lon": lon})


@app.route("/")
def index():
    return render_template(
        "index.html"
    )


@app.route("/map")
def map():
    return render_template(
        "map.html",
        mapkey=""
    )


@app.route("/stats")
def stats():
    # graphs = [ x for x in STATS.keys() ]
    return render_template(
        "stats.html",
        graphs=STATS
    )


@app.route("/metrics")
def metrics():
    return STATS


def run():
    # app.run(host='0.0.0.0', port=CFG.flightdata.webui_port, debug=CFG.general.debug, threaded=True, use_reloader=False)
    log.info("Start flighttracker...")
    socketio.run(app, host=local_host, port=int(CFG.flightdata.webui_port))
    log.info("Exiting flighttracker ...")


def main():
    ft.start()
    try:
        app.run(host=local_host, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Shutdown requested.")
    finally:
        print("App exiting...")
        ft.stop()
    print("Done!")


if __name__ == "__main__":
    main()
