# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import json
import serial

# open serial port (NOTE: change location as needed)
ss = serial.Serial("/dev/ttyACM0")

# read string
_ = ss.readline() # first read may be incomplete, just toss it
raw_string = ss.readline().strip().decode()

# load JSON
data = json.loads(raw_string)

# print data
print("CO2 =", data['CO2'])
print("pressure =", data['pressure'])
print("temperature =", data['temperature'])
print("humidity =", data['humidity'])