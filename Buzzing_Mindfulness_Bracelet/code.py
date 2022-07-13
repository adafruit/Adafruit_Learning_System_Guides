# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Mindfulness Bracelet sketch for Adafruit Gemma.  Briefly runs
# vibrating motor (connected through transistor) at regular intervals.

import time
import board
from digitalio import DigitalInOut, Direction

# vibrating disc mini motor disc connected on D1
vibrating_disc = DigitalInOut(board.D1)
vibrating_disc.direction = Direction.OUTPUT

on_time = 2     # Vibration motor run time, in seconds
interval = 60   # Time between reminders, in seconds

start_time = time.monotonic()

while True:

    timer = time.monotonic() - start_time

    if timer >= interval and timer <= (interval + on_time):
        vibrating_disc.value = True

    elif timer >= (interval + on_time):
        vibrating_disc.value = False
        start_time = time.monotonic()
