
import json

class SkynetDecode:

	def __init__(self, definitions_file):
		self.defs = {}

	def load_defs(file):
		definitions = json.load(definitions_file)

		for d in definitions:
			board = d["board"]
			packet_name = d["name"]
			address = d["address"]



	def print_defs(self):
		print(self.defs)



if __name__ == "__main__":
	with open('static/packets.json') as f:
		d = SkynetDecode(f)
		d.print_defs()