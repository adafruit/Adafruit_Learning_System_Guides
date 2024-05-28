# SPDX-FileCopyrightText: 2024 Bill Binko
#
# SPDX-License-Identifier: MIT

import digitalio
import board
import keypad
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

#We are only using Ring1 and Tip as input - set Ring2 & sleeve to GND
ground = digitalio.DigitalInOut(board.RING_2)
ground.direction=digitalio.Direction.OUTPUT
ground.value = False

ground2 = digitalio.DigitalInOut(board.SLEEVE)
ground2.direction=digitalio.Direction.OUTPUT
ground2.value = False

# Initialize Keyboard to send HID to host
kbd = Keyboard(usb_hid.devices)

#Setup which keystrokes to send on each switch press
#Any Keycodes can be sent
#Common AT device keystrokes:

#  Web Browser: Enter/Space
#keycodeList = [Keycode.ENTER, Keycode.SPACE]
#  Speech Devices (Tobii/PRC): ONE/TWO
#keycodeList = [Keycode.ONE, Keycode.TWO]
#  iOS Switch Control: A/B (reads only from "Switch Keyboard" not other keyboards)
keycodeList = [Keycode.A, Keycode.B]


#Use Keypad library to read buttons wired between ground and Tip/Ring1
keys = keypad.Keys((board.TIP,board.RING_1), value_when_pressed=False, pull=True)

#Main loop for events
while True:
    event=keys.events.get()
    if event:
        if event.pressed:
            kbd.press(keycodeList[event.key_number])
        else:
            kbd.release(keycodeList[event.key_number])
