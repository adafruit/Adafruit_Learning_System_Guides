# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-FileCopyrightText: 2024 Tyeth Gundry for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import wifi
import board
import displayio
import supervisor
import adafruit_connection_manager
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

## See TZ Identifier column at https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
## If you want to set the timezone, you can do so with the following code, which
## attempts to get timezone from settings.toml or defaults to New York
timezone = os.getenv("ADAFRUIT_AIO_TIMEZONE", "America/New_York")
## Or instead rely on automatic timezone detection based on IP Address
# timezone = None


## The time of the thing!
EVENT_YEAR = 2024
EVENT_MONTH = 8
EVENT_DAY = 16
EVENT_HOUR = 0
EVENT_MINUTE = 0
## we'll make a python-friendly structure
event_time = time.struct_time(
    (
        EVENT_YEAR,
        EVENT_MONTH,
        EVENT_DAY,
        EVENT_HOUR,
        EVENT_MINUTE,
        0,  # we don't track seconds
        -1,  # we dont know day of week/year or DST
        -1,
        False,
    )
)

print("Connecting to WiFi...")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)

## Initialize a requests session using the newer connection manager
## See https://adafruit-playground.com/u/justmobilize/pages/adafruit-connection-manager
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

## Create an instance of the Adafruit IO HTTP client
io = IO_HTTP(
    os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY"), requests
)

## Setup display and size appropriate assets
if board.board_id == "adafruit_qualia_s3_rgb666":
    # Display Initialisation for 3.2" Bar display (320x820)
    from qualia_bar_display_320x820 import setup_display
    display = setup_display()
    display.rotation = 90  # Rotate the display
    BITMAP_FILE = "/circuitpython_day_2024_820x260_16bit.bmp"
    FONT_FILE = "/font_free_mono_bold_48.pcf"
    FONT_Y_OFFSET = 30
    blinka_bitmap = displayio.OnDiskBitmap(BITMAP_FILE)
    PIXEL_SHADER = displayio.ColorConverter(
        input_colorspace=displayio.Colorspace.RGB565
    )
else:
    # Setup built-in display
    display = board.DISPLAY
    BITMAP_FILE = "/cpday_tft.bmp"
    FONT_FILE = "/Helvetica-Bold-16.pcf"
    FONT_Y_OFFSET = 13
    PIXEL_SHADER = displayio.ColorConverter()
    blinka_bitmap = displayio.OnDiskBitmap(BITMAP_FILE)
    PIXEL_SHADER = blinka_bitmap.pixel_shader
group = displayio.Group()
font = bitmap_font.load_font(FONT_FILE)
blinka_grid = displayio.TileGrid(blinka_bitmap, pixel_shader=blinka_bitmap.pixel_shader)
scrolling_label = bitmap_label.Label(font, text=" ", y=display.height - FONT_Y_OFFSET)

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
        except Exception as e:  # pylint: disable=broad-except
            print("Some error occured, retrying via supervisor.reload in 5seconds! -", e)
            time.sleep(5)
            # Normally calling microcontroller.reset() would be the way to go, but due to
            # a bug causing a reset into tinyUF2 bootloader mode we're instead going to
            # disconnect wifi to ensure fresh connection + use supervisor.reload()
            wifi.radio.enabled = False
            supervisor.reload()

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
                scrolling_label.text = (
                    "It's CircuitPython Day 2024! The snakiest day of the year!"
                )

                # Check for the moment of the event to trigger something (a NASA snake launch)
                if not triggered and (
                    hours_remaining == 0
                    and mins_remaining == 0
                    and secs_remaining <= 1
                    # Change at/after xx:yy:01 seconds so we've already updated the display
                ):
                    # send a signal to an adafruit IO feed, where an Action is listening
                    print("Launch the snakes! (sending message to Adafruit IO)")
                    triggered = True
                    io.send_data("cpday-countdown", "Launch the snakes!")

        else:
            # calculate time until event
            secs_remaining = remaining % 60
            remaining //= 60
            mins_remaining = remaining % 60
            remaining //= 60
            hours_remaining = remaining % 24
            remaining //= 24
            days_remaining = remaining
        if not finished or (finished and days_remaining < 0):
            # Add 1 to negative days_remaining to count from end of day instead of start
            if days_remaining < 0:
                days_remaining += 1
            # Update the display with current countdown value
            scrolling_label.text = (
                f"{days_remaining} DAYS, {hours_remaining} HOURS,"
                + f"{mins_remaining} MINUTES & {secs_remaining} SECONDS"
            )

        total_seconds += 1
        clock_clock = ticks_add(clock_clock, clock_timer)
    if ticks_diff(ticks_ms(), scroll_clock) >= scroll_timer:
        scrolling_label.x -= 1
        if scrolling_label.x < -(scrolling_label.width + 5):
            scrolling_label.x = display.width + 2
        display.refresh()
        scroll_clock = ticks_add(scroll_clock, scroll_timer)

    first_run = False
