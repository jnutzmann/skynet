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

import serial
import time
from threading import Thread


class SkyNetSerial(Thread):

    ESCAPE_CHARACTER = b'\x7D'
    START_OF_FRAME = b'\x7E'

    def __init__(self, serial_port='/dev/ttyUSB0', baud=500000, name=''):

        super(SkyNetSerial, self).__init__()

        self.serial_port = serial_port
        self.baud = baud

        self._port_handle = None
        self.running = False
        self.error = False
        self.name = name

        self.listeners = []

    def stop(self):
        self.running = False
        self.join()

    def get(self):
        return self.data_queue.get()

    def run(self):
        self._port_handle = serial.Serial(self.serial_port, self.baud)

        self.running = True
        escaped = False
        data_bytes = []
        meta_bytes = []
        crc_bytes = []
        data_length = 0
        address = 0
        rtr = False
        timestamp = 0

        # wait for the next start-of-frame
        c = self._port_handle.read()
        while c != self.START_OF_FRAME:
            c = self._port_handle.read()

        while self.running:
            try:
                c = self._port_handle.read()

                if c == self.START_OF_FRAME:
                    timestamp = time.time()
                    data_bytes = []
                    meta_bytes = []
                    crc_bytes = []
                    continue

                if c == self.ESCAPE_CHARACTER:
                    escaped = True
                    continue

                c = ord(c)

                if escaped:
                    c ^= 0x20
                    escaped = False
                
                if len(meta_bytes) == 0:
                    meta_bytes.append(c)
                elif len(meta_bytes) == 1:
                    meta_bytes.append(c)
                    address = (meta_bytes[1] // 32 + meta_bytes[0] * 8) 
                    rtr = not not(meta_bytes[1] & 16)
                    data_length = meta_bytes[1] & 15
                elif len(data_bytes) < data_length:
                    data_bytes.append(c)
                elif len(crc_bytes) == 0:
                    crc_bytes.append(c)
                    # TODO: verify CRC when implemented
                    for l in self.listeners:
                        l(timestamp, address, rtr, data_length, data_bytes)
                else:
                    pass
            except Exception as e:
                self.error = True
                break

        self.running = False

