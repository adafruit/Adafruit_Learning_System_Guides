# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
Pull the current translated percent of CircuitPython
from Weblate and show it on the screen with text
and a progress bar.

Copy leaguespartan18.bdf and leaguespartan11.bdf
into fonts/ on your CIRCUITPY drive.
"""
import time
from adafruit_magtag.magtag import MagTag
from adafruit_progressbar import ProgressBar

# Set up where we'll be fetching data from
DATA_SOURCE = "https://hosted.weblate.org/api/projects/circuitpython/statistics/"
NAME_LOCATION = ["name"]
PERCENT_LOCATION = ["translated_percent"]
URL_LOCATION = ["url"]

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(NAME_LOCATION, PERCENT_LOCATION, URL_LOCATION),
)

magtag.network.connect()

# name
magtag.add_text(
    text_font="fonts/leaguespartan18.bdf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        20,
    ),
    text_anchor_point=(0.5, 0.5),
)

# percentage
def textpercent_transform(val):
    return "Translated: {}%".format(val)

magtag.add_text(
    text_font="fonts/leaguespartan18.bdf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        45,
    ),
    text_transform=textpercent_transform,
    text_anchor_point=(0.5, 0.5),
)

# URL
def texturl_transform(val):
    return val.replace("https://", "")  # remove known prefix!

magtag.add_text(
    text_font="fonts/leaguespartan11.bdf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        (magtag.graphics.display.height) - 8,
    ),
    text_transform=texturl_transform,
    text_anchor_point=(0.5, 1.0),
)

# set progress bar width and height relative to board's display
BAR_WIDTH = magtag.graphics.display.width - 80
BAR_HEIGHT = 30

BAR_X = magtag.graphics.display.width // 2 - BAR_WIDTH // 2
BAR_Y = 66

# Create a new progress_bar object at (x, y)
progress_bar = ProgressBar(
    BAR_X, BAR_Y, BAR_WIDTH, BAR_HEIGHT, 1.0, bar_color=0x999999, outline_color=0x000000
)

magtag.graphics.splash.append(progress_bar)

timestamp = None

try:
    value = magtag.fetch()
    print("Response is", value)
    progress_bar.progress = value[1] / 100.0
    magtag.refresh()
    magtag.exit_and_deep_sleep(24 * 60 * 60)  # one day
except (ValueError, RuntimeError) as e:
    print("Some error occurred, retrying! -", e)
    magtag.exit_and_deep_sleep(60)  # one minute
