# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import serial

# open serial port
ss = serial.Serial("/dev/ttyACM0")

# read string
_ = ss.readline() # first read may be incomplete, just toss it
raw_string = ss.readline().strip().decode()

# create list of integers
rnd_ints = [int(x) for x in raw_string.split(',')]

# print them
print(rnd_ints)
