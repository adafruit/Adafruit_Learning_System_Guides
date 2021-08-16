"""
FlappyBird type game for the NeoTrellisM4

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=wildcard-import,unused-wildcard-import,eval-used

import game
import board
import adafruit_trellism4
import adafruit_adxl34x
import busio
from color_names import *


trellis = adafruit_trellism4.TrellisM4Express()
trellis.pixels.auto_write = False

i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelerometer = adafruit_adxl34x.ADXL345(i2c)

the_game = game.Game(trellis, accelerometer)

for x in range(8):
    for y in range(4):
        if x > 3:
            trellis.pixels[x, y] = BLUE
        else:
            trellis.pixels[x, y] = YELLOW
trellis.pixels.show()

keys = []
while not keys:
    keys = trellis.pressed_keys

while True:
    the_game.play(keys[0][0] < 4)        # False = key, True = accel
