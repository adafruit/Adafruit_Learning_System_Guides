# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
LTC4315 with two AHT20 sensors example
Set the LTC4315 switch A5 on and switch A4 off
The translated sensor will be on address 0x68
"""

import time
import board
import adafruit_ahtx0

# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
default_sensor = adafruit_ahtx0.AHTx0(i2c, 0x38)
translated_sensor = adafruit_ahtx0.AHTx0(i2c, 0x68)

while True:
    print("\nAHT20 at 0x38:")
    print(f"Temperature: {default_sensor.temperature:0.1f} C")
    print(f"Humidity: {default_sensor.relative_humidity:0.1f} %")
    print("\nAHT20 at 0x68:")
    print(f"Temperature: {translated_sensor.temperature:0.1f} C")
    print(f"Humidity: {translated_sensor.relative_humidity:0.1f} %")
    time.sleep(2)
