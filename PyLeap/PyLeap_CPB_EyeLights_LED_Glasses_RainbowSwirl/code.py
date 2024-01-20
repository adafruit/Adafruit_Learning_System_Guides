# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
from rainbowio import colorwheel
from adafruit_is31fl3741.adafruit_ledglasses import LED_Glasses
import adafruit_is31fl3741

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
glasses = LED_Glasses(i2c, allocate=adafruit_is31fl3741.MUST_BUFFER)

wheeloffset = 0
while True:
    for i in range(24):
        hue = colorwheel(i * 256 // 24 + wheeloffset)
        glasses.right_ring[i] = hue
        glasses.left_ring[23 - i] = hue
    glasses.show()
    wheeloffset += 10
