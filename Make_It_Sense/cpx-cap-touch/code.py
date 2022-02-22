# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from adafruit_circuitplayground.express import cpx

# NeoPixel blank out
cpx.pixels.fill( (0, 0, 0) )

# Set sensitivity of all touch pads
cpx.adjust_touch_threshold(200)

# Check for touch, if so light the nearby NeoPixel green
while True:
    if cpx.touch_A4:
        cpx.pixels[0] = (0, 30, 0)
    if cpx.touch_A5:
        cpx.pixels[1] = (0, 30, 0)
    if cpx.touch_A6:
        cpx.pixels[3] = (0, 30, 0)
    if cpx.touch_A7:
        cpx.pixels[4] = (0, 30, 0)
    if cpx.button_a:  # blank lights on Button A
        cpx.pixels.fill( (0, 0, 0) )
