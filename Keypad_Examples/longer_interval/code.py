# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import keypad
import board

km = keypad.KeyMatrix(
    row_pins=(board.A0, board.A1, board.A2, board.A3),
    column_pins=(board.D0, board.D1, board.D2),
    # Allow 50 msecs to debounce.
    interval=0.050,
)

while True:
    event = km.events.get()
    if event:
        print(event)
