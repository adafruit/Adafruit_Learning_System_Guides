# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=wildcard-import, undefined-variable

"""MicroPython Simple Soil Sensing Demo for micro:bit"""
from microbit import *

while True:
    moisture = pin0.read_analog()
    if moisture > 200:
        display.show(Image.HAPPY)
    else:
        display.show(Image.SAD)
    sleep(5000)
