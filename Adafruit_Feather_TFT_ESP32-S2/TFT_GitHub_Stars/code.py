# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython GitHub Stars viewer
"""
import time
import ssl
import wifi
import socketpool
import displayio
import board
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
import adafruit_requests

# Get WiFi details secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

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
text_area.x = 125
text_area.y = 90
group.append(text_area)
display.show(group)

# Connect to WiFi
print("Connecting to %s"%secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!"%secrets["ssid"])
print("My IP address is", wifi.radio.ipv4_address)

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
