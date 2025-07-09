# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=wildcard-import, undefined-variable

"""MicroPython Advanced Soil Sensing Demo for micro:bit"""
from microbit import *

while True:
    pin2.write_digital(1)
    sleep(100)
    moisture = pin0.read_analog()
    if moisture > 200:
        display.show(Image.HAPPY)
    else:
        display.show(Image.SAD)
    pin2.write_digital(0)
    sleep(5000)
