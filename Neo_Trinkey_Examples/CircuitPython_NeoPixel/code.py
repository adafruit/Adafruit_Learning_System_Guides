# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
from rainbowio import colorwheel
import neopixel

pixel_pin = board.DATA
num_pixels = 30
speed = 0.01
brightness = 0.5
order = "GRB" # "GRBW" for RGBW NeoPixels
pixels = neopixel.NeoPixel(pixel_pin, num_pixels,
                           brightness=brightness, auto_write=True,
                           pixel_order=order)
hue = 0
pixels.fill(colorwheel(hue))

while True:
    hue = (hue + 1) % 256
    pixels.fill(colorwheel(hue))
    time.sleep(speed)
