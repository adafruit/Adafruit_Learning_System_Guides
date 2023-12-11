# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import keypad

keys = keypad.Keys((board.D8,), value_when_pressed=False, pull=True)

# Create an event we will reuse over and over.
event = keypad.Event()

while True:
    if keys.events.get_into(event):
        print(event)
