# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import usb_midi
import adafruit_midi
import simpleio
from analogio import AnalogIn
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend

#  midi setup
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

#  potentiometer setup
mod_pot = AnalogIn(board.A0)
pitchDown_pot = AnalogIn(board.A1)
pitchUp_pot = AnalogIn(board.A2)
sus_pot = AnalogIn(board.A3)

#  function to read analog input
def val(pin):
    return pin.value

#  variables for last read value
#  defaults to 0
#  no pitchbend is 8192
mod_val2 = 0
pitchDown_val2 = 8192
pitchUp_val2 = 8192
sus_val2 = 0

while True:

    #  map range of analog input to midi values
    #  pitchbend range is 0 to 16383 with 8192 centered or no pitchbend
    mod_val1 = round(simpleio.map_range(val(mod_pot), 0, 65535, 0, 127))
    pitchDown_val1 = round(simpleio.map_range(val(pitchDown_pot), 0, 65535, 0, 8192))
    pitchUp_val1 = round(simpleio.map_range(val(pitchUp_pot), 0, 65535, 8192, 16383))
    sus_val1 = round(simpleio.map_range(val(sus_pot), 0, 65535, 0, 127))

    #  if modulation value is updated...
    if abs(mod_val1 - mod_val2) > 2:
        #  update mod_val2
        mod_val2 = mod_val1
        #  create integer
        modulation = int(mod_val2)
        #  create CC message
        modWheel = ControlChange(1, modulation)
        #  send CC message
        midi.send(modWheel)

    #  pitchbend down value is updated...
    if abs(pitchDown_val1 - pitchDown_val2) > 75:
        #  update pitchDown_val2
        pitchDown_val2 = pitchDown_val1
        #  create PitchBend message
        pitchDown = PitchBend(int(pitchDown_val2))
        #  send PitchBend message
        midi.send(pitchDown)

    #  pitchbend up value is updated...
    if abs(pitchUp_val1 - pitchUp_val2) > 75:
        #  updated pitchUp_val2
        pitchUp_val2 = pitchUp_val1
        #  create PitchBend message
        pitchUp = PitchBend(int(pitchUp_val2))
        #  send PitchBend message
        midi.send(pitchUp)

    #  sustain value is updated...
    if abs(sus_val1 - sus_val2) > 2:
        #  update sus_val2
        sus_val2 = sus_val1
        #  create integer
        sustain = int(sus_val2)
        #  create CC message
        sustainPedal = ControlChange(64, sustain)
        #  send CC message
        midi.send(sustainPedal)
