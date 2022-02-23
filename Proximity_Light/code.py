# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import busio
import neopixel
import adafruit_vl53l0x

TRIGGER_DISTANCE = 500          # number of mm where the light toggles
NEOPIXEL_PIN = board.D1
NUMBER_OF_PIXELS = 8

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_vl53l0x.VL53L0X(i2c)

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUMBER_OF_PIXELS, brightness=1.0, auto_write=False)

strip.fill((0, 0, 0))
for i in range(NUMBER_OF_PIXELS):
    strip[i] = (64, 64, 64)
    strip.show()
    time.sleep(0.1)
    strip[i] = (0, 0, 0)
    strip.show()

while True:
    if sensor.range < TRIGGER_DISTANCE:
        strip.fill((255, 255, 255))
        strip.show()
    else:
        strip.fill((0, 0, 0))
        strip.show()
    time.sleep(0.1)
