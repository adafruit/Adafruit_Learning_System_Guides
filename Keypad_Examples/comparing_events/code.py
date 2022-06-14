# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board

from keypad import Keys, Event

keys = Keys((board.D8, board.D9, board.D10), value_when_pressed=False, pull=True)

LEFT_EVENT = Event(0, True)  # Button 0 (D8) pressed
RIGHT_EVENT = Event(1, True)  # Button 1 (D9) pressed
STOP_EVENT = Event(2, True)  # Button 2 (D10) pressed

DIRECTION = {
    LEFT_EVENT: "LEFT",
    RIGHT_EVENT: "RIGHT",
}

while True:
    event = keys.events.get()
    if event:
        if event == STOP_EVENT:
            print("stop")
            break

        # Look up the event. If not found, direction is None.
        direction = DIRECTION.get(event)
        if direction:
            print(direction)
