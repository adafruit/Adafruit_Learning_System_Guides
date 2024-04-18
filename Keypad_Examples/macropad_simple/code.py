# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import keypad
import neopixel

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

keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)

neopixels = neopixel.NeoPixel(board.NEOPIXEL, 12, brightness=0.4)

while True:
    event = keys.events.get()
    if event:
        # A key transition occurred.
        print(event)

        if event.pressed:
            # Turn the key blue when pressed
            neopixels[event.key_number] = (0, 0, 255)

        # This could just be `else:`,
        # since event.pressed and event.released are opposites.
        if event.released:
            neopixels[event.key_number] = (0, 0, 0)
