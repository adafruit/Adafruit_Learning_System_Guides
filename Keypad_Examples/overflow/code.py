# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import keypad
import board

k = keypad.Keys(
    (board.D8, board.D9),
    value_when_pressed=False,
    pull=True,
)

while True:
    # Check if we lost some events.
    if k.events.overflowed:
        k.events.clear()  # Empty the event queue.
        k.reset()  # Forget any existing presses. Start over.

    event = k.events.get()
    if event:
        print(event)
