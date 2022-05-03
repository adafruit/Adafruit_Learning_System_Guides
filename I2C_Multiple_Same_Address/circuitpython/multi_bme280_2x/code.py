# SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_bme280 import basic as adafruit_bme280

# Get the board's default I2C port
i2c = board.I2C()

# Create each sensor instance
bme1 = adafruit_bme280.Adafruit_BME280_I2C(i2c)        # default 0x77 address
bme2 = adafruit_bme280.Adafruit_BME280_I2C(i2c, 0x76)  # alternate 0x76 address

print("Two BME280 Example")

while True:
    # Access each sensor via its instance
    pressure1 = bme1.pressure
    pressure2 = bme2.pressure

    print("-"*20)
    print("BME280 #1 Pressure =", pressure1)
    print("BME280 #2 Pressure =", pressure2)

    time.sleep(1)