#!/usr/bin/env python3
import struct, zlib, sys
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t+d)&0xffffffff)
sig=b"\x89PNG\r\n\x1a\n"
ihdr=chunk(b'IHDR', struct.pack(">IIBBBBB",1,1,8,2,0,0,0))
idat=chunk(b'IDAT', zlib.compress(b'\x00\x00\x00'))
iend=chunk(b'IEND', b'')
sys.stdout.buffer.write(sig+ihdr+idat+iend)
