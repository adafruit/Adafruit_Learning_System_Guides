# MagTag Shower Thoughts
# Be sure to put WiFi access point info in secrets.py file to connect

import time
import random
from adafruit_magtag.magtag import MagTag


# Set up where we'll be fetching data from
DATA_SOURCE = "https://www.reddit.com/r/showerthoughts/hot.json?limit=10"
quote_num = random.randint(0, 9)  # we get 10 possibilities, pick one of them
QUOTE_LOCATION = ["data", "children", quote_num, "data", "title"]
AUTHOR_LOCATION = ["data", "children", quote_num, "data", "author"]

# in seconds, we can refresh about 100 times on a battery
TIME_BETWEEN_REFRESHES = 1 * 60 * 60  # one hour delay

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(QUOTE_LOCATION, AUTHOR_LOCATION),
)

magtag.graphics.set_background("/bmps/magtag_shower_bg.bmp")

# quote in bold text, with text wrapping
magtag.add_text(
    text_font="/fonts/Arial-Bold-12.pcf",
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
    text_position=(magtag.graphics.display.width // 2, 118),
    text_anchor_point=(0.5, 0.5),  # left justify this line
)

try:
    magtag.network.connect()
    value = magtag.fetch()
    print("Response is", value)
except (ValueError, RuntimeError) as e:
    magtag.set_text(e)
    print("Some error occured, retrying! -", e)

# wait 2 seconds for display to complete
time.sleep(2)
magtag.exit_and_deep_sleep(TIME_BETWEEN_REFRESHES)
