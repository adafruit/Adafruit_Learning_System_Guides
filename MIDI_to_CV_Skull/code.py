# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import simpleio
import adafruit_mcp4725
import usb_midi
import adafruit_midi
from digitalio import DigitalInOut, Direction
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from volts import volts

#  midi channel setup
midi_in_channel = 1
midi_out_channel = 1

#  USB midi setup
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

# gate output pin
gate = DigitalInOut(board.A1)
gate.direction = Direction.OUTPUT

#  i2c setup
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
#  dac setup over i2c
dac = adafruit_mcp4725.MCP4725(i2c)

#  dac raw value (12 bit)
dac.raw_value = 4095

#  array for midi note numbers
midi_notes = []
#  array for 12 bit 1v/oct values
pitches = []

#  function to map 1v/oct voltages to 12 bit values
#  these values are added to the pitches[] array
def map_volts(n, volt, vref, bits):
    n = simpleio.map_range(volt, 0, vref, 0, bits)
    pitches.append(n)

#  brings values from volts.py into individual arrays
for v in volts:
    #  map_volts function to map 1v/oct values to 12 bit
    #  and append to pitches[]
    map_volts(v['label'], v['1vOct'], 5, 4095)
    #  append midi note numbers to midi_notes[] array
    midi_notes.append(v['midi'])

while True:
    #  read incoming midi messages
    msg = midi.receive()
    #  if a midi msg comes in...
    if msg is not None:
        #  if it's noteoff...
        if isinstance(msg, NoteOff):
            #  send 0 volts on dac
            dac.raw_value = 0
            #  turn off gate pin
            gate.value = False
        #  if it's noteon...
        if isinstance(msg, NoteOn):
            #  compare incoming note number to midi_notes[]
            z = midi_notes.index(msg.note)
            #  limit note range to defined notes in volts.py
            if msg.note < 36:
                msg.note = 36
            if msg.note > 96:
                msg.note = 96
            #  send corresponding 1v/oct value
            dac.raw_value = int(pitches[z])
            #  turn on gate pin
            gate.value = True
