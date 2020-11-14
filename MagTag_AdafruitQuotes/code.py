# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
from adafruit_magtag.magtag import MagTag

# Set up where we'll be fetching data from
DATA_SOURCE = "https://www.adafruit.com/api/quotes.php"
QUOTE_LOCATION = [0, 'text']
AUTHOR_LOCATION = [0, 'author']

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(QUOTE_LOCATION, AUTHOR_LOCATION),
)
magtag.network.connect()


def quote_transform(val):
    return val

# quote in bold text, with text wrapping
magtag.add_text(
    text_font="Arial-Bold-12.bdf",
    text_wrap=33,
    text_maxlen=160,
    text_position=(10, 15),
    line_spacing=0.75,
)

# author in italic text, no wrapping
magtag.add_text(
    text_font="Arial-Italic-12.bdf",
    text_position=(100, 110),
)

timestamp = None
while True:
    if not timestamp or (time.monotonic() - timestamp) > 60:  # once every 60 seconds...
        try:
            value = magtag.fetch()
            print("Response is", value)
        except (ValueError, RuntimeError) as e:
            print("Some error occured, retrying! -", e)
        timestamp = time.monotonic()
