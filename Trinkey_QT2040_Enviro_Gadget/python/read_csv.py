# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import serial

# open serial port (NOTE: change location as needed)
ss = serial.Serial("/dev/ttyACM0")

# read string
_ = ss.readline() # first read may be incomplete, just toss it
raw_string = ss.readline().strip().decode()

# create list of floats
data = [float(x) for x in raw_string.split(',')]

# print them
print("CO2 =", data[0])
print("pressure =", data[1])
print("temperature =", data[2])
print("humidity =", data[3])
