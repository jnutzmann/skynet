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
        self.data = []

        for field in packet.get('data'):
            d = SkyNetData(field.get('name'), field.get('description'), field.get('type'))
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
                arguments.append('((SkylabDataUnion_t){' + ', '.join(bytes) + ' }).f')
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
                    txt += '    p.data[' + str(dlc) + '] = ((SkylabDataUnion_t){.f=' + field.name + '}).b[' + str(i) + '];\n'
                else:
                    txt += '    p.data[' +str(dlc) + '] = ' + field.name + '>>' + str(i*8) + ';\n'
                dlc += 1
        return txt


class SkyNetData:

    def __init__(self, name, description, _type):

        if name is None or name is "":
            raise Exception('Data name is a required field.')

        self.name = name
        self.description = description

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

    def generate_deorbit_c(self, filename, board):
        txt = """// AUTOGENERATED FILE: DO NOT EDIT MANUALLY

#include "deorbit.h"
#include "stdbool.h"
#include "stdint.h"

typedef union {
    uint8_t b[4];
    uint32_t i;
    float f;
} SkylabDataUnion_t;


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

inline void deorbit_packet_serial( SkylabSerialPacket_t *p )
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
#include "stm32f4xx_can.h"

void deorbit_packet_can( CanRxMsg* p );
void deorbit_packet_serial( SkylabSerialPacket_t *p );

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

#include "debug_uart.h"
#include "orbit.h"
#include "stm32f4xx_can.h"
#include "string.h"

typedef union {
    uint8_t b[4];
    uint32_t i;
    float f;
} SkylabDataUnion_t;

static SkylabSerialSendFxn send_serial_fxn = NULL;
static SkylabCanSendFxn send_can_fxn = NULL;

void orbit_init(SkylabSerialSendFxn send_serial, SkylabCanSendFxn send_can)
{
    send_can_fxn = send_can;
    send_serial_fxn = send_serial;
}

"""
        for p in sorted(packet_list.keys()):
            packet = packet_list[p]
            txt += """
void orbit_%s_%s( %s, bool serial_only )
{
    SkylabSerialPacket_t p;

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

        with open(filename, 'w') as f:
            f.write(txt)

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
#include "stm32f4xx_can.h"

#define MAX_SKYLAB_SERIAL_DATA_SIZE (15)

typedef struct {
    uint16_t address;
    uint16_t length;
    bool request_to_receive;
    uint8_t data[MAX_SKYLAB_SERIAL_DATA_SIZE];
} SkylabSerialPacket_t;

typedef void (*SkylabSerialSendFxn)(SkylabSerialPacket_t * packet);
typedef void (*SkylabCanSendFxn)(CanTxMsg* packet);

void orbit_init(SkylabSerialSendFxn send_serial, SkylabCanSendFxn send_can);

"""
        for p in sorted(packet_list.keys()):
            packet = packet_list[p]
            txt += "void orbit_%s_%s( %s, bool serial_only );\n" % (packet.board, packet.name, packet.get_parameters())

        txt += """
#endif // ORBIT_H
"""
        with open(filename, 'w') as f:
            f.write(txt)



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

    print("Generating deorbit.c ...", end="")
    s.generate_deorbit_c(args.dest + "deorbit.c", args.board)
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)
    print("Generating deorbit.h ...", end="")
    s.generate_deorbit_h(args.dest + "deorbit.h")
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)
    print("Generating orbit.h ...", end="")
    s.generate_orbit_h(args.dest + "orbit.h")
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)
    print("Generating orbit.c ...", end="")
    s.generate_orbit_c(args.dest + "orbit.c")
    print (TermColors.OKGREEN, "[SUCCESS]", TermColors.ENDC)

