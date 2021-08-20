# Write the time for the Adafruit DS3231 real-time clock.
# Limor Fried/Mike Barela for Adafruit Industries

import time
import board
import busio as io
import digitalio
import adafruit_ds3231

i2c = io.I2C(board.SCL, board.SDA)

# Create the RTC instance:
rtc = adafruit_ds3231.DS3231(i2c)

LED13 = digitalio.DigitalInOut(board.D13)
LED13.direction = digitalio.Direction.OUTPUT

# pylint: disable-msg=bad-whitespace
# pylint: disable-msg=using-constant-test
if True:
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2019,   7,    10,   17,  00,   0,    0,   -1,    -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday is not supported
    # isdst can be set but we don't do anything with it at this time
    print("Setting time to:", t)     # uncomment for debugging
    rtc.datetime = t
    print("Done!")
    LED13.value = True
# pylint: enable-msg=using-constant-test
# pylint: enable-msg=bad-whitespace
