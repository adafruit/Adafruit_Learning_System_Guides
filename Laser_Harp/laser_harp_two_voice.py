# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board
import busio
import simpleio
import adafruit_vl53l4cd
import adafruit_midi
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.program_change import ProgramChange
#  uncomment if using volume CC message in the loop
#  from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend
import adafruit_tca9548a

# Create I2C bus as normal
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# Create the TCA9548A object and give it the I2C bus
tca = adafruit_tca9548a.TCA9548A(i2c)

tof_0 = adafruit_vl53l4cd.VL53L4CD(tca[0])
tof_1 = adafruit_vl53l4cd.VL53L4CD(tca[1])
tof_2 = adafruit_vl53l4cd.VL53L4CD(tca[2])
tof_3 = adafruit_vl53l4cd.VL53L4CD(tca[3])
tof_4 = adafruit_vl53l4cd.VL53L4CD(tca[4])
tof_5 = adafruit_vl53l4cd.VL53L4CD(tca[5])
tof_6 = adafruit_vl53l4cd.VL53L4CD(tca[6])
tof_7 = adafruit_vl53l4cd.VL53L4CD(tca[7])

flights = [tof_0, tof_1, tof_2, tof_3, tof_4, tof_5, tof_6, tof_7]

for flight in flights:
    flight.inter_measurement = 0
    flight.timing_budget = 50
    flight.start_ranging()

#  midi uart setup for music maker featherwing
uart = busio.UART(board.TX, board.RX, baudrate=31250)

midi_in_channel = 1
midi_out_channel = 1
#  midi setup
#  UART is setup as the input
midi = adafruit_midi.MIDI(
    midi_in=uart,
    midi_out=uart,
    in_channel=(midi_in_channel - 1),
    out_channel=(midi_out_channel - 1),
    debug=False,
)

flight_height = 150

pluck_0 = False
pluck_1 = False
pluck_2 = False
pluck_3 = False
pluck_4 = False
pluck_5 = False
pluck_6 = False
pluck_7 = False

plucks = [pluck_0, pluck_1, pluck_2, pluck_3, pluck_4, pluck_5, pluck_6, pluck_7]

low_notes = [28, 32, 35, 36, 40, 43, 47, 48]
high_notes = [52, 55, 59, 60, 64, 67, 71, 72]

heights = [0, 0, 0, 0, 0, 0, 0]

bend_sense = 5
vel = 120

while True:
    for f in range(8):
        while not flights[f].data_ready:
            pass
        flights[f].clear_interrupt()
        if flights[f].distance != 0.0:
            if int(flights[f].distance) < flight_height:
                if int(flights[f].distance) < 30 and not plucks[f]:
                    bass = ProgramChange(81)
                    vel = round(simpleio.map_range(flights[f].distance, 0, 30, 127, 75))
                    bend_sense = 5
                    velocity = int(vel)
                    #  send midi message
                    midi.send([bass, NoteOn(low_notes[f], velocity)])
                    plucks[f] = True
                    heights[f] = int(flights[f].distance)
                if (int(flights[f].distance) > 40) and not plucks[f]:
                    lead = ProgramChange(54)
                    vel = round(simpleio.map_range(flights[f].distance, 30, flight_height, 127, 75))
                    bend_sense = 10
                    velocity = int(vel)
                    #  send midi message
                    midi.send([lead, NoteOn(high_notes[f], velocity)])
                    plucks[f] = True
                    heights[f] = int(flights[f].distance)
            #  this section affects pitchbend OR volume control_change while you are playing a note
            #  comment/uncomment lines to change effect affected
            if abs(int(flights[f].distance) - heights[f]) > bend_sense and plucks[f]:
                bend_up = round(simpleio.map_range(flights[f].distance, heights[f], flight_height,
                                                                        8192, 16383))
                bend_down = round(simpleio.map_range(flights[f].distance, heights[f], 0,
                                                                          8192, 0))
                '''vol_up = round(simpleio.map_range(flights[f].distance, heights[f], flight_height,
                                                                          velocity, 0))
                vol_down = round(simpleio.map_range(flights[f].distance, heights[f], 0,
                                                                         velocity, 127))'''
                if int(flights[f].distance) > heights[f]:
                    pitchUp = PitchBend(int(bend_up))
                    midi.send(pitchUp)
                    #  volume = ControlChange(7, int(vol_down))
                    #  midi.send(volume)
                    print("bend up!")
                if int(flights[f].distance) < heights[f]:
                    pitchDown = PitchBend(int(bend_down))
                    midi.send(pitchDown)
                    #  volume = ControlChange(7, int(vol_up))
                    #  midi.send(volume)
                    print("bend down!")
            #  send note off message
            if int(flights[f].distance) > flight_height and plucks[f]:
                plucks[f] = False
                midi.send(NoteOff(low_notes[f], velocity))
                midi.send(NoteOff(high_notes[f], velocity))
