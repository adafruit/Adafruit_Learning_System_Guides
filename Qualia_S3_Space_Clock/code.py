# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark (Adafruit Industries) with OpenAI ChatGPT v4 Aug 3rd, 2023 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/63cbe4c6-007f-4934-a458-a9c8a521620e
# https://chat.openai.com/share/674c0f13-bc78-4d1e-be79-3bc777e29991

import time
from math import pi, cos, sin
import os
import ssl
import wifi
import socketpool
import adafruit_requests
import board
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
import vectorio
import displayio
from adafruit_io.adafruit_io import IO_HTTP
from jepler_udecimal import Decimal
import keypad
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_qualia.graphics import Graphics, Displays

key = keypad.Keys((board.A0,), value_when_pressed=False, pull=True)

timezone = -5

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

aio_username = os.getenv('ADAFRUIT_AIO_USERNAME')
aio_key = os.getenv('ADAFRUIT_AIO_KEY')

context = ssl.create_default_context()
print("socketpool")
pool = socketpool.SocketPool(wifi.radio)
print("requests")
requests = adafruit_requests.Session(pool, context)
print("io")
io = IO_HTTP(aio_username, aio_key, requests)

earth_bitmap = displayio.OnDiskBitmap("/earth.bmp")
mars_bitmap = displayio.OnDiskBitmap("/mars.bmp")

graphics = Graphics(Displays.ROUND40, default_bg=None, auto_refresh=True)

# Create a TileGrid to hold the bitmap
earth_grid = displayio.TileGrid(earth_bitmap, pixel_shader=earth_bitmap.pixel_shader)

# Create a Group to hold the TileGrid
earth_group = displayio.Group()

# Add the TileGrid to the Group
earth_group.append(earth_grid)

# Create a TileGrid to hold the bitmap
mars_grid = displayio.TileGrid(mars_bitmap, pixel_shader=mars_bitmap.pixel_shader)

def center(grid, bitmap):
    # Center the image
    grid.x -= (bitmap.width - graphics.display.width) // 2
    grid.y -= (bitmap.height - graphics.display.height) // 2

center(mars_grid, mars_bitmap)
center(earth_grid, earth_bitmap)
# Create a Group to hold the TileGrid
mars_group = displayio.Group()

# Add the TileGrid to the Group
mars_group.append(mars_grid)

graphics.display.root_group = mars_group

# Pointer using vectorio, first the hub
pointer_pal = displayio.Palette(4)
pointer_pal[0] = 0xff0000
pointer_pal[1] = 0x000000
pointer_pal[2] = 0x0000ff
pointer_pal[3] = 0xffffff
pointer_hub = vectorio.Circle(pixel_shader=pointer_pal, radius=16, x=0, y=0)
pointer_hub.x = graphics.display.width // 2
pointer_hub.y = graphics.display.height // 2

# Pointer itself
pw = 15    # pointer width
ph = 200   # pointer height
pointer_points = [(pw,0), (pw,-ph), (-pw,-ph), (-pw,0)]
pointer = vectorio.Polygon(pixel_shader=pointer_pal, points=pointer_points, x=0,y=0)
pointer.x = graphics.display.width // 2
pointer.y = graphics.display.height // 2
mars_group.append(pointer)
earth_group.append(pointer)
hw = 13    # pointer width
hh = 150   # pointer height
hour_points = [(hw,0), (hw,-hh), (-hw,-hh), (-hw,0)]
hour_hand = vectorio.Polygon(pixel_shader=pointer_pal, points=hour_points,
                             x=0, y=0, color_index=1)
hour_hand.x = graphics.display.width // 2
hour_hand.y = graphics.display.height // 2
mars_group.append(hour_hand)
earth_group.append(hour_hand)

def calculate_number_position(number, center_x, center_y, radius):
    angle = (360 / 12) * (number - 3)  # -3 adjusts the angle to start at 12 o'clock
    rad_angle = pi * angle / 180
    if number >=8:
        x = int(center_x + cos(rad_angle) * radius-40)
    x = int(center_x + cos(rad_angle) * radius)
    y = int(center_y + sin(rad_angle) * radius)
    return x, y

clock_face_numbers = {i: calculate_number_position(i, graphics.display.width // 2,
                        graphics.display.height // 2, 300) for i in range(1, 13)}

font_file = "/Roboto-Regular-47.pcf"

for i in range(1, 13):
    mars_c = vectorio.Circle(pixel_shader=pointer_pal, radius=30, x=clock_face_numbers[i][0]+12,
                             y=clock_face_numbers[i][1], color_index=1)
    earth_c = vectorio.Circle(pixel_shader=pointer_pal, radius=30, x=clock_face_numbers[i][0]+12,
                             y=clock_face_numbers[i][1], color_index=3)
    if i >= 10:
        mars_c.x = mars_c.x + 14
        earth_c.x = earth_c.x + 14
    mars_group.append(mars_c)
    earth_group.append(earth_c)
    text = str(i)
    font = bitmap_font.load_font(font_file)

    mars_text = label.Label(font, text=text, color=0xFFFFFF)
    earth_text = label.Label(font, text=text, color=0x000000)
    mars_text.x = clock_face_numbers[i][0]
    mars_text.y = clock_face_numbers[i][1]
    earth_text.x = clock_face_numbers[i][0]
    earth_text.y = clock_face_numbers[i][1]
    mars_group.append(mars_text)
    earth_group.append(earth_text)

mars_group.append(pointer_hub)
earth_group.append(pointer_hub)

def update_time():
    print("time")
    now = io.receive_time()
    return now

def convert_time(the_time):
    h = the_time[3]
    if h >= 12:
        h -= 12
        a = "PM"
    else:
        a = "AM"
    if h == 0:
        h = 12
    return h, a

def mars_time():
    dt = io.receive_time()
    print(dt)
    utc_offset = 3600 * abs(timezone)
    tai_offset = 37
    millis = time.mktime(dt)
    unix_timestamp = millis + utc_offset

    # Convert to MSD
    msd = (unix_timestamp + tai_offset) / Decimal("88775.244147") + Decimal("34127.2954262")
    print(msd)
    # Convert MSD to MTC
    mtc = (msd % 1) * 24
    mtc_hours = int(mtc)
    mtc_minutes = int((mtc * 60) % 60)
    mtc_seconds = int(((mtc * 3600)) % 60)

    print(f"Mars Time: {mtc_hours:02d}:{mtc_minutes:02d}:{mtc_seconds:02d}")
    return mtc_minutes, mtc_hours

def time_angle(m, the_hour):
    if m == 15:
        m = 16
    elif m == 45:
        m = 46
    # Adjusted angle calculation for minute hand
    theta_minute = 360 - (m / 60) * 360
    theta_hour = ((the_hour / 12) + (m / (12 * 60))) * 360
    # Calculate coordinates for minute hand (mirrored)
    minute_x = -int(cos(pi * (theta_minute - 90) / 180) * ph)
    minute_y = int(sin(pi * (theta_minute + 90) / 180) * ph)
    hour_x = int(cos(pi * (theta_hour - 90) / 180) * hh)
    hour_y = int(sin(pi * (theta_hour + 90) / 180) * hh)
    pointer.points = [(pw, 0), (minute_x + 2, -minute_y), (minute_x - 2, -minute_y), (-pw, 0)]
    hour_hand.points = [(hw, 0), (hour_x + 2, -hour_y), (hour_x - 2, -hour_y), (-hw, 0)]

clock_timer = 1 * 1000
clock_clock = ticks_ms()
display_timer = 10 * 1000
display_clock = ticks_ms()
mars_second = 88775
mars_clock = ticks_ms()
clock = update_time()
hour, am_pm = convert_time(clock)
tick = clock[5]
minute = clock[4]
mars_min, mars_hour = mars_time()
show_earth = True

time_angle(minute, hour)

while True:
    event = key.events.get()
    if event:
        if event.pressed:
            print("updating display")
            show_earth = not show_earth
    if show_earth:
        if pointer.color_index != 2:
            time_angle(minute, hour)
            graphics.display.root_group = earth_group
            pointer.color_index = 2
            pointer_hub.color_index = 2
    else:
        if pointer.color_index != 0:
            time_angle(mars_min, mars_hour)
            graphics.display.root_group = mars_group
            pointer.color_index = 0
            pointer_hub.color_index = 0
    if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
        tick += 1
        if tick > 59:
            tick = 0
            minute += 1
            if minute > 59:
                clock = update_time()
                hour, am_pm = convert_time(clock)
                tick = clock[5]
                minute = clock[4]
            print(f"{hour}:{minute:02} {am_pm}")
            mars_min, mars_hour = mars_time()
            if show_earth:
                time_angle(minute, hour)
            else:
                time_angle(mars_min, mars_hour)
        clock_clock = ticks_add(clock_clock, clock_timer)
