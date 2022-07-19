# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import keypad
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

KEY_PINS = (
    board.KEY1,
    board.KEY2,
    board.KEY3,
    board.KEY4,
    board.KEY5,
    board.KEY6,
    board.KEY7,
    board.KEY8,
    board.KEY9,
    board.KEY10,
    board.KEY11,
    board.KEY12,
)

KEYCODES = (
    Keycode.SEVEN,
    Keycode.EIGHT,
    Keycode.NINE,
    Keycode.FOUR,
    Keycode.FIVE,
    Keycode.SIX,
    Keycode.ONE,
    Keycode.TWO,
    Keycode.THREE,
    Keycode.BACKSPACE,
    Keycode.ZERO,
    Keycode.ENTER,
)

ON_COLOR = (0, 0, 255)
OFF_COLOR = (0, 20, 0)

keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)
neopixels = neopixel.NeoPixel(board.NEOPIXEL, 12, brightness=0.4)
neopixels.fill(OFF_COLOR)
kbd = Keyboard(usb_hid.devices)

while True:
    event = keys.events.get()
    if event:
        key_number = event.key_number
        # A key transition occurred.
        if event.pressed:
            kbd.press(KEYCODES[key_number])
            neopixels[key_number] = ON_COLOR

        if event.released:
            kbd.release(KEYCODES[key_number])
            neopixels[key_number] = OFF_COLOR
