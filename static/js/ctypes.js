function bit(byte, pos)
{
    return byte & (1<<pos);
}

function uint8(byte)
{
    return byte;
}

function int8(byte)
{
    if (byte > 127)
    {
	    return byte - 256;
    }
    else
    {
	    return byte;
    }
}

function uint16(msb, lsb)
{
    return msb * 256 + lsb;
}

function int16(msb, lsb)
{
    var out = msb * 256 + lsb;

    if (out > 32767)
    {
	    out = out - 65536;
    }
    return out;
}

function uint32(b3,b2,b1,b0)
{
    return b3*16777216+b2*65536+b1*256+b0;
}

function int32(b3,b2,b1,b0)
{
    var out = uint32(b3,b2,b1,b0);

	if (out > 2147483648){
		out = out-4294967296;
	}

	return out;
}

function uint8p(packet, index)
{
    return uint8(packet.data[index]);
}

function uint16p(packet, index)
{
    return uint16(packet.data[index],packet.data[index+1]);
}

function uint16p_le(packet, index)
{
    return uint16(packet.data[index+1],packet.data[index]);
}

function int16p(packet, index)
{
    return int16(packet.data[index],packet.data[index+1]);
}

function int16p_le(packet, index)
{
    return int16(packet.data[index+1],packet.data[index]);
}

function uint32p(packet, index)
{
    return uint32(packet.data[index],packet.data[index+1],packet.data[index+2],packet.data[index+3]);
}

function uint32p_le(packet, index)
{
    return uint32(packet.data[index+3],packet.data[index+2],packet.data[index+1],packet.data[index]);
}

function int32p(packet, index)
{
    return int32(packet.data[index],packet.data[index+1],packet.data[index+2],packet.data[index+3]);
}

function int32p_le(packet, index)
{
    return int32(packet.data[index+3],packet.data[index+2],packet.data[index+1],packet.data[index]);
}