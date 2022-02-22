# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import adafruit_ble
import touchio
import board
import adafruit_midi
import adafruit_ble_midi
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

#  CLUE cap touch setup
c_touch = touchio.TouchIn(board.D0)
f_touch = touchio.TouchIn(board.D1)
g_touch = touchio.TouchIn(board.D2)

#  array of touch pads
pads = [c_touch, f_touch, g_touch]

#  BLE MIDI setup
midi_service = adafruit_ble_midi.MIDIService()
advertisement = ProvideServicesAdvertisement(midi_service)

ble = adafruit_ble.BLERadio()
if ble.connected:
    for c in ble.connections:
        c.disconnect()

#  midi setup
midi = adafruit_midi.MIDI(midi_out=midi_service, out_channel=0)

print("advertising")
ble.start_advertising(advertisement)

#  MIDI note numbers for C, F and G major triads
c_triad = (60, 64, 67)
f_triad = (65, 69, 72)
g_triad = (67, 71, 74)

#  array of triads
triads = [c_triad, f_triad, g_triad]

#  touch debounce states
c_pressed = False
f_pressed = False
g_pressed = False

#  array of debounce states
triad_states = [c_pressed, f_pressed, g_pressed]

#  beginning triad
active_triad = c_triad
#  variable for triad index
z = 0

while True:
    #  BLE connection
    print("Waiting for connection")
    while not ble.connected:
        pass
    print("Connected")
    time.sleep(1.0)

    #  while BLE is connected...
    while ble.connected:
        #  iterate through the touch inputs
        for i in range(3):
            inputs = pads[i]
            #  if a touch input is detected...
            if inputs.value and triad_states[i] is False:
                #  debounce state activated
                triad_states[i] = True
                #  update triad
                active_triad = triads[i]
                print(active_triad)
            #  after touch input...
            if not inputs.value and triad_states[i] is True:
                #  reset debounce state
                triad_states[i] = False
        #  send triad arpeggios out with half second delay
        midi.send(NoteOn(active_triad[z]))
        time.sleep(0.5)
        midi.send(NoteOff(active_triad[z]))
        time.sleep(0.5)
        #  increase index by 1
        z += 1
        #  reset index at end of triad
        if z > 2:
            z = 0

    #  BLE connection
    print("Disconnected")
    print()
    ble.start_advertising(advertisement)
