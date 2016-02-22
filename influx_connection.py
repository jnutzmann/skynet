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

from influxdb import InfluxDBClient
from strict_rfc3339 import rfc3339_to_timestamp


class SkynetInflux:

    def __init__(self):

        # TODO: make this configurable.
        # connect to the influx server
        self.client = InfluxDBClient('localhost', 8086, 'root', 'root', 'skynet')
        self.client.create_database('skynet', if_not_exists=True)

    def get_results_for_plot(self, query):
        pts = self.client.query(query)        
        results = list(pts.get_points())
        
        retval = []

        if len(results) > 0:

            keys = list(results[0].keys())
            keys.remove('time')
            f = keys[0]

            for r in results:
                t = rfc3339_to_timestamp(r['time'])
                d = r[f]

                retval.append([t,d])

        return retval

        # for s in series:
        #     root = ".".join([s["tags"][0]["board"], s["tags"][0]["name"], s["name"]])

        #     rs = self.client.query("SELECT * FROM %s WHERE board='%s' AND name='%s' LIMIT 1" %
        #         (s["name"], s["tags"][0]["board"], s["tags"][0]["name"]))
        #     qr = list(rs.get_points())[0]
        #     subs = []

        #     for k in qr.keys():
        #         if k not in ['time', 'name', 'board', 'rtr']:
        #             measurements.append(root + "." + k)

        # return sorted(measurements)

    def get_measurements(self):
        series = self.client.get_list_series()
        measurements = []

        for s in series:
            try:
                root = ".".join([s["tags"][0]["board"], s["tags"][0]["name"], s["name"]])

                query = "SELECT * FROM %s WHERE board='%s' AND name='%s' LIMIT 1" % (s["name"], s["tags"][0]["board"], s["tags"][0]["name"])
                rs = self.client.query(query)
                qr = list(rs.get_points())[0]

                for k in qr.keys():
                    if k not in ['time', 'name', 'board', 'rtr', 'origin']:
                        measurements.append(root + "." + k)

            except Exception as e:
                print(e)

        return sorted(measurements)

    def get_points(measurement, start, stop, limit):

        board, name, packet, data = measurement.split('.')

        q = "SELECT %s FROM %s WHERE board='%s' AND name='%s' LIMIT %i"