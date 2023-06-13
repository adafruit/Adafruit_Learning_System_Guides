# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

'''This example should only be used with Linux single board computers
that require creating an I2C busio object by passing in the Bus ID'''

import time
from rainbowio import colorwheel
from adafruit_extended_bus import ExtendedI2C as I2C
from adafruit_seesaw import seesaw, neopixel

i2c = I2C(1, frequency=800000)
ss = seesaw.Seesaw(i2c, addr=0x60)
neo_pin = 15
num_pixels = 30

pixels = neopixel.NeoPixel(ss, neo_pin, num_pixels, brightness = 0.3, auto_write=False)

color_offset = 0

while True:
    for i in range(num_pixels):
        rc_index = (i * 256 // num_pixels) + color_offset
        pixels[i] = colorwheel(rc_index & 255)
    pixels.show()
    color_offset += 8
    time.sleep(0.01)
