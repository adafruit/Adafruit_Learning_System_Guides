# MagTag Quote Board
# Displays Quotes from the Adafruit quotes server
# Be sure to put WiFi access point info in secrets.py file to connect

import time
from adafruit_magtag.magtag import MagTag

# Set up where we'll be fetching data from
DATA_SOURCE = "https://www.adafruit.com/api/quotes.php"
QUOTE_LOCATION = [0, "text"]
AUTHOR_LOCATION = [0, "author"]
# in seconds, we can refresh about 100 times on a battery
TIME_BETWEEN_REFRESHES = 1 * 60 * 60  # one hour delay

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(QUOTE_LOCATION, AUTHOR_LOCATION),
)

magtag.graphics.set_background("/bmps/magtag_quotes_bg.bmp")

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
    text_position=(magtag.graphics.display.width // 2, 118),
    text_anchor_point=(0.5, 0.5),  # center it in the nice scrolly thing
)

# OK now we're ready to connect to the network, fetch data and update screen!
try:
    magtag.network.connect()
    value = magtag.fetch()
    print("Response is", value)
except (ValueError, RuntimeError) as e:
    magtag.set_text(e)
    print("Some error occured, retrying later -", e)
# wait 2 seconds for display to complete
time.sleep(2)
magtag.exit_and_deep_sleep(TIME_BETWEEN_REFRESHES)
