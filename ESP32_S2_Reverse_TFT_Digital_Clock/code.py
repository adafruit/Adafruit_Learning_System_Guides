# SPDX-FileCopyrightText: 2023 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import os
import ssl
import time
import wifi
import board
import displayio
import terminalio
import socketpool
import adafruit_requests
from adafruit_display_text import bitmap_label

# Initialize Wi-Fi connection
try:
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
    )
    print("Connected to %s!" % os.getenv("CIRCUITPY_WIFI_SSID"))
except Exception as e:  # pylint: disable=broad-except
    print(
        "Failed to connect to WiFi. Error:", e, "\nBoard will hard reset in 30 seconds."
    )

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Set up the URL for fetching time data
DATA_SOURCE = "http://worldtimeapi.org/api/timezone/" + os.getenv("TIMEZONE")

# Set up display a default image
display = board.DISPLAY
default_bitmap = displayio.OnDiskBitmap("/images/blanka-chan.bmp")
default_tile_grid = displayio.TileGrid(default_bitmap, pixel_shader=default_bitmap.pixel_shader)

group = displayio.Group()
group.append(default_tile_grid)

# Create label for displaying time
time_label = bitmap_label.Label(terminalio.FONT, scale=5)
time_label.anchor_point = (0.2, 0.5)
time_label.anchored_position = (display.width // 2, display.height // 2)

# Create main group to hold all display groups
main_group = displayio.Group()
main_group.append(group)
main_group.append(time_label)
# Show the main group on the display
display.show(main_group)

current_background_image = "/images/blanka-chan.bmp"

def set_background_image(filename):
    global current_background_image  # pylint: disable=global-statement
    tile_bitmap = displayio.OnDiskBitmap(filename)
    new_tile_grid = displayio.TileGrid(tile_bitmap, pixel_shader=tile_bitmap.pixel_shader)
    group[0] = new_tile_grid
    current_background_image = filename

def parse_time(datetime_str):
    # Extract the time part from the datetime string
    time_str = datetime_str.split("T")[1].split(".")[0]
    hour, minute, _ = map(int, time_str.split(":"))

    # Convert 24-hour format to 12-hour format and determine AM/PM
    period = "AM"
    if hour >= 12:
        period = "PM"
        if hour > 12:
            hour -= 12
    elif hour == 0:
        hour = 12

    return hour, minute, period

while True:
    # Fetch time data from WorldTimeAPI
    response = requests.get(DATA_SOURCE)
    data = response.json()

    # Parse the time from the datetime string
    current_hour, current_minute, current_period = parse_time(data["datetime"])

    # Display the time
    time_label.text = " {:2}{}\n  :{:02}".format(current_hour, current_period, current_minute)

    # Switch between two images
    if current_background_image == "/images/blanka-chan.bmp":
        set_background_image("/images/blanka-chan-charged.bmp")
    else:
        set_background_image("/images/blanka-chan.bmp")

    time.sleep(5)
