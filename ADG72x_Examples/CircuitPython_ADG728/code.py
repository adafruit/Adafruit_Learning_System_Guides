# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_adg72x
from analogio import AnalogIn

analog_in = AnalogIn(board.A0)

i2c = board.I2C()
switch = adafruit_adg72x.ADG72x(i2c)

c = 0
switch_time = 2
channels = [0, 4]
clock = time.monotonic()
while True:
    if (time.monotonic() - clock) > switch_time:
        print(f"Selecting channel {channels[c] + 1}")
        switch.channel = channels[c]
        c = (c + 1) % 2
        clock = time.monotonic()
    print((analog_in.value,))
    time.sleep(0.1)
