

function streamPackets(callback)
{
	var source = new EventSource('/magic/json_source');

	source.addEventListener('message', function(e) {
	    callback($.parseJSON(e.data));
	});
}

function sendPacket(packet) {
    $.ajax("/magic/send_packet", {type: "POST", data: packet});
}

var packetFormatByID = [];
var packetFormatByName = {};
var packetFormats;

var packetFormatsReadyCB = []
var packetFormatsReady = false

$(function() {
    $.getJSON("packets.json",function (data) {
        packetFormats = data.packets;
        for (typenum in data.packets) {
            packetFormatByID[data.packets[typenum].id] = data.packets[typenum];
            packetFormatByName[data.packets[typenum].name] = data.packets[typenum];
        }

        packetFormatsReady = true;
        for (i in packetFormatsReadyCB){
            packetFormatsReadyCB[i](packetFormats);
        }
    });
});

function registerPacketsReadyCallback(fxn){
    if(packetFormatsReady){
        fxn(packetFormats);
    }else{
        packetFormatsReadyCB.push(fxn);
    }
}

function decodePacket(packet) {

    if (!(packet.id in packetFormatByID)) return;

    var byte = 0;
    var format = packetFormatByID[packet.id];
    var endian = 'little';
    var littleEndian = (format.endian == 'little');

    packet.name = format.name;
    packet.f = {};
	packet.i = {};

    var field_data;

    var buffer = new ArrayBuffer(8);
	var asBytes = new Uint8Array(buffer);

    for (var i in packet.data) {
        asBytes[i] = packet.data[i];
    }

	dv = new DataView(buffer);
    for (field_num in format.data) {
        switch (format.data[field_num].type) {
        case "uint8_t":
            field_data = dv.getUint8(byte);
            byte += 1;
            break;
        case "int8_t":
            field_data = dv.getInt8(byte);
            byte += 1;
            break;
        case "uint16_t":
			field_data = dv.getUint16(byte, littleEndian);
            byte += 2;
            break;
        case "int16_t":
            field_data = dv.getInt16(byte, littleEndian);
            byte += 2;
            break;
        case "uint32_t":
            field_data = dv.getUint32(byte, littleEndian);
            byte += 4;
            break;
        case "int32_t":
            field_data = dv.getInt32(byte, littleEndian);
            byte += 4;
            break;
	    case "float":
			field_data = dv.getFloat32(byte, littleEndian);
			byte += 4;
			break;
        case "bitfield":
            field_data = uint8p(packet, byte);
            for (bit_num in format.data[field_num].bits) {
				var bitval = (field_data & (1 << bit_num)) ? 1 : 0;
                packet.f[format.data[field_num].bits[bit_num].name] = bitval;
				packet.i[format.data[field_num].bits[bit_num].name] = {
					'value':(bitval),
					'cvalue':(bitval),
					'unit':'bool'
				}
            }
            byte += 1;
            break;
        }

		var fmtdata = format.data[field_num]
        packet.f[fmtdata.name] = field_data;
		packet.i[fmtdata.name] = {}
		packet.i[fmtdata.name]['value'] = field_data

		if("conversion" in fmtdata){
			//conversion data is available,  we should convert to std units
			packet.i[fmtdata.name]['cvalue'] = (field_data*fmtdata['conversion'])
		}else{
			//otherwise don't convert
			packet.i[fmtdata.name]['cvalue'] = field_data
		}
		if("unit" in fmtdata){
			packet.i[fmtdata.name]['unit'] = fmtdata['unit']
		}else{
			packet.i[fmtdata.name]['unit'] = "" //no units
		}
    }
}
function encodePacket(packet) {
    if (!(packet.id in packetFormatByID)) return;
    var byte = 0;
    var format = packetFormatByID[packet.id];

	var buffer = new ArrayBuffer(8);
	var asBytes = new Uint8Array(buffer);
	var dv = new DataView(buffer, 0);
	var littleEndian = (format.endian == 'little')

    packet.data = [];

    for (field_num in format.data) {
	switch (format.data[field_num].type) {
	    case "uint8_t":
			dv.setUint8(byte, packet.f[format.data[field_num].name]);
			byte += 1;
		break;
	    case "int8_t":
			dv.setInt8(byte, packet.f[format.data[field_num].name]);
		byte += 1;
		break;
	    case "uint16_t":
			dv.setUint16(byte, packet.f[format.data[field_num].name], littleEndian);
			byte += 2;
		break;
	    case "int16_t":
			dv.setInt16(byte, packet.f[format.data[field_num].name], littleEndian);
			byte += 2;
		break;
	    case "uint32_t":
			dv.setUint32(byte, packet.f[format.data[field_num].name], littleEndian);
			byte += 4;
		break;
	    case "int32_t":
			dv.setInt32(byte, packet.f[format.data[field_num].name], littleEndian);
			byte += 4;
		break;
	    case "float":
			dv.setFloat32(byte, packet.f[format.data[field_num].name], littleEndian);
			byte += 4;
		break;
	    case "bitfield":
			output = 0;
			for(bit in format.data[field_num].bits){
				if(packet.f[format.data[field_num].bits[bit].name]){
					output |= 1<<bit;
				}
			}
			dv.setUint8(byte, output);
			byte += 1;
		break;
	}
    }
	for (i=0; i<byte; i++) {
        packet.data[i] = asBytes[i];
    }
}
