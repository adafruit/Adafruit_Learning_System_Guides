"""
Circuit Playground Express head-tilt activated ears.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import busio
import board
import adafruit_lis3dh
import simpleio

# Setup accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
sensor = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)

# Setup servos
left_ear = simpleio.Servo(board.A1)
right_ear = simpleio.Servo(board.A2)

#initialize things
left_ear.angle = 0
right_ear.angle = 0

while True:
    x, _, _ = sensor.acceleration
    if x < -5.0:
        left_ear.angle = 90
    elif x > 5.0:
        right_ear.angle = 90
    elif abs(x) < 4.0:
        left_ear.angle = 0
        right_ear.angle = 0
    time.sleep(0.1)
