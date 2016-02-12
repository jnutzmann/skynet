# Copyright (c) 2015, Jonathan Nutzmann
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


class SkyNetLogger(Thread):

    def __init__(self, port, serial_connection):
        Thread.__init__(self)
        self.port = port
        self.q = Queue()
        self.s = serial_connection

        def listener(timestamp, address, rtr, data_length, data_bytes):
            o = {
                "timestamp": timestamp,
                "address": address,
                "rtr": rtr,
                "length": data_length,
                "data": data_bytes
            }

            self.q.put(o)
        self.listener = listener
        self.s.listeners.append(self.listener)

    def run(self):
        with open("%s_%i.log" % (self.s.name, time.time()), 'w') as f:
            try:
                while True:
                    r = self.q.get()
                    f.write(json.dumps(r) + "\n")

            except Exception:
                self.s.listeners.remove(self.listener)
