# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import keypad
import board

k = keypad.Keys(
    (board.D8, board.D9),
    value_when_pressed=False,
    pull=True,
    # Increase event queue size to 128 events.
    max_events=128,
)

while True:
    event = k.events.get()
    if event:
        print(event)
