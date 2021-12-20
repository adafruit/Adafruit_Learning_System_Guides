# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_scd4x
from adafruit_bme280 import basic as adafruit_bme280

scd = adafruit_scd4x.SCD4X(board.I2C())
scd.start_periodic_measurement()

bme = adafruit_bme280.Adafruit_BME280_I2C(board.I2C())

while True:
    time.sleep(5)
    print("CO2 =", scd.CO2)
    print("Pressure = {:.1f} hPa".format(bme.pressure))
    print("Temperature = {:.1f} degC".format(bme.temperature))
    print("Humidity = {:.1f}%".format(bme.humidity))
