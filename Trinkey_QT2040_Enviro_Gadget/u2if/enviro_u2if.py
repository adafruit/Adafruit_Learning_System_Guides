# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_scd4x
from adafruit_bme280 import basic as adafruit_bme280

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
scd = adafruit_scd4x.SCD4X(i2c)
scd.start_periodic_measurement()

bme = adafruit_bme280.Adafruit_BME280_I2C(i2c)

while True:
    time.sleep(5)
    print("CO2 =", scd.CO2)
    print("Pressure = {:.1f} hPa".format(bme.pressure))
    print("Temperature = {:.1f} degC".format(bme.temperature))
    print("Humidity = {:.1f}%".format(bme.humidity))
