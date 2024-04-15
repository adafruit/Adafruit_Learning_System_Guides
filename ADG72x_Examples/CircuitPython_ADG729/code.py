# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_adg72x
from analogio import AnalogIn

analog_in_DA = AnalogIn(board.A0)
analog_in_DB = AnalogIn(board.A1)

i2c = board.I2C()
switch = adafruit_adg72x.ADG72x(i2c, 0x44)

c = 0
switch_time = 3
clock = time.monotonic()

while True:
    if (time.monotonic() - clock) > switch_time:
        if c < 4:
            channels = "A"
        else:
            channels = "B"
        print(f"Selecting channel {(c % 4) + 1}{channels}")
        switch.channel = c
        c = (c + 1) % 8
        clock = time.monotonic()
    print((analog_in_DA.value, analog_in_DB.value,))
    time.sleep(0.1)
