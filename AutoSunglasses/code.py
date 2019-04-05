"""
Circuit Playground Express auto-sunglasses/flashlight

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import board
import simpleio
from adafruit_circuitplayground.express import cpx

servo = simpleio.Servo(board.A1)

cpx.pixels.fill((0, 0, 0))
servo.angle = 90

while True:
    light_level = cpx.light

    if light_level < 10:
        cpx.pixels.fill((200, 200, 200))
    else:
        cpx.pixels.fill((0, 0, 0))
        if light_level < 200:
            servo.angle = 90
        else:
            servo.angle = 0

    time.sleep(0.25)
