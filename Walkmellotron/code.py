# SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
import adafruit_mcp4728
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn

i2c = busio.I2C(board.SCL1, board.SDA1)  # qt py rp2040 amirite
mcp4728 = adafruit_mcp4728.MCP4728(i2c)

FULL_VREF_RAW_VALUE = 4095

mcp4728.channel_a.raw_value = FULL_VREF_RAW_VALUE
mcp4728.channel_a.vref = adafruit_mcp4728.Vref.INTERNAL
mcp4728.channel_a.gain = 2

time.sleep(1)  # settle
volts_per_note = 0.0833  # 1/12th V for 1V/Oct

def midi_to_mv(note):
    notemv = 1000 * (note * volts_per_note)
    return int(notemv)


midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)


while True:
    msg = midi.receive()
    if msg is not None:
        if isinstance(msg, NoteOn):
            string_msg = 'NoteOn'
            #  get note number
            string_val = str(msg.note)
            # print("\nnote:",string_val)
            if msg.note < 32:
                mv = midi_to_mv(msg.note)
                # print(mv*0.001, "V")
                mcp4728.channel_a.raw_value = (mv)
