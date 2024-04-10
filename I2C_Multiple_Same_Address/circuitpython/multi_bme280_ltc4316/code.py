# SPDX-FileCopyrightText: 2024 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_bme280 import basic as adafruit_bme280

# Get the board's default I2C port
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

#--------------------------------------------------------------------
# NOTE!!! This is the "special" part of the code
#
# Create each sensor instance
# If left out, the default address is used.
# But also OK to be explicit and specify address.
bme1 = adafruit_bme280.Adafruit_BME280_I2C(i2c, 0x77)  # address = 0x77
bme2 = adafruit_bme280.Adafruit_BME280_I2C(i2c, 0x37)  # address = 0x37
#--------------------------------------------------------------------

print("Two BME280 Example")

while True:
    # Access each sensor via its instance
    pressure1 = bme1.pressure
    pressure2 = bme2.pressure

    print("-"*20)
    print("BME280 #1 Pressure =", pressure1)
    print("BME280 #2 Pressure =", pressure2)

    time.sleep(1)
