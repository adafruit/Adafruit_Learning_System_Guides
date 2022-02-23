# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_pcf8523

pcf = adafruit_pcf8523.PCF8523(board.I2C())

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