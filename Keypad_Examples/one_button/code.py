# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import keypad

keys = keypad.Keys((board.D5,), value_when_pressed=False, pull=True)

while True:
    event = keys.events.get()
    # event will be None if nothing has happened.
    if event:
        print(event)
