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
#print("Asset table pointers:", [hex(i) for i in assetTablePointers])



# Go to the metadata table
SNXROM['metaOffset'] = assetTablePointers[0]
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

##############

SNXROM['audioOffset'] = assetTablePointers[-1]

# verify audio offset
print("Looking for audio at", hex(SNXROM['audioOffset']))
storyfile.seek(SNXROM['audioOffset'])

if "AU" != storyfile.read(2).decode('utf-8'):
    raise RuntimeError("Didn't find AU at beginning of audio")
print("Found beginning of audio")
(samplerate, bitrate, channels, frame_count, file_len, mark_flag, silence_flag, \
 mbf, pcs, rec, header_len) = \
 struct.unpack('<HHHIIHHHHHH', storyfile.read(26))

print("Header Size (16b words):", hex(header_len))

print("Samplerate:", samplerate)
print("Bitrate:", bitrate)
print("Channels:", channels)
print("Frame count:", frame_count)
print("File len (16b words):", file_len)
if (file_len * 2) / 80 != frame_count:
    print("Should be %d frames * 80 bytes per frame = %d total size" % (frame_count, file_len*2))
print("Mark flag:", mark_flag)
print("Silence flag:", silence_flag)
print("Header Size (16b words):", header_len)

#print(storyfile.tell() - SNXROM['audioOffset'])

# toss 0xFFFFFFFF
storyfile.read(4)

table_size = struct.unpack('<H', storyfile.read(2))[0]
#print(table_size * 2)
mark_entries = header_len*2 - (storyfile.tell() - SNXROM['audioOffset']) - 4
print("entries:", mark_entries)

marktable = []
for i in range(mark_entries // 2):
    marktable.append(struct.unpack('<H', storyfile.read(2))[0])
totaltime = 0;
for i in range(len(marktable) // 2):
    totaltime+=marktable[2*i+0]
    print(marktable[2*i+0], marktable[2*i+1])
print("total length of motion mark table (s):", totaltime / 1000.0)

print("Actual audio data starts at", hex(SNXROM['audioOffset'] + header_len*2))
print("and ends at ", hex(SNXROM['audioOffset'] + header_len*2 + file_len*2))
"""



SNXROM['leftEyeOffset'] = struct.unpack('I', storyfile.read(4))[0]
SNXROM['rightEyeOffset'] = struct.unpack('I', storyfile.read(4))[0]


print("Metadata offset: %d bytes, address 0x%0X" % (SNXROM['metaOffset'], SNXROM['metaOffset']))

print("Left Eye offset: %d bytes, address 0x%0X" % (SNXROM['leftEyeOffset'], SNXROM['leftEyeOffset']))
print("Right Eye offset: %d bytes, address 0x%0X" % (SNXROM['rightEyeOffset'], SNXROM['rightEyeOffset']))
print("Audio data offset: %d bytes, address 0x%0X" % (SNXROM['audioOffset'], SNXROM['audioOffset']))

print(storyfile.tell())

"""
