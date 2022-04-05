# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import usb_midi
import adafruit_midi
import simpleio
from analogio import AnalogIn
from adafruit_midi.control_change import ControlChange

#  midi setup
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

#  potentiometer setup
mod_pot = AnalogIn(board.A0)

#  function to read analog input
def val(pin):
    return pin.value

#  variables for last read value
#  defaults to 0
mod_val2 = 0

while True:

    #  Print out the min/max values from potentiometer to the serial monitor and plotter
    print((mod_pot.value,))
    time.sleep(0.05)

    #  map range of potentiometer input to midi values - update the min/max values below
    mod_val1 = round(simpleio.map_range(val(mod_pot), 0, 65535, 0, 127))

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
