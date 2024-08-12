# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-FileCopyrightText: 2024 Tyeth Gundry for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import wifi
import board
import displayio
import microcontroller
import adafruit_connection_manager
import adafruit_requests

## Import either NeoPixel or DotStar, depending on your hardware
# import neopixel
from adafruit_dotstar import DotStar

from adafruit_io.adafruit_io import IO_HTTP
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

## See TZ Identifier column at https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
## If you want to set the timezone, you can do so with the following line:
timezone = "GB"
#timezone = None  # Or instead rely on automatic timezone detection based on IP Address


## The time of the thing!
EVENT_YEAR = 2024
EVENT_MONTH = 8
EVENT_DAY = 16
EVENT_HOUR = 0
EVENT_MINUTE = 0
## we'll make a python-friendly structure
event_time = time.struct_time((EVENT_YEAR, EVENT_MONTH, EVENT_DAY,
                               EVENT_HOUR, EVENT_MINUTE, 0,  # we don't track seconds
                               -1, -1, False))  # we dont know day of week/year or DST

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))

## Initialize a requests session using the newer connection manager
## See https://adafruit-playground.com/u/justmobilize/pages/adafruit-connection-manager
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

## Create an instance of the Adafruit IO HTTP client
io = IO_HTTP(os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY"), requests)

## Setup RGB LEDs - comment out the DotStar import and setup if using NeoPixel
pixels_length = 1  # Set to the number of pixels in your strip (funhouse has 5)
pixels_brightness = 0.4  # Set to a value between 0.0 and 1.0
# Uncomment the following lines if you are using DotStar and update pins if necessary
dotstar_clock_pin = board.DOTSTAR_CLOCK
dotstar_data_pin = board.DOTSTAR_DATA
pixels = DotStar(dotstar_clock_pin, dotstar_data_pin, pixels_length, brightness=pixels_brightness)
## Uncomment the following lines if you are using NeoPixel and update pin if necessary
# neopixel_pin = board.NEOPIXEL
# pixels = neopixel.NeoPixel(neopixel_pin, pixels_length, brightness=pixels_brightness)

pixels.fill((0, 0, 0))  # Turn off all pixels

# Setup built-in display
display = board.DISPLAY
group = displayio.Group()
font = bitmap_font.load_font("/Helvetica-Bold-16.pcf")
blinka_bitmap = displayio.OnDiskBitmap("/cpday_tft.bmp")
blinka_grid = displayio.TileGrid(blinka_bitmap, pixel_shader=blinka_bitmap.pixel_shader)
scrolling_label = bitmap_label.Label(font, text=" ", y=display.height - 13)

group.append(blinka_grid)
group.append(scrolling_label)
display.root_group = group
display.auto_refresh = False

refresh_clock = ticks_ms()
refresh_timer = 3600 * 1000  # 1 hour
clock_clock = ticks_ms()
clock_timer = 1000
scroll_clock = ticks_ms()
scroll_timer = 50
first_run = True
finished = False
triggered = False

while True:
    # only query the online time once per hour (and on first run)
    if ticks_diff(ticks_ms(), refresh_clock) >= refresh_timer or first_run:
        try:
            print("Getting time from internet!")
            now = time.struct_time(io.receive_time(timezone))
            print(now)
            total_seconds = time.mktime(now)
            refresh_clock = ticks_add(refresh_clock, refresh_timer)
        except Exception as e: # pylint: disable=broad-except
            print("Some error occured, retrying via reset in 5seconds! -", e)
            time.sleep(5)
            microcontroller.reset()

    if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
        remaining = time.mktime(event_time) - total_seconds
        if remaining < 0:
            # calculate time since event
            remaining = abs(remaining)
            secs_remaining = -(remaining % 60)
            remaining //= 60
            mins_remaining = -(remaining % 60)
            remaining //= 60
            hours_remaining = -(remaining % 24)
            remaining //= 24
            days_remaining = -remaining
            finished = True
            if not first_run and days_remaining == 0:
                scrolling_label.text = "It's CircuitPython Day 2024! The snakiest day of the year!"
                # Flash on/off blinka colours (nice purple) each second
                if pixels[0] == (0, 0, 0):
                    pixels.fill((0x40, 0x00, 0x80))
                else:
                    pixels.fill((0, 0, 0))

                # Check for the moment of the event to trigger something (a NASA snake launch)
                if not triggered and (
                    hours_remaining==0 and mins_remaining == 0 and secs_remaining <= 0
                ):
                    # send a signal to an adafruit IO feed, where an Action is listening
                    print("Launch the snakes!")
                    triggered = True
                    io.send_data("cpday-countdown", "Launch the snakes!")
            else:
                pixels.fill((0, 0, 0))  # Turn off all pixels
        else:
            secs_remaining = remaining % 60
            remaining //= 60
            mins_remaining = remaining % 60
            remaining //= 60
            hours_remaining = remaining % 24
            remaining //= 24
            days_remaining = remaining
            pixels.fill((0, 0, 0))  # Turn off all pixels
        if not finished or (finished and days_remaining < 0):
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
    
    first_run = False
