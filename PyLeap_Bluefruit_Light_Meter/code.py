# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Bluefruit NeoPixel Light Meter.

Shine a light on the front of the Circuit Playground Bluefruit to see the number of NeoPixels lit
up increase. Cover the front of the CPB to see the number decrease.
"""
from adafruit_circuitplayground import cp

# Choose a color. Defaults to cyan. This is an RGB value, where (r, g, b) represents red, green,
# and blue. Each value has a range of 0-255, where 0 is off and 255 is max intensity. You can
# update these values to change the colors. For example, (0, 255, 0) would be max green. You can
# combine numbers within the range to make other colors such as (255, 0, 180) being pink.
# Try it out!
color_value = (0, 255, 255)

cp.pixels.auto_write = False
cp.pixels.brightness = 0.3


def scale_range(value):
    """Scale a value from 0-320 (light range) to 0-9 (NeoPixel range).
    Allows remapping light value to pixel position."""
    return round(value / 320 * 9)


while True:
    peak = scale_range(cp.light)

    for i in range(10):
        if i <= peak:
            cp.pixels[i] = color_value
        else:
            cp.pixels[i] = (0, 0, 0)
    cp.pixels.show()
