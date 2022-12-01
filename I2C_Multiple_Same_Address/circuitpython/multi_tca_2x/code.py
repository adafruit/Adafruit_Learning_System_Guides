# SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_tca9548a
from adafruit_bme280 import basic as adafruit_bme280

# Create I2C bus as normal
i2c = board.I2C()

#--------------------------------------------------------------------
# NOTE!!! This is the "special" part of the code
#
# For each TCA9548A, create a separate instance and give each
# the *same* I2C bus but with specific address for each
tca1 = adafruit_tca9548a.TCA9548A(i2c, 0x70)   # TCA with address 0x70
tca2 = adafruit_tca9548a.TCA9548A(i2c, 0x71)   # TCA with address 0x71
# Create each BME280 using the TCA9548A channel instead of the I2C object
# Be sure to use the TCA instance each BME280 is attached to
bme1 = adafruit_bme280.Adafruit_BME280_I2C(tca1[0])   # TCA 1 Channel 0
bme2 = adafruit_bme280.Adafruit_BME280_I2C(tca1[1])   # TCA 1 Channel 1
bme3 = adafruit_bme280.Adafruit_BME280_I2C(tca2[0])   # TCA 2 Channel 0
#--------------------------------------------------------------------

print("Multiple BME280 / Multiple TCA9548A Example")

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
