# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_pcf8523.pcf8523 import PCF8523

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
pcf = PCF8523(i2c)

# values to set
YEAR = 2021
MON = 1
DAY = 1
HOUR = 12
MIN = 23
SEC = 42

print("Ready to set RTC to: {:4}/{:2}/{:2}  {:2}:{:02}:{:02}".format(YEAR,
                                                                     MON,
                                                                     DAY,
                                                                     HOUR,
                                                                     MIN,
                                                                     SEC))
_ = input("Press ENTER to set.")

pcf.datetime = time.struct_time((YEAR, MON, DAY, HOUR, MIN, SEC, 0, -1, -1))

print("SET!")

while True:
    now = pcf.datetime
    print("{:4}/{:2}/{:2}  {:2}:{:02}:{:02}".format(now.tm_year,
                                                  now.tm_mon,
                                                  now.tm_mday,
                                                  now.tm_hour,
                                                  now.tm_min,
                                                  now.tm_sec))
    time.sleep(1)
