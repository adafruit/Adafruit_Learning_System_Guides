# MagTag Shower Thoughts
# Be sure to put WiFi access point info in secrets.py file to connect

import time
from adafruit_magtag.magtag import MagTag


# Set up where we'll be fetching data from
DATA_SOURCE = "https://www.reddit.com/r/showerthoughts/hot.json?limit=10"
quote_num = 0
QUOTE_LOCATION = ["data", "children", quote_num, "data", "title"]
AUTHOR_LOCATION = ["data", "children", quote_num, "data", "author"]
AUTHOR_LOCATION = ["data", "children", 0, "data", "author"]

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(QUOTE_LOCATION, AUTHOR_LOCATION),
    debug = False,
)
magtag.graphics.set_background("/bmps/magtag_shower_bg.bmp")
magtag.refresh()

magtag.network.connect()

# quote in bold text, with text wrapping
magtag.add_text(
    text_font="/fonts/Arial-Bold-12.bdf",
    text_wrap=28,
    text_maxlen=120,
    text_position=(
        (magtag.graphics.display.width // 2),
        (magtag.graphics.display.height // 2) - 10,
    ),
    line_spacing=0.75,
    text_anchor_point=(0.5, 0.5),  # center the text on x & y
)

# author in italic text, no wrapping
magtag.add_text(
    text_font="/fonts/Arial-Italic-12.bdf",
    text_position=(20, 118),
    text_anchor_point=(0.0, 0.5),  # left justify this line
)

timestamp = None

while True:
    if not timestamp or (time.monotonic() - timestamp) > 60:  # new one each minute
        try:
            quote_num = (quote_num + 1) % 10
            QUOTE_LOCATION = ["data", "children", quote_num, "data", "title"]
            AUTHOR_LOCATION = ["data", "children", quote_num, "data", "author"]
            magtag.json_path = (QUOTE_LOCATION, AUTHOR_LOCATION)
            value = magtag.fetch()
            print("Response is", value)
        except (ValueError, RuntimeError) as e:
            print("Some error occured, retrying! -", e)
        timestamp = time.monotonic()
        print(timestamp)
