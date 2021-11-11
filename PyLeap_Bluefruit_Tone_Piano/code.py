# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Bluefruit Light-Up Tone Piano

Touch the each of the touchpads around the outside of the board to play a tone for each pad.
Touch A6 and TX at the same time to play the final tone in the octave. A0 is not a touchpad.
"""

from adafruit_circuitplayground import cp

cp.pixels.brightness = 0.3

while True:
    if cp.touch_A1:
        cp.pixels.fill((255, 0, 0))
        cp.start_tone(262)
    elif cp.touch_A2:
        cp.pixels.fill((210, 45, 0))
        cp.start_tone(294)
    elif cp.touch_A3:
        cp.pixels.fill((155, 155, 0))
        cp.start_tone(330)
    elif cp.touch_A4:
        cp.pixels.fill((0, 255, 0))
        cp.start_tone(349)
    elif cp.touch_A5:
        cp.pixels.fill((0, 255, 255))
        cp.start_tone(392)
    elif cp.touch_A6 and not cp.touch_A7:
        cp.pixels.fill((0, 0, 255))
        cp.start_tone(440)
    elif cp.touch_A7 and not cp.touch_A6:
        cp.pixels.fill((100, 0, 255))
        cp.start_tone(494)
    elif cp.touch_A6 and cp.touch_A7:
        cp.pixels.fill((255, 0, 255))
        cp.start_tone(523)
    else:
        cp.pixels.fill((0, 0, 0))
        cp.stop_tone()
