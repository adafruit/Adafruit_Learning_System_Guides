# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""This uses the Feather Sense as a Bluetooth LE sensor node."""

import time
import adafruit_ble_broadcastnet
import board
import adafruit_lsm6ds   # accelerometer
import adafruit_sht31d   # humidity sensor
import adafruit_bmp280   # barometric sensor
import adafruit_lis3mdl  # magnetic sensor

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

sense_accel = adafruit_lsm6ds.LSM6DS33(i2c)
sense_humid = adafruit_sht31d.SHT31D(i2c)
sense_barometric = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
sense_magnet = adafruit_lis3mdl.LIS3MDL(i2c)

print("This is BroadcastNet Feather Sense sensor:", adafruit_ble_broadcastnet.device_address)

while True:
    measurement = adafruit_ble_broadcastnet.AdafruitSensorMeasurement()

    measurement.temperature = sense_barometric.temperature
    measurement.pressure = sense_barometric.pressure
    measurement.relative_humidity = sense_humid.relative_humidity
    measurement.acceleration = sense_accel.acceleration
    measurement.magnetic = sense_magnet.magnetic

    # print(measurement)
    adafruit_ble_broadcastnet.broadcast(measurement)
    time.sleep(60)
