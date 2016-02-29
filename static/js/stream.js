/*
Copyright (c) 2015, Jonathan Nutzmann

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
*/

var packetsByAddress = [];
var packetsByName = {};

for (packet in packets)
{
    packetsByAddress[packets[packet].address] = packets[packet];
    packetsByName[packets[packet].board + "_" + packets[packet].name] = packets[packet];
}

function streamPackets(port, callback)
{
	var source = new EventSource("/serial/stream/" + port);

	source.addEventListener('message', function(e) {
	    callback($.parseJSON(e.data));
	});
}

function sendPacket(port, address, rtr, data) {
    $.ajax(
    {
        type: "POST",
        url: "/serial/send/" + port,
        contentType: "application/json",
        data: JSON.stringify({
            address: address,
            rtr: rtr,
            data: data
        })
    });
}

function ascii_2_string(array) 
{
    var result = "";
    for (var i = 0; i < array.length; i++) 
    {
        result += String.fromCharCode(array[i]);
    }

    return result;
}

function decodeSTDIO(packet) 
{
    $("#console_out").val($("#console_out").val() + ascii_2_string(packet.data));
    $('#console_out').scrollTop($('#console_out')[0].scrollHeight);
    console.log(ascii_2_string(packet.data));
    console.log(packet.data);
}

function decodePacket(packet) {

    if (packet.address == 0x790)
    {
        decodeSTDIO(packet);
        return false;
    }


    if (!(packet.address in packetsByAddress)) return false;

    var byte = 0;
    var format = packetsByAddress[packet.address];
    var endian = 'little';
    var littleEndian = (format.endian == 'little');

    packet.name = format.name;
    packet.board = format.board;

	packet.decoded = {};

    var field_data;

    var buffer = new ArrayBuffer(15);
	var asBytes = new Uint8Array(buffer);

    for (var i in packet.data)
    {
        asBytes[i] = packet.data[i];
    }

	var dv = new DataView(buffer);

    for (field_num in format.data)
    {
        switch (format.data[field_num].type)
        {
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
        }

		var fmtdata = format.data[field_num]

		packet.decoded[fmtdata.name] = {}
		packet.decoded[fmtdata.name]['value'] = field_data

		if(fmtdata["scale"] !== null)
		{
			// conversion data is available,  we should convert to std units
			packet.decoded[fmtdata.name]['cvalue'] = (field_data * fmtdata['scale'])
		}
		else
		{
			// otherwise don't convert
			packet.decoded[fmtdata.name]['cvalue'] = field_data
		}

		if(fmtdata["unit"] !== null)
		{
            packet.decoded[fmtdata.name]['unit'] = fmtdata['unit']
		}
		else
		{
			packet.decoded[fmtdata.name]['unit'] = "" //no units
		}

        packet.decoded[fmtdata.name]['decimals'] = fmtdata['decimals']
    }

    return true;
}

function encodePacket(packet)
{
    if (!(packet.address in packetsByAddress)) return;

    var byte = 0;
    var format = packetsByAddress[packet.address];

	var buffer = new ArrayBuffer(15);
	var asBytes = new Uint8Array(buffer);
	var dv = new DataView(buffer, 0);
	var littleEndian = (format.endian == 'little')

    packet.data = [];

    for (field_num in format.data)
    {
        switch (format.data[field_num].type)
        {
            case "uint8_t":
                dv.setUint8(byte, parseInt(packet.decoded[format.data[field_num].name]));
                byte += 1;
            break;
            case "int8_t":
                dv.setInt8(byte, parseInt(packet.decoded[format.data[field_num].name]));
            byte += 1;
            break;
            case "uint16_t":
                dv.setUint16(byte, parseInt(packet.decoded[format.data[field_num].name]), littleEndian);
                byte += 2;
            break;
            case "int16_t":
                dv.setInt16(byte, parseInt(packet.decoded[format.data[field_num].name]), littleEndian);
                byte += 2;
            break;
            case "uint32_t":
                dv.setUint32(byte, parseInt(packet.decoded[format.data[field_num].name]), littleEndian);
                byte += 4;
            break;
            case "int32_t":
                dv.setInt32(byte, parseInt(packet.decoded[format.data[field_num].name]), littleEndian);
                byte += 4;
            break;
            case "float":
                dv.setFloat32(byte, parseFloat(packet.decoded[format.data[field_num].name]), littleEndian);
                byte += 4;
            break;
        }
    }

	for (i=0; i<byte; i++)
	{
        packet.data[i] = asBytes[i];
    }
}
