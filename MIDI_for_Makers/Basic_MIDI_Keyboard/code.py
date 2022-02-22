# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import digitalio
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff

#  midi setup
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

#  midi note numbers
midi_notes = [60, 64, 67, 72]

#  digital pins for the buttons
key_pins = [board.D5, board.D6, board.D9, board.D10]

#  array for buttons
keys = []

#  setup buttons as inputs
for key in key_pins:
    key_pin = digitalio.DigitalInOut(key)
    key_pin.direction = digitalio.Direction.INPUT
    key_pin.pull = digitalio.Pull.UP
    keys.append(key_pin)

#  states for buttons
key0_pressed = False
key1_pressed = False
key2_pressed = False
key3_pressed = False

#  array for button states
key_states = [key0_pressed, key1_pressed, key2_pressed, key3_pressed]

while True:

    #  iterate through 4 buttons
    for i in range(4):
        inputs = keys[i]
        #  if button is pressed...
        if not inputs.value and key_states[i] is False:
            #  update button state
            key_states[i] = True
            #  send NoteOn for corresponding MIDI note
            midi.send(NoteOn(midi_notes[i], 120))

        #  if the button is released...
        if inputs.value and key_states[i] is True:
            #  send NoteOff for corresponding MIDI note
            midi.send(NoteOff(midi_notes[i], 120))
            key_states[i] = False
