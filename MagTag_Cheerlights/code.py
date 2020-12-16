# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
import board
from adafruit_magtag.magtag import MagTag
import neopixel

external_pixels = neopixel.NeoPixel(board.D10, 30, brightness=0.3)

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.thingspeak.com/channels/1417/field/2/last.json"
COLOR_LOCATION = ['field2']
DATE_LOCATION = ['created_at']

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(COLOR_LOCATION, DATE_LOCATION),
)
magtag.network.connect()

# Color
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 15),
    text_transform=lambda x: "New Color {}".format(x),
)
# datestamp
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_position=(10, 35),
    text_transform=lambda x: "Updated on: {}".format(x),
)

timestamp = None
while True:
    if not timestamp or ((time.monotonic() - timestamp) > 10):  # once every 10 seconds...
        try:
            value = magtag.fetch()
            print("Response is", value)
            magtag.peripherals.neopixel_disable = False
            color = int(value[0][1:], 16)
            magtag.peripherals.neopixels.fill(color)
            external_pixels.fill(color)
            timestamp = time.monotonic()
        except (ValueError, RuntimeError) as e:
            print("Some error occured, retrying! -", e)
    time.sleep(1)
