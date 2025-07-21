# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

sensor_power = DigitalInOut(board.D5)
sensor_power.direction = Direction.OUTPUT

analog_in = AnalogIn(board.A0)

while True:
    sensor_power.value = True
    print(f"Soil Moisture: {analog_in.value}")
    sensor_power.value = False
    time.sleep(5)
