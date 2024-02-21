# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import simpleio
import adafruit_ds3231
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_ht16k33 import segments
from adafruit_debouncer import Button
from adafruit_seesaw import seesaw, rotaryio, digitalio

# min and max display brightness range
# value must be 0.0 to 1.0
max_brightness = 1
min_brightness = 0.01
# weekday hours to have clock on max brightness
# (24-hour time)
weekday_wakeup = 8
weekday_sleep = 21
# weekend hours to have clock on max brightness
# (24-hour time)
weekend_wakeup = 9
weekend_sleep = 23

i2c = board.STEMMA_I2C()

rtc = adafruit_ds3231.DS3231(i2c)
seesaw = seesaw.Seesaw(i2c, addr=0x36)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
ss_pin = digitalio.DigitalIO(seesaw, 24)
button = Button(ss_pin, long_duration_ms=1000)

encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

# pylint: disable-msg=using-constant-test
if False:  # change to True if you want to set the time!
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2024, 1, 25, 15, 7, 0, 3, -1, -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday is not supported, isdst can be set but we don't do anything with it at this time
    print("Setting time to:", t)  # uncomment for debugging
    rtc.datetime = t
    print()
# pylint: enable-msg=using-constant-test

display = segments.BigSeg7x4(i2c)

display.fill(0)
display.brightness = max_brightness

display.colon = True

def clock_conversion(h, m, set_brightness):
    # pylint: disable-msg=simplifiable-if-expression
    am_pm = False if h < 12 else True
    hour_12 = h if h <= 12 else h - 12
    if hour_12 == 0:
        hour_12 = 12
    display.print(f"{(hour_12):02}:{m:02}")
    display.ampm = am_pm
    if set_brightness:
        if awake_hours[0] <= h <= awake_hours[1] - 1:
            display.brightness = max_brightness
        elif h is awake_hours[0] - 1:
            bright = simpleio.map_range(m, 0, 59, min_brightness, max_brightness)
            display.brightness = bright
        elif h is awake_hours[1]:
            bright = simpleio.map_range(m, 0, 59, max_brightness, min_brightness)
            display.brightness = bright
        else:
            display.brightness = min_brightness
    else:
        display.brightness = max_brightness

clock_clock = ticks_ms()
clock_timer = 1 * 1000
clock_mode = True
set_hour = True
power_up = True
hour = 0
minute = 0

while True:

    if clock_mode:
        button.update()
        if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
            t = rtc.datetime
            if t.tm_wday in range(5, 6):
                awake_hours = [weekend_wakeup, weekend_sleep]
            else:
                awake_hours = [weekday_wakeup, weekday_sleep]
            if t.tm_sec < 1 or power_up:
                power_up = False
                clock_conversion(t.tm_hour, t.tm_min, True)
            clock_clock = ticks_add(clock_clock, clock_timer)
    else:
        button.update()
        position = -encoder.position
        if position != last_position:
            if position > last_position:
                if set_hour:
                    hour = (hour + 1) % 24
                else:
                    minute = (minute + 1) % 60
            else:
                if set_hour:
                    hour = (hour - 1) % 24
                else:
                    minute = (minute - 1) % 60
            clock_conversion(hour, minute, False)
            last_position = position
        if button.short_count:
            set_hour = not set_hour
        # toggling dots with not did not seem to work consistantly
        # so setting manually
        if set_hour:
            display.top_left_dot = True
            display.bottom_left_dot = False
        else:
            display.top_left_dot = False
            display.bottom_left_dot = True
    if button.long_press:
        if not clock_mode:
            t = rtc.datetime
            new_t = time.struct_time((t.tm_year, t.tm_mon, t.tm_mday,
                                      hour, minute, t.tm_sec, t.tm_wday,
                                      t.tm_yday, t.tm_isdst))
            print("Setting time to:", new_t)
            rtc.datetime = new_t
            clock_clock = ticks_add(clock_clock, clock_timer)
            power_up = True
            display.top_left_dot = False
            display.bottom_left_dot = False
        else:
            set_hour = True
            t = rtc.datetime
            hour = t.tm_hour
            minute = t.tm_min
        clock_mode = not clock_mode
        display.blink_rate = not display.blink_rate
