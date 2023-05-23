#!/usr/local/bin/python3

import struct

FILENAME = "Intro.bin"

storyfile = open(FILENAME, "rb")

SNXROM = {}

# check for magic bytes
SNXROM['SNXROM'] = storyfile.read(12).decode('utf-16')
if SNXROM['SNXROM'] != 'SNXROM':
    raise RuntimeError("Didn't find SNXROM magic bytes")

print(SNXROM['SNXROM'], "found")

# read and toss next 28 bytes all 0xFF
storyfile.read(28)
# find 0x400 bytes
if 0x400 != struct.unpack('I', storyfile.read(4))[0]:
    raise RuntimeError("Didn't find 0x400 magic bytes")

SNXROM['assetTableLengthWords'] = struct.unpack('I', storyfile.read(4))[0]
print("Asset table length (words):", SNXROM['assetTableLengthWords'], "& bytes:", SNXROM['assetTableLengthWords'] * 4)

# read and toss next 464 bytes all 0xFF
storyfile.read(464)

# NOTE: the pointers are in byte offsets not words!
print("Looking for asset table pointers at", hex(storyfile.tell()))
assetTablePointers = [0] * SNXROM['assetTableLengthWords']
for i in range(SNXROM['assetTableLengthWords']):
    assetTablePointers[i] = struct.unpack('I', storyfile.read(4))[0]
print("Asset table pointers:", [hex(i) for i in assetTablePointers])

SNXROM['audioOffset'] = assetTablePointers[-1]

# verify audio offset
print("Looking for audio at", hex(SNXROM['audioOffset']))
storyfile.seek(SNXROM['audioOffset'])
if "AU" != storyfile.read(2).decode('utf-8'):
    raise RuntimeError("Didn't find AU at beginning of audio")
print("Found beginning of audio")
"""
SNXROM['metaOffset'] = struct.unpack('I', storyfile.read(4))[0]
SNXROM['leftEyeOffset'] = struct.unpack('I', storyfile.read(4))[0]
SNXROM['rightEyeOffset'] = struct.unpack('I', storyfile.read(4))[0]


print("Metadata offset: %d bytes, address 0x%0X" % (SNXROM['metaOffset'], SNXROM['metaOffset']))
print("Left Eye offset: %d bytes, address 0x%0X" % (SNXROM['leftEyeOffset'], SNXROM['leftEyeOffset']))
print("Right Eye offset: %d bytes, address 0x%0X" % (SNXROM['rightEyeOffset'], SNXROM['rightEyeOffset']))
print("Audio data offset: %d bytes, address 0x%0X" % (SNXROM['audioOffset'], SNXROM['audioOffset']))

print(storyfile.tell())

# Go to the metadata table
storyfile.seek(SNXROM['metaOffset'])

if 0x0000 != struct.unpack('h', storyfile.read(2))[0]:
    raise RuntimeError("Didn't find 0x0000 magic bytes")
SNXROM['storyId'] = struct.unpack('h', storyfile.read(2))[0]
SNXROM['numberOfEyeAnimations'] = struct.unpack('h', storyfile.read(2))[0]
SNXROM['numberOfEyeBitmaps'] = struct.unpack('h', storyfile.read(2))[0]
SNXROM['numberOfVideoSequences'] = struct.unpack('h', storyfile.read(2))[0]
SNXROM['numberOfAudioBlocks'] = struct.unpack('h', storyfile.read(2))[0]
print("Story ID: ", SNXROM['storyId'])
print("Eye animations:", SNXROM['numberOfEyeAnimations'])
print("Eye bitmaps:", SNXROM['numberOfEyeBitmaps'])
print("Video seqs:", SNXROM['numberOfVideoSequences'])
print("Audio blocks:", SNXROM['numberOfAudioBlocks'])

SNXROM['ROMfilesize'] = struct.unpack('i', storyfile.read(4))[0]
print(SNXROM['ROMfilesize'])
"""
