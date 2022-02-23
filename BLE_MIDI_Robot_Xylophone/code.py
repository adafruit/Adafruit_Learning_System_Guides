# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import busio
from adafruit_mcp230xx.mcp23017 import MCP23017
from digitalio import Direction
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
import adafruit_ble_midi

# These import auto-register the message type with the MIDI machinery.
# pylint: disable=unused-import
import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.midi_message import MIDIUnknownEvent
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

#  i2c setup
i2c = busio.I2C(board.SCL, board.SDA)

#  i2c addresses for muxes
mcp1 = MCP23017(i2c, address=0x20)
mcp2 = MCP23017(i2c, address=0x21)

#  1st solenoid array, corresponds with 1st mux
noids0 = []

for pin in range(16):
    noids0.append(mcp1.get_pin(pin))
for n in noids0:
    n.direction = Direction.OUTPUT

#  2nd solenoid array, corresponds with 2nd mux
noids1 = []

for pin in range(16):
    noids1.append(mcp2.get_pin(pin))
for n in noids1:
    n.direction = Direction.OUTPUT

#  MIDI note arrays. notes0 = noids0; notes1 = noids1
notes0 = [55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70]
notes1 = [71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86]

#  setup MIDI BLE service
midi_service = adafruit_ble_midi.MIDIService()
advertisement = ProvideServicesAdvertisement(midi_service)

#  BLE connection setup
ble = adafruit_ble.BLERadio()
if ble.connected:
    for c in ble.connections:
        c.disconnect()

#  MIDI in setup
midi = adafruit_midi.MIDI(midi_in=midi_service, in_channel=0)

#  start BLE advertising
print("advertising")
ble.start_advertising(advertisement)

#  delay for solenoids
speed = 0.01

while True:

	#  waiting for BLE connection
    print("Waiting for connection")
    while not ble.connected:
        pass
    print("Connected")
	#  delay after connection established
    time.sleep(1.0)

    while ble.connected:

		#  msg holds MIDI messages
        msg = midi.receive()

        for i in range(16):
			#  states for solenoid on/off
			#  noid0 = mux1
			#  noid1 = mux2
            noid0_output = noids0[i]
            noid1_output = noids1[i]

			#  states for MIDI note recieved
			#  notes0 = mux1
			#  notes1 = mux2
            notes0_played = notes0[i]
            notes1_played = notes1[i]

			#  if NoteOn msg comes in and the MIDI note # matches with predefined notes:
            if isinstance(msg, NoteOn) and msg.note is notes0_played:
                print(time.monotonic(), msg.note)

				#  solenoid is triggered
                noid0_output.value = True
				#  quick delay
                time.sleep(speed)
				#  solenoid retracts
                noid0_output.value = False

			#  identical to above if statement but for mux2
            if isinstance(msg, NoteOn) and msg.note is notes1_played:
                print(time.monotonic(), msg.note)

                noid1_output.value = True

                time.sleep(speed)

                noid1_output.value = False

	#  if BLE disconnects try reconnecting
    print("Disconnected")
    print()
    ble.start_advertising(advertisement)
