# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
from rainbowio import colorwheel
from adafruit_seesaw import seesaw, neopixel

i2c = busio.I2C(board.SCL, board.SDA)
ss = seesaw.Seesaw(i2c, addr=0x60)
neo_pin = 15
num_pixels = 64

pixels = neopixel.NeoPixel(ss, neo_pin, num_pixels, brightness = 0.1)

color_offset = 0

while True:
    for i in range(num_pixels):
        rc_index = (i * 256 // num_pixels) + color_offset
        pixels[i] = colorwheel(rc_index & 255)
    pixels.show()
    color_offset += 1
    time.sleep(0.01)
