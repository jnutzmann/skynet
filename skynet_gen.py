#!/usr/bin/env python3

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

import argparse
import yaml
import sys
import json
import os

c_types = {
    'uint8_t': 1,
    'int8_t': 1,
    'uint16_t': 2,
    'int16_t': 2,
    'uint32_t': 4,
    'int32_t': 4,
    # TODO: not supporting bitfields for now.  Should add back later.
    # 'bitfield': 1,
    'float': 4
}


class TermColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SkyNetBoard:

    def __init__(self, defs):

        name = defs.get('name')

        if name is None or name is "":
            raise Exception('Packet name is a required field.')

        self.name = name
        self.description = defs.get('description')
        self.listen = []

        for board in defs.get('listen'):
            name = board['board']
            for p in board['packets']:
                self.listen.append((name, p))

        self.packets = {}

        for segment in defs.get('packets'):
            address = segment['segment']
            for packet in segment['packets']:
                p = SkyNetPacket(packet, address, self.name)
                if p.name in self.packets:
                    raise Exception('Duplicate packet name: %s for board %s' % (p.name, self.name))
                self.packets[p.name] = p
                address += 1

        self.chunks = {}
        if 'chunks' in defs:
            for segment in defs.get('chunks'):
                address = segment['segment']
                for chunk in segment['chunks']:
                    c = SkyNetChunk(chunk, address, self.name)
                    if c.name in self.chunks:
                        raise Exception('Duplicate chunk name: %s for board %s' % (c.name, self.name))
                    self.chunks[c.name] = c
                    address += 1


class SkyNetPacket:

    def __init__(self, packet, address, board):

        name = packet.get('name')

        if name is None or name is "":
            raise Exception('Packet name is a required field.')

        self.name = name

        if address < 0 or address >= pow(2, 11):
            raise Exception('Address must be between 0x%x and 0x%x, not ' % (0, pow(2, 11)) + address)

        self.address = address
        self.description = packet.get('description')
        self.board = board
        self.endian = packet.get('endian')
        self.data = []

        for field in packet.get('data'):
            d = SkyNetData(
                field.get('name'),
                field.get('description'),
                field.get('type'),
                field.get('unit'),
                field.get('scale'),
                field.get('decimals'))
            self.data.append(d)

    def get_parameters(self):
        params = []
        for d in self.data:
            params.append(d.get_parameter())
        return ", ".join(params)

    def get_arguments(self):

        byte_num = 0
        arguments = []

        for field in self.data:
            bytes = []
            # TODO: endian stuff
            if field.type == "float":
                for offset in range(0, c_types[field.type]):
                    bytes.append('.b[' + str(offset) + ']=data[' + str(offset + byte_num) + ']')
                arguments.append('((SkynetDataUnion_t){' + ', '.join(bytes) + ' }).f')
            else:
                for offset in range(0, c_types[field.type]):
                    bytes.append('(data[' + str(offset + byte_num) + ']<<' + str(offset*8) + ')')
                arguments.append('(' + field.type + ')(' + '|'.join(bytes) + ')')

            byte_num += c_types[field.type]

        return ', '.join(arguments)

    def data_length(self):
        length = 0
        for field in self.data:
            length += c_types[field.type]
        return length

    def get_data_copy(self):
        dlc = 0
        txt = ""

        for field in self.data:
            for i in range(0, c_types[field.type]):
                if field.type == "float":
                    txt += '    p.data[' + str(dlc) + '] = ((SkynetDataUnion_t){.f=' + field.name + '}).b[' + str(i) + '];\n'
                else:
                    txt += '    p.data[' +str(dlc) + '] = ' + field.name + '>>' + str(i*8) + ';\n'
                dlc += 1
        return txt


class SkyNetChunk:

    def __init__(self, chunk, address, board):

        name = chunk.get('name')

        if name is None or name is "":
            raise Exception('Packet name is a required field.')

        self.name = name

        if address < 0 or address >= pow(2, 11):
            raise Exception('Address must be between 0x%x and 0x%x, not ' % (0, pow(2, 11)) + address)

        self.address = address
        self.description = chunk.get('description')
        self.size = chunk.get('size')
        self.board = board


class SkyNetData:

    def __init__(self, name, description, _type, unit, scale, decimals):

        if name is None or name is "":
            raise Exception('Data name is a required field.')

        self.name = name
        self.description = description
        self.unit = unit
        self.scale = scale
        self.decimals = decimals

        if _type not in c_types:
            raise Exception('Unknown data type: %s' % _type)

        self.type = _type

    def get_parameter(self):
        return "%s %s" % (self.type, self.name)


class SkyNetDefinition:

    def __init__(self):
        self.boards = {}

    def load_file(self, path):

        with open(path, 'r') as f:
            defs = yaml.load(f)

        b = SkyNetBoard(defs)
        if b.name in self.boards:
            raise Exception('Duplication definitions for board: %s given.' % b.name)
        self.boards[b.name] = b

    def validate(self):

        packet_list = {}

        for board_name in self.boards:
            board = self.boards[board_name]
            for packet_name in board.packets:
                packet = board.packets[packet_name]

                if packet.address in packet_list:
                    raise Exception('Packet address collision. %s_%s and %s_%s for address: %i' %
                                    (packet.board, packet.name, packet_list[packet.address].board,
                                     packet_list[packet.address].name, packet.address))

                packet_list[packet.address] = packet

            for chunk_name in board.chunks:
                    chunk = board.chunks[chunk_name]

                    if chunk.address in packet_list:
                        raise Exception('Chunk address collision. %s_%s and %s_%s for address: %i' %
                                        (chunk.board, chunk.name, packet_list[chunk.address].board,
                                         packet_list[chunk.address].name, chunk.address))

                    packet_list[chunk.address] = chunk

    def generate_deorbit_c(self, filename, board):

        # TODO: add support for receiving chunks.

        txt = """// AUTOGENERATED FILE: DO NOT EDIT MANUALLY

#include "deorbit.h"
#include "stdbool.h"
#include "stdint.h"

typedef union {
    uint8_t b[4];
    uint32_t i;
    float f;
} SkynetDataUnion_t;


// Application must define all of these handlers
"""
        for p in self.boards[board].listen:
            board = p[0]
            name = p[1]

            packet = self.boards[board].packets[name]

            txt += "void deorbit_%s_%s( %s );\n" % (packet.board, packet.name, packet.get_parameters())

        txt += """

static void deorbit_packet( uint16_t addr, uint8_t len, bool rtr, uint8_t* data );

inline void deorbit_packet_can( CanRxMsg* p )
{
    deorbit_packet( p->StdId, p->DLC, p->RTR, p->Data );
}

inline void deorbit_packet_serial( SkynetSerialPacket_t *p )
{
    deorbit_packet( p->address, p->length, p->request_to_receive, p->data );
}

static void deorbit_packet( uint16_t addr, uint8_t len, bool rtr, uint8_t* data )
{
    switch ( addr )
    {
"""
        for p in self.boards[board].listen:
            board = p[0]
            name = p[1]

            packet = self.boards[board].packets[name]
            txt += "        case 0x%x:\n" % packet.address
            txt += "            deorbit_%s_%s( %s );\n" % (packet.board, packet.name, packet.get_arguments())
            txt += "            break;\n"
        txt += """
    }
}
"""
        with open(filename, 'w') as f:
            f.write(txt)

    def generate_deorbit_h(self, filename):
        txt = """// AUTOGENERATED FILE: DO NOT EDIT MANUALLY

#ifndef DEORBIT_H
#define DEORBIT_H

#include "orbit.h"
#include "stm32f4xx_can.h"  // TOOD: this should not need the std periph

void deorbit_packet_can( CanRxMsg* p );
void deorbit_packet_serial( SkynetSerialPacket_t *p );

#endif // DEORBIT_H
"""
        with open(filename, 'w') as f:
            f.write(txt)

    def generate_orbit_c(self, filename):

        packet_list = {}

        for board_name in self.boards:
            board = self.boards[board_name]
            for packet_name in board.packets:
                packet = board.packets[packet_name]
                packet_list[packet.address] = packet

        txt = """// AUTOGENERATED FILE: DO NOT EDIT MANUALLY

#include "FreeRTOS.h"
#include "orbit.h"
#include "string.h"
#include "task.h"
#include "diagnostics.h"

#define DEBUG_STDIO_PACKET_TIMOUT_MS    ( 50 )

typedef union {
    uint8_t b[4];
    uint32_t i;
    float f;
} SkynetDataUnion_t;


static void skynet_stdio_task ( void * pvParameters );


static SkynetSerialSendFxn send_serial_fxn = NULL;
static SkynetCanSendFxn send_can_fxn = NULL;

static xTaskHandle skynet_stdio_task_handle;

static portTickType xLastPacketSent = 0;

static uint8_t pending_buffer[MAX_SKYNET_SERIAL_DATA_SIZE];
static uint8_t bytes_waiting = 0;
static bool send_in_progress = false;

static bool stdio_serial_only;
static bool skynet_stdio_enabled = false;
static uint8_t max_packet_size = MAX_SKYNET_SERIAL_DATA_SIZE;

static uint16_t stdio_tx_id;


void orbit_init(SkynetSerialSendFxn send_serial, SkynetCanSendFxn send_can)
{
    send_can_fxn = send_can;
    send_serial_fxn = send_serial;
}

void skynet_stdio_init( bool serial_only, uint16_t tx_id )
{
    stdio_serial_only = serial_only;
    xTaskCreate(skynet_stdio_task, "SKSTDIO", 1024, NULL, 2, &skynet_stdio_task_handle);
    skynet_stdio_enabled = true;
    stdio_tx_id = tx_id;
    max_packet_size = serial_only ? MAX_SKYNET_SERIAL_DATA_SIZE : 8;
    setbuf(stdout, NULL);  // make printf flush ASAP
}

void skynet_stdio_deinit( void )
{
    skynet_stdio_enabled = false;
}

static void send_buffer( void )
{
    SkynetSerialPacket_t p;

    p.address = stdio_tx_id;
    p.request_to_receive = false;
    p.length = bytes_waiting;
    memcpy(p.data, pending_buffer, bytes_waiting);
    send_serial_fxn(&p);

    if (!stdio_serial_only)
    {
        CanTxMsg m;
        m.IDE = 0;
        m.RTR = 0;
        m.StdId = p.address;
        m.DLC = p.length;
        memcpy(m.Data, p.data, p.length);

        send_can_fxn(&m);
    }

    bytes_waiting = 0;
}

// NOTE: this is definitely not thread safe.  Is printf?
void skynet_stdio_send(const uint8_t *buf, size_t len)
{
    if (skynet_stdio_enabled == DISABLE) return;
    send_in_progress = true;

    for ( ; len > 0; len--)
    {
        if ( bytes_waiting < max_packet_size )
        {
            pending_buffer[bytes_waiting++] = *(buf++);
        }

        if (bytes_waiting == max_packet_size)
        {
            // Use the ISR method to be safe.
            // TODO: does this have any side-effects?
            send_buffer();
            xLastPacketSent = xTaskGetTickCountFromISR();
        }
    }

    send_in_progress = false;
}

size_t _write(int handle, const uint8_t *buf, size_t len)
{
    if ((handle == -1) || (buf == NULL))
    {
        return 0;
    }

    if (handle != 1 && handle != 2)
    {
        return -1;
    }

    skynet_stdio_send(buf,len);

    return len;
}

void skynet_stdio_task ( void * pvParameters )
{
    int32_t timeRemainingUntilTimeout = 0;

    while(1)
    {
        timeRemainingUntilTimeout = DEBUG_STDIO_PACKET_TIMOUT_MS - (xTaskGetTickCount() - xLastPacketSent);

        if (timeRemainingUntilTimeout > 0)
        {
            vTaskDelay(timeRemainingUntilTimeout);
        }

        // If we have data to send, send it.
        if (bytes_waiting > 0)
        {
            if (!send_in_progress) send_buffer();
        }

        xLastPacketSent = xTaskGetTickCount();

        vTaskDelay(DEBUG_STDIO_PACKET_TIMOUT_MS);
    }
}

"""
        for p in sorted(packet_list.keys()):
            packet = packet_list[p]

            if type(packet) == SkyNetPacket:

                txt += """
void orbit_%s_%s( %s, bool serial_only )
{
    SkynetSerialPacket_t p;

    p.address = 0x%x;
    p.request_to_receive = false;
    p.length = %i;

%s

    send_serial_fxn(&p);

    if (!serial_only)
    {
        CanTxMsg m;
        m.IDE = 0;
        m.RTR = 0;
        m.StdId = p.address;
        m.DLC = p.length;
        memcpy(m.Data, p.data, p.length);

        send_can_fxn(&m);
    }

}
""" % (packet.board, packet.name, packet.get_parameters(), packet.address, packet.data_length(), packet.get_data_copy())

        # TODO: add support for chunks.




    def generate_orbit_h(self, filename):

        packet_list = {}

        for board_name in self.boards:
            board = self.boards[board_name]
            for packet_name in board.packets:
                packet = board.packets[packet_name]
                packet_list[packet.address] = packet

        txt = """// AUTOGENERATED FILE: DO NOT EDIT MANUALLY

#ifndef ORBIT_H
#define ORBIT_H

#include "stdbool.h"
#include "stdint.h"
#include "stdio.h"
#include "stm32f4xx_can.h"  // TOOD: this should not need the std periph

#define MAX_SKYNET_SERIAL_DATA_SIZE (15)

typedef struct {
    uint16_t address;
    uint16_t length;
    bool request_to_receive;
    uint8_t data[MAX_SKYNET_SERIAL_DATA_SIZE];
    uint32_t unix_timestamp;                      // optional, not used by skynet
} SkynetSerialPacket_t;

typedef void (*SkynetSerialSendFxn)(SkynetSerialPacket_t * packet);
typedef void (*SkynetCanSendFxn)(CanTxMsg* packet);

void skynet_stdio_init( bool serial_only, uint16_t tx_id );
void skynet_stdio_deinit( void );
void skynet_stdio_send( const uint8_t *buf, size_t len );

void orbit_init(SkynetSerialSendFxn send_serial, SkynetCanSendFxn send_can);

"""
        for p in sorted(packet_list.keys()):
            packet = packet_list[p]
            txt += "void orbit_%s_%s( %s, bool serial_only );\n" % (packet.board, packet.name, packet.get_parameters())

        txt += """
#endif // ORBIT_H
"""
        with open(filename, 'w') as f:
            f.write(txt)

    def generate_packet_list(self):

        packet_list = {}
        out = []

        for board_name in self.boards:
            board = self.boards[board_name]
            for packet_name in board.packets:
                packet = board.packets[packet_name]
                packet_list[packet.address] = packet

        for p in sorted(packet_list.keys()):
            packet = packet_list[p]
            j = {
                "name": packet.name,
                "board": packet.board,
                "description": packet.description,
                "endian": packet.endian,
                "address": packet.address,
                "data": []
            }

            for field in packet.data:
                j["data"].append({
                    "name": field.name,
                    "description": field.description,
                    "type": field.type,
                    "unit": field.unit,
                    "scale": field.scale,
                    "decimals": field.decimals
                })
            out.append(j)

        return out

    def generate_js_packet_list(self, filename):
        with open(filename, 'w') as f:
            f.write("var packets = " + json.dumps(self.generate_packet_list()) + ";")

    def generate_json_packet_list(self, filename):
        with open(filename, 'w') as f:
            f.write(json.dumps(self.generate_packet_list(), sort_keys=True, indent=4, separators=(',', ': ')))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--board")
    p.add_argument("--file", nargs="*", action="append")
    p.add_argument("--dest", default="")

    args = p.parse_args()

    files = []

    for fl in args.file:
        for f in fl:
            files.append(f)

    try:
        s = SkyNetDefinition()
        for f in files:
            print("Loading file %s..." % f, end="")
            s.load_file(f)
            print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)
    except Exception as e:
        print (TermColors.FAIL, "[FAIL]\nError parsing file: ", str(e), TermColors.ENDC)
        sys.exit(1)

    try:
        print("Validating SkyNet...", end="")
        s.validate()
        print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)
    except Exception as e:
        print (TermColors.FAIL, "[FAIL]\n", str(e), TermColors.ENDC)
        sys.exit(1)

    f = args.dest + "deorbit.c"
    print("Generating %s ..." % f, end="")
    s.generate_deorbit_c(f, args.board)
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)

    f = args.dest + "deorbit.h"
    print("Generating %s ..." % f, end="")
    s.generate_deorbit_h(f)
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)

    f = args.dest + "orbit.c"
    print("Generating %s ..." % f, end="")
    s.generate_orbit_c(f)
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)

    f = args.dest + "orbit.h"
    print("Generating %s ..." % f, end="")
    s.generate_orbit_h(f)
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)

    f = "%s/static/packets.js" % os.path.dirname(__file__)
    print("Generating %s ..." % f, end="")
    s.generate_js_packet_list(f)
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)

    f = "%s/static/packets.json" % os.path.dirname(__file__)
    print("Generating %s ..." % f, end="")
    s.generate_json_packet_list(f)
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)
