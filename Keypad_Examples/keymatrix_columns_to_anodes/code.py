# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import keypad
import board

km = keypad.KeyMatrix(
    row_pins=(board.D0, board.D1, board.D2, board.D3),
    column_pins=(board.D4, board.D5, board.D6),
    columns_to_anodes=True,
)

while True:
    event = km.events.get()
    if event:
        print(event)
