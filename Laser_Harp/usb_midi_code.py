# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import simpleio
import adafruit_vl53l4cd
import adafruit_tca9548a
import usb_midi
import adafruit_midi
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.control_change import ControlChange

# Create I2C bus as normal
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# Create the TCA9548A object and give it the I2C bus
tca = adafruit_tca9548a.TCA9548A(i2c)

#  setup time of flight sensors to use TCA9548A inputs
tof_0 = adafruit_vl53l4cd.VL53L4CD(tca[0])
tof_1 = adafruit_vl53l4cd.VL53L4CD(tca[1])
tof_2 = adafruit_vl53l4cd.VL53L4CD(tca[2])
tof_3 = adafruit_vl53l4cd.VL53L4CD(tca[3])
tof_4 = adafruit_vl53l4cd.VL53L4CD(tca[4])
tof_5 = adafruit_vl53l4cd.VL53L4CD(tca[5])
tof_6 = adafruit_vl53l4cd.VL53L4CD(tca[6])
tof_7 = adafruit_vl53l4cd.VL53L4CD(tca[7])

#  array of tof sensors
flights = [tof_0, tof_1, tof_2, tof_3, tof_4, tof_5, tof_6, tof_7]

#  setup each tof sensor
for flight in flights:
    flight.inter_measurement = 0
    flight.timing_budget = 50
    flight.start_ranging()

midi_in_channel = 1
midi_out_channel = 1
#  midi setup
#  USB is setup as the input
midi = adafruit_midi.MIDI(
    midi_out=usb_midi.ports[1],
    in_channel=(midi_in_channel - 1),
    out_channel=(midi_out_channel - 1),
    debug=False,
)

#  state of each tof sensor
#  tracks if you have hit the laser range
pluck_0 = False
pluck_1 = False
pluck_2 = False
pluck_3 = False
pluck_4 = False
pluck_5 = False
pluck_6 = False
pluck_7 = False

#  array of tof sensor states
plucks = [pluck_0, pluck_1, pluck_2, pluck_3, pluck_4, pluck_5, pluck_6, pluck_7]

#  height cutoff for tof sensors
#  adjust depending on the height of your ceiling/performance area
flight_height = 150

#  midi notes for each tof sensor
notes = [48, 52, 55, 59, 60, 64, 67, 71]

while True:
    #  iterate through the 8 tof sensors
    for f in range(8):
        while not flights[f].data_ready:
            pass
        #  reset tof sensors
        flights[f].clear_interrupt()
        #  if the reading from a tof is not 0...
        if flights[f].distance != 0.0:
            #  map range of tof sensor distance to midi parameters
            #  modulation
            mod = round(simpleio.map_range(flights[f].distance, 0, 100, 120, 0))
            #  sustain
            sus = round(simpleio.map_range(flights[f].distance, 0, 100, 127, 0))
            #  velocity
            vel = round(simpleio.map_range(flights[f].distance, 0, 150, 120, 0))
            modulation = int(mod)
            sustain = int(sus)
            #  create sustain and modulation CC message
            pedal = ControlChange(71, sustain)
            modWheel = ControlChange(1, modulation)
            #  send the sustain and modulation messages
            midi.send([modWheel, pedal])
            #  if tof registers a height lower than the set max height...
            if int(flights[f].distance) < flight_height and not plucks[f]:
                #  set state tracker
                plucks[f] = True
                #  convert tof distance to a velocity value
                velocity = int(vel)
                #  send midi note with velocity and sustain message
                midi.send([NoteOn(notes[f], velocity), pedal])
            #  if tof registers a height = to or greater than set max height
            #  aka you remove your hand from above the sensor...
            if int(flights[f].distance) > flight_height and plucks[f]:
                #  reset state
                plucks[f] = False
                #  send midi note off
                midi.send(NoteOff(notes[f], velocity))
