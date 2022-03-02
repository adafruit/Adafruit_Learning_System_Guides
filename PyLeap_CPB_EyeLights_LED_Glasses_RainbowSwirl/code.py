# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
from rainbowio import colorwheel
from adafruit_is31fl3741.adafruit_ledglasses import LED_Glasses
import adafruit_is31fl3741

glasses = LED_Glasses(board.I2C(), allocate=adafruit_is31fl3741.MUST_BUFFER)

wheeloffset = 0
while True:
    for i in range(24):
        hue = colorwheel(i * 256 // 24 + wheeloffset)
        glasses.right_ring[i] = hue
        glasses.left_ring[23 - i] = hue
    glasses.show()
    wheeloffset += 10
