
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
import struct

class SkynetDecode:

	def __init__(self, definitions_file):
		self.packets_by_address = self.load_defs(definitions_file)

	def load_defs(self, file):
		defs = json.load(file)
		by_address = {}

		for d in defs:
			by_address[d["address"]] = d

		return by_address

	def decode(self, address, rtr, data_bytes):

		if address not in self.packets_by_address:
			return None

		d = self.packets_by_address[address]

		packet = {}

		packet["name"] = d["name"]
		packet["board"] = d["board"]
		packet["data"] = {}

		byte = 0

		if d["endian"] == "little":
			endian = "<"
		else:
			endian = ">"

		for field in d["data"]:

			if field["type"] == "uint8_t":
				format = "B"
				length = 1
			elif field["type"] == "int8_t":
				format = "b"
				length = 1
			elif field["type"] == "uint16_t":
				format = endian + "H"
				length = 2
			elif field["type"] == "int16_t":
				format = endian + "h"
				length = 2
			elif field["type"] == "uint32_t":
				format =  endian + "I"
				length = 4
			elif field["type"] == "int32_t":
				format = endian + "i"
				length = 4
			elif field["type"] == "float":
				format = endian + "f"
				length = 4

			bytes = bytearray(data_bytes[byte:byte+length])
			data = struct.unpack(format, bytes)[0]
			packet["data"][field["name"]] = data
			byte += length
			# TODO: implement scale

		return packet


	def print_defs(self):
		print(self.packets_by_address)

if __name__ == "__main__":
	with open('static/packets.json') as f:
		d = SkynetDecode(f)
		d.print_defs()