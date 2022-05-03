# SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_tca9548a
from adafruit_bme280 import basic as adafruit_bme280

# Create I2C bus as normal
i2c = board.I2C()

# Create the TCA9548A object and give it the I2C bus
tca = adafruit_tca9548a.TCA9548A(i2c)

#--------------------------------------------------------------------
# NOTE!!! This is the "special" part of the code
#
# Create each BME280 using the TCA9548A channel instead of the I2C object
bme1 = adafruit_bme280.Adafruit_BME280_I2C(tca[0])
bme2 = adafruit_bme280.Adafruit_BME280_I2C(tca[1])
bme3 = adafruit_bme280.Adafruit_BME280_I2C(tca[2])
#--------------------------------------------------------------------

print("Three BME280 Example")

while True:
    # Access each sensor via its instance
    pressure1 = bme1.pressure
    pressure2 = bme2.pressure
    pressure3 = bme3.pressure

    print("-"*20)
    print("BME280 #1 Pressure =", pressure1)
    print("BME280 #2 Pressure =", pressure2)
    print("BME280 #3 Pressure =", pressure3)

    time.sleep(1)