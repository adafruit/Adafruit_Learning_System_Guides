# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import busio
import adafruit_midi
import usb_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn

#  uart setup
uart = busio.UART(board.TX, board.RX, baudrate=31250, timeout=0.001)
#  midi channel setup
midi_in_channel = 1
midi_out_channel = 1
#  midi setup
#  UART is setup as the input
#  USB is setup as the output
midi = adafruit_midi.MIDI(
    midi_in=uart,
    midi_out=usb_midi.ports[1],
    in_channel=(midi_in_channel - 1),
    out_channel=(midi_out_channel - 1),
    debug=False,
)

print("MIDI UART In/USB Out")
print("Default output channel:", midi.out_channel + 1)

#  array of message types
messages = (NoteOn, NoteOff, PitchBend, ControlChange)

while True:
    #  receive MIDI input from UART
    msg = midi.receive()

    #  if the input is a recognized message...
    if msg is not None:
        for i in range(0, 3):
            #  iterate through message types
            #  makes it so that you aren't sending any unnecessary messages
            if isinstance(msg, messages[i]):
                #  send the input out via USB
                midi.send(msg)
                print(msg)
