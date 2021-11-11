# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Circuit Playground Bluefruit NeoPixel Button Control

Press button A to light up half the NeoPixels and button B to light up the other half.
"""
from adafruit_circuitplayground import cp

# Choose colors. Defaults to red for button A and green for button B. These are RGB values, where
# (r, g, b) represents red, green, and blue. Each value has a range of 0-255, where 0 is off and
# 255 is max intensity. You can update these values to change the colors. For example, (0, 255, 0)
# would be max green. You can combine numbers within the range to make other colors such as
# (255, 0, 180) being pink. Try it out!
color_value_a = (255, 0, 0)
color_value_b = (0, 255, 0)

cp.pixels.brightness = 0.3

while True:
    if cp.button_a:
        cp.pixels[0:5] = [color_value_a] * 5
    else:
        cp.pixels[0:5] = [(0, 0, 0)] * 5

    if cp.button_b:
        cp.pixels[5:10] = [color_value_b] * 5
    else:
        cp.pixels[5:10] = [(0, 0, 0)] * 5
