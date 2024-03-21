# SPDX-FileCopyrightText: 2019 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import displayio
import i2cdisplaybus
import adafruit_displayio_ssd1306
import terminalio
import adafruit_ds3231
from adafruit_display_text import label


font = terminalio.FONT


displayio.release_displays()

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3c)
oled = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)

rtc = adafruit_ds3231.DS3231(i2c)


# The first time you run this code, you must set the time!
# You must set year, month, date, hour, minute, second and weekday.
# struct_time order: year, month, day (date), hour, minute, second, weekday , yearday, isdst
# yearday is not supported, isdst can be set but we don't do anything with it at this time

# UNCOMMENT THE FOLLOWING FOUR LINES THE FIRST TIME YOU RUN THE CODE TO SET THE TIME!
# import time
# set_time = time.struct_time((2019, 8, 16, 23, 59, 45, 4, -1, -1))
# print("Setting time to:", set_time)
# rtc.datetime = set_time

# Comment out the above four lines again after setting the time!


while True:
    current = rtc.datetime

    hour = current.tm_hour % 12
    if hour == 0:
        hour = 12

    am_pm = "AM"
    if current.tm_hour / 12 >= 1:
        am_pm = "PM"

    time_display = "{:d}:{:02d}:{:02d} {}".format(hour, current.tm_min, current.tm_sec, am_pm)
    date_display = "{:d}/{:d}/{:d}".format(current.tm_mon, current.tm_mday, current.tm_year)
    text_display = "CircuitPython Time"

    clock = label.Label(font, text=time_display)
    date = label.Label(font, text=date_display)
    text = label.Label(font, text=text_display)

    (_, _, width, _) = clock.bounding_box
    clock.x = oled.width // 2 - width // 2
    clock.y = 5

    (_, _, width, _) = date.bounding_box
    date.x = oled.width // 2 - width // 2
    date.y = 15

    (_, _, width, _) = text.bounding_box
    text.x = oled.width // 2 - width // 2
    text.y = 25

    watch_group = displayio.Group()
    watch_group.append(clock)
    watch_group.append(date)
    watch_group.append(text)

    oled.root_group = watch_group
