# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
from digitalio import DigitalInOut, Direction, Pull
import rotaryio
from adafruit_debouncer import Button
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService

#  pin assignments for the rotary encoder
ENCA = board.SDA
ENCB = board.SCL
COMA = board.D5
CENTER = board.D6
RIGHT = board.D9
UP = board.D10
LEFT = board.D11
DOWN = board.D12
COMB = board.D13

#  mode slide switch pin
SWITCH = board.A1

# Rotary encoder setup
encoder = rotaryio.IncrementalEncoder(ENCA, ENCB)
last_position = 0

# setting the COMA and COMB pins to LOW aka GND
com_a = DigitalInOut(COMA)
com_a.switch_to_output()
com_a = False
com_b = DigitalInOut(COMB)
com_b.switch_to_output()
com_b = False

#  mode switch setup
SWITCH = DigitalInOut(board.A1)
SWITCH.direction = Direction.INPUT
SWITCH.pull = Pull.UP

#  encoder button pins
enc_buttons = (
    CENTER,
    UP,
    LEFT,
    DOWN,
    RIGHT,
)

#  array for the encoder buttons
inputs = []

#  setting the encoder buttons as inputs
for enc in enc_buttons:
    enc_button = DigitalInOut(enc)
    enc_button.pull = Pull.UP
	#  adding to the inputs array with the Button Class of the Debouncer lib
    inputs.append(Button(enc_button))

#  streaming mode keycodes
CHILL_CODES = (
    Keycode.SPACE,
    Keycode.F,
    Keycode.LEFT_ARROW,
    Keycode.M,
    Keycode.RIGHT_ARROW,
)

#  doom mode keycodes
DOOM_CODES = (
    Keycode.CONTROL,
    Keycode.UP_ARROW,
    Keycode.LEFT_ARROW,
    Keycode.DOWN_ARROW,
    Keycode.RIGHT_ARROW,
)

#  streaming state
chill = True
#  doom state
doom = False

#  BLE HID setup
hid = HIDService()

advertisement = ProvideServicesAdvertisement(hid)
advertisement.appearance = 961
scan_response = Advertisement()
scan_response.complete_name = "CircuitPython HID"

#  BLE instance
ble = adafruit_ble.BLERadio()

#  keyboard HID setup
kbd = Keyboard(hid.devices)

#  BLE advertisement
if not ble.connected:
    print("advertising")
    ble.start_advertising(advertisement, scan_response)
else:
    print("connected")
    print(ble.connections)

while True:
	#  check for BLE connection
    while not ble.connected:
        pass
	#  while BLE connected
    while ble.connected:
		#  mode switch
		#  selects whether to be in streaming mode or doom mode
		#  affects the keycodes assigned to the encoder's inputs
        if not SWITCH.value:
            chill = False
            doom = True
        if SWITCH.value:
            chill = True
            doom = False

		#  rotary encoder position tracking
        position = encoder.position
		#  if the encoder is turned to the right
        if position > last_position:
			#  if in streaming mode
            if chill:
				#  send UP arrow for volume
                kbd.send(Keycode.UP_ARROW)
			#  if in doom mode
            if doom:
				#  send period for right strafe
                kbd.send(Keycode.PERIOD)
			#  reset encoder position
            last_position = position
		#  if the encoder is turned to the left
        if position < last_position:
            #  if in streaming mode
            if chill:
				#  send DOWN arrow for volume
                kbd.send(Keycode.DOWN_ARROW)
			#  if in doom mode
            if doom:
				#  send comma for left strafe
                kbd.send(Keycode.COMMA)
			#  reset encoder position
            last_position = position

		#  for loop for keycodes
        for i in range(5):
			#  update state of the buttons
            inputs[i].update()
			#  if you press the center button for a long press
            if inputs[0].long_press:
				#  sends space key
				#  used in Doom for use/open
                kbd.send(Keycode.SPACE)
			#  if a press is detected...
            if inputs[i].pressed:
				#  if in streaming mode
                if chill:
					#  send the streaming keycodes
                    kbd.press(CHILL_CODES[i])
				#  if in doom mode
                if doom:
					#  send the doom keycodes
                    kbd.press(DOOM_CODES[i])
			#  if a button is released...
            if inputs[i].released:
				#  if in streaming mode
                if chill:
					#  release the streaming keycodes
                    kbd.release(CHILL_CODES[i])
				#  if in doom mode
                if doom:
					#  release the doom keycodes
                    kbd.release(DOOM_CODES[i])

	#  if BLE disconnects, begin advertising again
    ble.start_advertising(advertisement)
