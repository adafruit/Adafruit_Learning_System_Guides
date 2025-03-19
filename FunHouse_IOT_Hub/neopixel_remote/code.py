# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
NeoPixel remote control using PyPortal Titano.

Colors used are taken from Adafruit_CircuitPython_LED_Animation library
"""

from os import getenv
import time
import math
import board
import busio
from digitalio import DigitalInOut
import displayio
from adafruit_display_shapes.rect import Rect
import adafruit_imageload
import adafruit_touchscreen

# ESP32 SPI
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager

# Import NeoPixel Library
import neopixel

# Import Adafruit IO HTTP Client
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

if None in [ssid, password, aio_username, aio_key]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME' and 'ADAFRUIT_AIO_KEY' at a minimum."
    )

ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((5200, 59000), (5800, 57000)),
    size=(480, 320),
)
RED = 0xFF0000
YELLOW = 0xFF9600
ORANGE = 0xFF2800
GREEN = 0x00FF00
TEAL = 0x00FF78
CYAN = 0x00FFFF
BLUE = 0x0000FF
PURPLE = 0xB400FF
MAGENTA = 0xFF0014
WHITE = 0xFFFFFF
BLACK = 0x000000

GOLD = 0xFFDE1E
PINK = 0xF15AFF
AQUA = 0x32FFFF
JADE = 0x00FF28
AMBER = 0xFF6400

colors = [
    None,
    None,
    GREEN,
    PURPLE,
    GOLD,
    AMBER,
    None,
    None,
    ORANGE,
    BLUE,
    BLACK,
    JADE,
    None,
    None,
    YELLOW,
    CYAN,
    WHITE,
    AQUA,
    None,
    None,
    RED,
    TEAL,
    MAGENTA,
    PINK,
]

print(colors)
group = displayio.Group()
# pyportal_setter.xcf has been included so you can edit the colors used in GIMP, just make sure to
# change them here as well
background, palette = adafruit_imageload.load(
    "bmps/pyportal_setter.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
tile_grid = displayio.TileGrid(background, pixel_shader=palette)
group.append(tile_grid)
rect = Rect(0, 0, 160, 320, fill=0x000000)
group.append(rect)
print(len(group))

# PyPortal ESP32 Setup
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.WiFiManager(esp, ssid, password, status_pixel=status_pixel)

# Create an instance of the Adafruit IO HTTP client
io = IO_HTTP(aio_username, aio_key, wifi)

try:
    # Get the 'temperature' feed from Adafruit IO
    neopixel_feed = io.get_feed("neopixel")
except AdafruitIO_RequestError:
    neopixel_feed = io.create_new_feed("neopixel")

board.DISPLAY.root_group = group
print("ready")
last_color = 257
last_index = 0
while True:
    p = ts.touch_point
    if p:
        x = math.floor(p[0] / 80)
        y = math.floor(p[1] / 80)
        index = 6 * y + x
        # Used to prevent the touchscreen sending incorrect results
        if last_index == index:
            color = colors[index]
            if colors[index] is not None:
                group[1].fill = color
                if last_color != color:
                    color_str = "#{:06x}".format(color)
                    print(color_str)
                    io.send_data(neopixel_feed["key"], color_str)
                    last_color = color
        last_index = index
    time.sleep(0.1)
