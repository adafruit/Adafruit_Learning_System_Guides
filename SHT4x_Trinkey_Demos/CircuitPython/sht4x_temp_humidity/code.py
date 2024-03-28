# SPDX-FileCopyrightText: Copyright (c) 2020 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_sht4x

i2c = board.I2C()  # uses board.SCL and board.SDA
sht = adafruit_sht4x.SHT4x(i2c)
print("Found SHT4x with serial number", hex(sht.serial_number))

sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
print("Current mode is: ", adafruit_sht4x.Mode.string[sht.mode])
print()

while True:
    temperature, relative_humidity = sht.measurements
    print(f"Temperature: {temperature:0.1f} C")
    print(f"Humidity: {relative_humidity:0.1f} %")
    print("")
    time.sleep(1)
