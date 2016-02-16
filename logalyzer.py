
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

class InfluxLogalyzer:

	def __init__(self, server='localhost', port=8086, username='root', password='root', database='skynet'):

		self.client = InfluxDBClient(server, port, username, password, database)

	def get_measurements(self):
		series = self.client.get_list_series()
		
		measurements = []

		for s in series:
			root = ".".join([s["tags"][0]["board"], s["tags"][0]["name"], s["name"]])

			rs = self.client.query("SELECT * FROM %s WHERE board='%s' AND name='%s' LIMIT 1" %
				(s["name"], s["tags"][0]["board"], s["tags"][0]["name"]))
			qr = list(rs.get_points())[0]
			subs = []

			for k in qr.keys():
				if k not in ['time', 'name', 'board', 'rtr']:
					measurements.append(root + "." + k)

		return sorted(measurements)

	def get_points(measurement, start, stop, limit):

		board, name, packet, data = measurement.split('.')

		q = "SELECT %s FROM %s WHERE board='%s' AND name='%s' LIMIT %i"


if __name__ == "__main__":

	l = InfluxLogalyzer()
	for m in l.get_measurements():
		print(m)