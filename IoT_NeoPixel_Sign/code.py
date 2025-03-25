# SPDX-FileCopyrightText: 2020 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from os import getenv
import ssl
import board
import neopixel
import adafruit_requests
import socketpool
import wifi
from adafruit_io.adafruit_io import IO_HTTP
from adafruit_pixel_framebuf import PixelFramebuffer
# adafruit_circuitpython_adafruitio usage with native wifi networking

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

# Neopixel matrix configuration
PIXEL_PIN = board.IO6
PIXEL_WIDTH = 12
PIXEL_HEIGHT = 12

# LED matrix creation
PIXELS = neopixel.NeoPixel(
    PIXEL_PIN, PIXEL_WIDTH * PIXEL_HEIGHT, brightness=0.5, auto_write=False,
)

PIXEL_FRAMEBUF = PixelFramebuffer(
    PIXELS,
    PIXEL_WIDTH,
    PIXEL_HEIGHT,
    alternating=True,
    rotation=1,
    reverse_x=True
    )

# Adafruit.io feeds setup
QUOTE_FEED = "sign-quotes.signtext"
COLOR_FEED = "sign-quotes.signcolor"
CURRENT_TEXT = "Merry Christmas!"
CURRENT_COLOR = 0xFFFFFF

# Helper function to get updated data from Adafruit.io
def update_data():
    global CURRENT_TEXT, CURRENT_COLOR # pylint: disable=global-statement
    print("Updating data from Adafruit IO")
    try:
        quote_feed = IO.get_feed(QUOTE_FEED)
        quotes_data = IO.receive_data(quote_feed["key"])
        CURRENT_TEXT = quotes_data["value"]
        color_feed = IO.get_feed(COLOR_FEED)
        color_data = IO.receive_data(color_feed["key"])
        CURRENT_COLOR = int(color_data["value"][1:], 16)
    # pylint: disable=broad-except
    except Exception as error:
        print(error)


# Connect to WiFi
print(f"Connecting to {ssid}")
wifi.radio.connect(ssid, password)
print(f"Connected to {ssid}!")

# Setup Adafruit IO connection
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
IO = IO_HTTP(aio_username, aio_key, requests)


while True:
    update_data()
    print("Displaying", CURRENT_TEXT, "in", hex(CURRENT_COLOR))

    for i in range(12 * len(CURRENT_TEXT) + PIXEL_WIDTH):
        PIXEL_FRAMEBUF.fill(0x000000)
        PIXEL_FRAMEBUF.pixel(0, 0, 0x000000)
        PIXEL_FRAMEBUF.text(CURRENT_TEXT, PIXEL_WIDTH - i, 3, CURRENT_COLOR)
        PIXEL_FRAMEBUF.display()
