# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import wifi
import board
import displayio
import socketpool
import microcontroller
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
import adafruit_ntp
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

timezone = -4
# The time of the thing!
EVENT_YEAR = 2024
EVENT_MONTH = 8
EVENT_DAY = 16
EVENT_HOUR = 0
EVENT_MINUTE = 0
# we'll make a python-friendly structure
event_time = time.struct_time((EVENT_YEAR, EVENT_MONTH, EVENT_DAY,
                               EVENT_HOUR, EVENT_MINUTE, 0,  # we don't track seconds
                               -1, -1, False))  # we dont know day of week/year or DST

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=timezone, cache_seconds=3600)

display = board.DISPLAY
group = displayio.Group()
font = bitmap_font.load_font("/Helvetica-Bold-16.pcf")
blinka_bitmap = displayio.OnDiskBitmap("/cpday_tft.bmp")
blinka_grid = displayio.TileGrid(blinka_bitmap, pixel_shader=blinka_bitmap.pixel_shader)
scrolling_label = bitmap_label.Label(font, text=" ", y=display.height - 15)

group.append(blinka_grid)
group.append(scrolling_label)
display.root_group = group
display.auto_refresh = False

refresh_clock = ticks_ms()
refresh_timer = 3600 * 1000
clock_clock = ticks_ms()
clock_timer = 1000
scroll_clock = ticks_ms()
scroll_timer = 50
first_run = True

while True:
    # only query the online time once per hour (and on first run)
    if ticks_diff(ticks_ms(), refresh_clock) >= refresh_timer or first_run:
        try:
            print("Getting time from internet!")
            now = ntp.datetime
            print(now)
            total_seconds = time.mktime(now)
            first_run = False
            refresh_clock = ticks_add(refresh_clock, refresh_timer)
        except Exception as e: # pylint: disable=broad-except
            print("Some error occured, retrying! -", e)
            time.sleep(2)
            microcontroller.reset()

    if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
        remaining = time.mktime(event_time) - total_seconds
        secs_remaining = remaining % 60
        remaining //= 60
        mins_remaining = remaining % 60
        remaining //= 60
        hours_remaining = remaining % 24
        remaining //= 24
        days_remaining = remaining
        scrolling_label.text = (f"{days_remaining} DAYS, {hours_remaining} HOURS," +
                               f"{mins_remaining} MINUTES & {secs_remaining} SECONDS")
        total_seconds += 1
        clock_clock = ticks_add(clock_clock, clock_timer)
    if ticks_diff(ticks_ms(), scroll_clock) >= scroll_timer:
        scrolling_label.x -= 1
        if scrolling_label.x < -(scrolling_label.width + 5):
            scrolling_label.x = display.width + 2
        display.refresh()
        scroll_clock = ticks_add(scroll_clock, scroll_timer)
