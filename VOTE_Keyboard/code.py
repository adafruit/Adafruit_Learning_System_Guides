# SPDX-FileCopyrightText: 2020 Collin Cunningham for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
from digitalio import DigitalInOut, Direction, Pull
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

kbd = Keyboard(usb_hid.devices)
kbdLayout = KeyboardLayoutUS(kbd)
state = []
pins = {}
buttonMap = [
    dict(row="D4", col="D0", id=1),
    dict(row="D4", col="D1", id=2),
    dict(row="D4", col="D2", id=3),
    dict(row="D3", col="D2", id=4),
    dict(row="D3", col="D0", id=5),
    dict(row="D3", col="D1", id=6)]

# Set up row pins
for pin in ["D4", "D3"]:
    p = DigitalInOut(getattr(board, pin))
    p.direction = Direction.OUTPUT
    pins[pin] = p

# Set up column pins
for pin in ["D0", "D1", "D2"]:
    p = DigitalInOut(getattr(board, pin))
    p.direction = Direction.INPUT
    p.pull = Pull.DOWN
    pins[pin] = p

buttonIDtoKeycode = {
    1: Keycode.V,
    2: Keycode.O,
    3: Keycode.T,
    4: Keycode.E,
    5: Keycode.SPACE,
    6: Keycode.ENTER}

while True:
	# Compare old and new state
    oldState = state
    newState = []
    newBtn = None
    for button in buttonMap:
        r = pins[button["row"]]
        r.value = True
        if pins[button["col"]].value:
            newState += [button["id"]]
            if not button["id"] in oldState:
                newBtn = button["id"]
        r.value = False
    # Press & release keys
    for oldID in oldState:
        if not oldID in newState:
            kbd.release(buttonIDtoKeycode[oldID])
    if newBtn:
        kbd.press(buttonIDtoKeycode[newBtn])
    state = newState
    