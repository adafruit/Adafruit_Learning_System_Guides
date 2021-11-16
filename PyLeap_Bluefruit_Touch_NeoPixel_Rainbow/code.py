# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Bluefruit Capacitive Touch Rainbow

Touch the each of the touchpads around the outside of the board to light up the pixels a different
color for each pad touched.
"""
from adafruit_circuitplayground import cp

cp.pixels.brightness = 0.3

while True:
    if cp.touch_A1:
        cp.pixels.fill((255, 0, 0))
    if cp.touch_A2:
        cp.pixels.fill((210, 45, 0))
    if cp.touch_A3:
        cp.pixels.fill((155, 100, 0))
    if cp.touch_A4:
        cp.pixels.fill((0, 255, 0))
    if cp.touch_A5:
        cp.pixels.fill((0, 135, 125))
    if cp.touch_A6:
        cp.pixels.fill((0, 0, 255))
    if cp.touch_TX:
        cp.pixels.fill((100, 0, 155))
