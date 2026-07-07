#!/usr/bin/env python3
import struct
import sys
import zlib


def chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


sig = b"\x89PNG\r\n\x1a\n"
ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 2, 0, 0, 0))
idat = chunk(b"IDAT", zlib.compress(b"\x00" + (b"\x11\x22\x33" * 16)))
iend = chunk(b"IEND", b"")
sys.stdout.buffer.write(sig + ihdr + idat + iend)
