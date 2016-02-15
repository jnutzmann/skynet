
import json

class SkynetDecode:

	def __init__(self, definitions_file):
		self.packets_by_address = self.load_defs(definitions_file)

	def load_defs(self, file):
		defs = json.load(file)
		by_address = {}

		for d in defs:
			by_address[d["address"]] = d

		return by_address

	def decode(address, rtr, data_length, data_bytes):

		if address not in self.packets:
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
				pass
			elif field["type"] == "int8_t"





	def print_defs(self):
		print(self.packets_by_address)

if __name__ == "__main__":
	with open('static/packets.json') as f:
		d = SkynetDecode(f)
		d.print_defs()