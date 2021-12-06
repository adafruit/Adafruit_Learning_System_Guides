# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
from digitalio import DigitalInOut, Direction, Pull
import neopixel
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff

#  USB MIDI setup
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

#  NeoPixel setup
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.02, auto_write=False)

#  setup for digital inputs
inputs = []
cpx_pins = [board.A1, board.A2, board.A3, board.A4]

for pin in cpx_pins:
    cpx_pin = DigitalInOut(pin)
    cpx_pin.direction = Direction.INPUT
    cpx_pin.pull = Pull.UP
    inputs.append(cpx_pin)

#  NeoPixel colors
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)

#  debounce states for inputs
state_A1 = False
state_A2 = False
state_A3 = False
state_A4 = False

#  array of NeoPixel colors
colors = [GREEN, CYAN, BLUE, PURPLE]
#  array of MIDI notes
midi_notes = [60, 64, 67, 72]
#  array of input states
input_states = [state_A1, state_A2, state_A3, state_A4]

while True:

    #  iterate through colors, inputs and MIDI notes
    for i in range(4):
        #  reset the state of the input and send NoteOff msg
        #  after the input is released
        if inputs[i].value and input_states[i]:
            input_states[i] = False
            midi.send(NoteOff(midi_notes[i], 120))

        #  if an input is pressed...
        if not inputs[i].value and not input_states[i]:
            #  change thhe colors of the NeoPixels
            pixels.fill(colors[i])
            pixels.show()
            #  send the NoteOn msg
            midi.send(NoteOn(midi_notes[i], 120))
            #  update input state
            input_states[i] = True
