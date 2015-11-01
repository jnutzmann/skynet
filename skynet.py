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

import os
import json
from skynet_serial import SkyNetSerial
from flask import Flask, render_template, request, Response, abort
from queue import Queue


class ServerSentEvent(object):

    def __init__(self, data):
        self.data = data
        self.event = None
        self.id = None
        self.desc_map = {
            self.data : "data",
            self.event : "event",
            self.id : "id"
        }

    def encode(self):
        if not self.data:
            return ""
        lines = ["%s: %s" % (v, k)
                 for k, v in self.desc_map.items() if k]
        return "%s\n\n" % "\n".join(lines)


app = Flask(__name__)

serial_connections = {}


def get_serial_ports():
    ports = []
    for dirname, dirnames, filenames in os.walk('/dev/serial/by-id/'):
        for filename in filenames:
            ports.append(filename)
    return ports


@app.route('/')
def index():
    conn_ports = serial_connections
    avail_ports = []
    for p in get_serial_ports():
        if p not in conn_ports:
            avail_ports.append(p)

    return render_template('index.html', avail_ports=avail_ports, conn_ports=conn_ports)


@app.route('/serial/connect')
def serial_connect():

    _id = request.args.get('port')
    baud = int(request.args.get('baud'))
    name = request.args.get('name')

    port = "/dev/serial/by-id/%s" % _id

    s = SkyNetSerial(serial_port=port, baud=baud, name=name)
    s.start()
    serial_connections[_id] = s

    return "OK"


@app.route('/serial/view/<port>')
def serial_view(port):
    if port not in serial_connections:
        print('aborting')
        abort(404)
    return render_template('default.html', s=serial_connections[port], port=port)


@app.route('/serial/stream/<port>')
def serial_stream(port):

    q = Queue()
    s = serial_connections[port]

    def listener(timestamp, address, rtr, data_length, data_bytes):

        o = {
            "timestamp": timestamp,
            "address": address,
            "rtr": rtr,
            "length": data_length,
            "data": data_bytes
        }

        q.put(o)

    def gen():
        s.listeners.append(listener)

        try:
            while True:
                r = q.get()
                ev = ServerSentEvent(json.dumps(r))
                yield ev.encode()
        except GeneratorExit:
            s.listeners.remove(listener)

    return Response(gen(), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
