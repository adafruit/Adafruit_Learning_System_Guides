# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import wifi
import microcontroller
import board
import neopixel
import adafruit_connection_manager
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

timezone = "America/New_York"
color = 0xFF00FF
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

print("Connecting to WiFi...")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)
io = IO_HTTP(
    os.getenv("AIO_USERNAME"), os.getenv("AIO_KEY"), requests
)

pixel_pin = board.SCL1
pixel_num = 16
pixels = neopixel.NeoPixel(pixel_pin, n = pixel_num, brightness=1, auto_write=True)
pixel_length = 0
last_length = -1

refresh_clock = ticks_ms()
refresh_timer = 3600 * 1000  # 1 hour
first_run = True
finished = False

while True:
    if not finished:
        if ticks_diff(ticks_ms(), refresh_clock) >= refresh_timer or first_run:
            try:
                print("Getting time from internet!")
                now = time.struct_time(io.receive_time(timezone))
                print(now)
                total_seconds = time.mktime(now)
                remaining = time.mktime(event_time) - total_seconds
                if remaining < 0:
                    pixel_length = pixel_num + 1
                    finished = True
                else:
                    if now.tm_mon == EVENT_MONTH:
                        pixel_length = now.tm_mday % (pixel_num + 1)
                refresh_clock = ticks_add(refresh_clock, refresh_timer)
            except Exception as e:  # pylint: disable=broad-except
                print("Some error occured, retrying via reset in 15 seconds! - ", e)
                time.sleep(15)
                microcontroller.reset()
    if last_length != pixel_length:
        if not pixel_length:
            pixels.fill(0x000000)
        else:
            for i in range(pixel_length):
                pixels[i] = color
        last_length = pixel_length
    first_run = False
