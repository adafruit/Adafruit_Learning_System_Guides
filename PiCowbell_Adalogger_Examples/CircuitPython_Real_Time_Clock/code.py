# SPDX-FileCopyrightText: 2017 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
import adafruit_pcf8523

I2C = busio.I2C(board.GP5, board.GP4)
rtc = adafruit_pcf8523.PCF8523(I2C)

days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")

set_time = False

if set_time:   # change to True if you want to write the time!
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2023,  3,   6,   10,  55,  00,    1,   -1,    -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday is not supported, isdst can be set but we don't do anything with it at this time

    print("Setting time to:", t)     # uncomment for debugging
    rtc.datetime = t
    print()

while True:
    t = rtc.datetime
    #print(t)     # uncomment for debugging

    print("The date is %s %d/%d/%d" % (days[t.tm_wday], t.tm_mon, t.tm_mday, t.tm_year))
    print("The time is %d:%02d:%02d" % (t.tm_hour, t.tm_min, t.tm_sec))

    time.sleep(1) # wait a second
