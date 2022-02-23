# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""This uses the CLUE as a Bluetooth LE sensor node."""

import time
from adafruit_clue import clue
import adafruit_ble_broadcastnet

print("This is BroadcastNet CLUE sensor:", adafruit_ble_broadcastnet.device_address)

while True:
    measurement = adafruit_ble_broadcastnet.AdafruitSensorMeasurement()

    measurement.temperature = clue.temperature
    measurement.pressure = clue.pressure
    measurement.relative_humidity = clue.humidity
    measurement.acceleration = clue.acceleration
    measurement.magnetic = clue.magnetic

    print(measurement)
    adafruit_ble_broadcastnet.broadcast(measurement)
    time.sleep(60)
