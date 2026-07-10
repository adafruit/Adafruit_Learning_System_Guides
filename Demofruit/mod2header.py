#!/usr/bin/env python3
"""Convert a ProTracker .mod file to a C header for the Fruit Jam demos.

Usage: python3 mod2header.py song.mod [output.h]

Produces a MOD_DATA byte array. pocketmod plays up to 32 channels, so
4-channel and multichannel MODs both work; only the FLT8 variant is
unsupported by the player.
"""
import sys
import os

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.h'
data = open(src, 'rb').read()

# -- Detect channel count from the 4-byte tag at offset 1080 -----------------
# Recognized ProTracker / clone tags:
#   M.K. M!K! M&K! FLT4 4CHN  -> 4 channels
#   xCHN (e.g. 6CHN, 8CHN)    -> x channels  (single digit)
#   xxCH (e.g. 10CH, 32CH)    -> xx channels (two digits)
#   FLT8                      -> 8 channels, but NOT supported by pocketmod
tag = data[1080:1084]
channels = None
supported = True

if tag in (b'M.K.', b'M!K!', b'M&K!', b'FLT4', b'4CHN'):
    channels = 4
elif tag == b'FLT8':
    channels = 8
    supported = False           # pocketmod explicitly cannot parse FLT8
elif tag[1:4] == b'CHN' and tag[0:1].isdigit():
    channels = int(tag[0:1])
elif tag[2:4] == b'CH' and tag[0:2].isdigit():
    channels = int(tag[0:2])

if channels is None:
    print(f"warning: unrecognized format tag {tag!r} -- this may not be a "
          f"ProTracker MOD; pocketmod may fail to load it")
elif not supported:
    print(f"warning: {channels}-channel FLT8 module -- pocketmod does NOT "
          f"support FLT8 and will fail to load this file; try re-saving as "
          f"a standard {channels}CHN module in a tracker")
else:
    print(f"detected {channels}-channel MOD (tag {tag.decode('latin1')}) -- OK")

# -- Emit the C header --------------------------------------------------------
with open(dst, 'w') as out:
    out.write(f'// {os.path.basename(dst)} -- generated from '
              f'{os.path.basename(src)} ({len(data)} bytes)\n#pragma once\n\n')
    out.write(f'static const unsigned char MOD_DATA[{len(data)}] = {{\n')
    for i in range(0, len(data), 16):
        out.write('  ' + ', '.join(f'0x{b:02X}' for b in data[i:i+16]) + ',\n')
    out.write('};\n')
print(f"{dst}: {len(data)} bytes")
