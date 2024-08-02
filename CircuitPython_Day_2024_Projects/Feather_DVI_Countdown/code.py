# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import displayio
import picodvi
import board
import framebufferio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_pcf8523.pcf8523 import PCF8523
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

EVENT_YEAR = 2024
EVENT_MONTH = 8
EVENT_DAY = 16
EVENT_HOUR = 0
EVENT_MINUTE = 0
# we'll make a python-friendly structure
event_time = time.struct_time((EVENT_YEAR, EVENT_MONTH, EVENT_DAY,
                               EVENT_HOUR, EVENT_MINUTE, 0,  # we don't track seconds
                               -1, -1, False))  # we dont know day of week/year or DST

# check for DVI Feather with built-in display
if 'DISPLAY' in dir(board):
    display = board.DISPLAY

# check for DVI feather without built-in display
elif 'CKP' in dir(board):
    displayio.release_displays()
    fb = picodvi.Framebuffer(320, 240,
        clk_dp=board.CKP, clk_dn=board.CKN,
        red_dp=board.D0P, red_dn=board.D0N,
        green_dp=board.D1P, green_dn=board.D1N,
        blue_dp=board.D2P, blue_dn=board.D2N,
        color_depth=8)
    display = framebufferio.FramebufferDisplay(fb)
# otherwise assume Pico
else:
    displayio.release_displays()
    fb = picodvi.Framebuffer(320, 240,
        clk_dp=board.GP12, clk_dn=board.GP13,
        red_dp=board.GP10, red_dn=board.GP11,
        green_dp=board.GP8, green_dn=board.GP9,
        blue_dp=board.GP6, blue_dn=board.GP7,
        color_depth=8)
    display = framebufferio.FramebufferDisplay(fb)

i2c = board.I2C()
rtc = PCF8523(i2c)
set_clock = False
if set_clock:
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2024,  8,   1,   16,  26,  00,    0,   -1,    -1))
    print("Setting time to:", t)
    rtc.datetime = t
    print()
#  variable to hold RTC datetime
t = rtc.datetime

pink = 0xf1078e
purple = 0x673192
aqua = 0x19beed
group = displayio.Group()
my_font = bitmap_font.load_font("/Helvetica-Bold-16.pcf")
clock_area = label.Label(my_font, text="00:00:00:00", color=pink)
clock_area.anchor_point = (0.0, 1.0)
clock_area.anchored_position = (display.width / 2 - clock_area.width / 2,
                                display.height - (clock_area.height + 20))
text1 = label.Label(my_font, text="Starting In:", color=aqua)
text1.anchor_point = (0.0, 0.0)
text1.anchored_position = (display.width / 2 - text1.width / 2,
                           display.height - (clock_area.height + text1.height + 35))

blinka_bitmap = displayio.OnDiskBitmap("/cpday_dvi.bmp")
blinka_grid = displayio.TileGrid(blinka_bitmap, pixel_shader=blinka_bitmap.pixel_shader)
group.append(blinka_grid)
group.append(text1)
group.append(clock_area)
display.root_group = group

clock_clock = ticks_ms()
clock_timer = 1000
while True:
    if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
        t = rtc.datetime
        remaining = time.mktime(event_time) - time.mktime(t)
        secs_remaining = remaining % 60
        remaining //= 60
        mins_remaining = remaining % 60
        remaining //= 60
        hours_remaining = remaining % 24
        remaining //= 24
        days_remaining = remaining
        clock_area.text = (f"{days_remaining:0>2}:{hours_remaining:0>2}" +
                          f":{mins_remaining:0>2}:{secs_remaining:0>2}")
        clock_clock = ticks_add(clock_clock, clock_timer)
