# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython GitHub Stars viewer
"""

from os import getenv
import time
import ssl
import wifi
import socketpool
import displayio
import board
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
import adafruit_requests

# Get WiFi details, ensure these are setup in settings.toml
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

if None in [ssid, password]:
    raise RuntimeError(
        "WiFi settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "at a minimum."
    )

display = board.DISPLAY

# URL to fetch from
JSON_STARS_URL = "https://api.github.com/repos/adafruit/circuitpython"

# Set up background image and text
bitmap = displayio.OnDiskBitmap("/images/stars_background.bmp")
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
group = displayio.Group()
group.append(tile_grid)
font = bitmap_font.load_font("/fonts/Arial-Bold-36.bdf")
text_area = bitmap_label.Label(font, text="----", color=0xFFFFFF)
text_area.x = 135
text_area.y = 90
group.append(text_area)
display.root_group = group

# Connect to WiFi
print(f"Connecting to {ssid}")
wifi.radio.connect(ssid, password)
print(f"Connected to {ssid}!")
print(f"My IP address is {wifi.radio.ipv4_address}")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

while True:
    print("Fetching and parsing json from", JSON_STARS_URL)
    response = requests.get(JSON_STARS_URL)
    stars = response.json()["stargazers_count"]
    print("-" * 40)
    print("CircuitPython GitHub Stars", stars)
    print("-" * 40)
    text_area.text = str(stars)
    time.sleep(120)
