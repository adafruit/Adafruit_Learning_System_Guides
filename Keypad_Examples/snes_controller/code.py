# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import keypad
import board

SNES_KEY_NAMES = (
    "B",
    "Y",
    "SELECT",
    "START",
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "A",
    "X",
    "L",
    "R",
)

shift_k = keypad.ShiftRegisterKeys(
    clock=board.D5,
    latch=board.D6,
    value_to_latch=False,
    data=board.D7,
    key_count=12,
    value_when_pressed=False,
)

while True:
    event = shift_k.events.get()
    if event:
        print(
            SNES_KEY_NAMES[event.key_number],
            "pressed" if event.pressed else "released",
        )
