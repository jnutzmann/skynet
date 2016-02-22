# Copyright (c) 2016, Jonathan Nutzmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import json
import time
from threading import Thread
from queue import Queue
from skynet_parse import SkynetDecode
from influxdb import InfluxDBClient



class SkyNetDBLogger(Thread):

    def __init__(self, port, serial_connection, db):
        Thread.__init__(self)
        self.port = port
        self.q = Queue()
        self.s = serial_connection
        self.db = db
        
        with open('static/packets.json') as f:
            self.decoder = SkynetDecode(f)

        # create a listener that can be attached to a serial port.
        def listener(timestamp, address, rtr, data_length, data_bytes, origin="device"):
            
            decoded = self.decoder.decode(address, rtr, data_bytes)

            point = {
                "measurement": decoded["name"],
                "time": int(timestamp*1e9),
                "tags": {
                    "board": decoded["board"],
                    "name": self.s.name,
                    "rtr": str(rtr),
                    "origin": origin
                },
                "fields": decoded["data"]
            }

            self.q.put(point)

        self.listener = listener
        self.s.listeners.append(self.listener)

    def run(self):
        try:
            while True:
                points = []
                time.sleep(1)  # wait for more points (only make influx call 1/sec)
                
                points.append(self.q.get())
                
                while not self.q.empty():
                    points.append(self.q.get())
                
                try:
                    self.db.client.write_points(points)
                except Exception as e:
                    print(e)
                
                print(len(points))

        except Exception:
            self.s.listeners.remove(self.listener)
