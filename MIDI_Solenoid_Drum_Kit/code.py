# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn

#  pins for the solenoid output signals
noid_pins = [board.D5, board.D6, board.D9, board.D10]

#  array for the solenoids
noids = []

#  setup for the solenoid pins to be outputs
for pin in noid_pins:
    noid = digitalio.DigitalInOut(pin)
    noid.direction = digitalio.Direction.OUTPUT
    noids.append(noid)

#  MIDI note array
notes = [60, 61, 62, 63]

#  MIDI in setup
midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], in_channel=0)

#  delay for solenoids
speed = 0.03
retract = 0

while True:

    #  msg holds MIDI messages
    msg = midi.receive()

    for i in range(4):
        #  states for solenoid on/off
        noid_output = noids[i]

        #  states for MIDI note recieved
        notes_played = notes[i]

        #  if NoteOn msg comes in and the MIDI note # matches with predefined notes:
        if isinstance(msg, NoteOn) and msg.note is notes_played:
            print(time.monotonic(), msg.note)

            #  solenoid is triggered
            noid_output.value = True
            #  quick delay
            retract = time.monotonic()

        #  retracts solenoid using time.monotonic() to avoid delays between notes activating
        if (retract + speed) < time.monotonic():
            noid_output.value = False
