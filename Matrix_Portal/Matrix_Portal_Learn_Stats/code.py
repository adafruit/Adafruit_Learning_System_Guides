# SPDX-FileCopyrightText: 2020 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from random import randrange
import board
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal

# --- Data Setup --- #
# Number of guides to fetch and display from the Adafruit Learning System
DISPLAY_NUM_GUIDES = 5
# Data source URL
DATA_SOURCE = (
    "https://learn.adafruit.com/api/guides/new.json?count=%d" % DISPLAY_NUM_GUIDES
)
TITLE_DATA_LOCATION = ["guides"]

matrixportal = MatrixPortal(
    url=DATA_SOURCE,
    json_path=TITLE_DATA_LOCATION,
    status_neopixel=board.NEOPIXEL,
)

# --- Display Setup --- #

# Colors for guide name
colors = [0xFFA500, 0xFFFF00, 0x008000, 0x0000FF, 0x4B0082, 0xEE82EE]

# Delay for scrolling the text
SCROLL_DELAY = 0.03

FONT = "/IBMPlexMono-Medium-24_jep.bdf"

# Learn guide count (ID = 0)
matrixportal.add_text(
    text_font=FONT,
    text_position=(
        (matrixportal.graphics.display.width // 12) - 1,
        (matrixportal.graphics.display.height // 2) - 8,
    ),
    text_color=0x800000,
)
matrixportal.preload_font("0123456789")

# Learn guide title (ID = 1)
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 25),
    text_color=0x000080,
    scrolling=True,
)


def get_guide_info(index):
    """Parses JSON data returned by the DATA_SOURCE
    to obtain the ALS guide title and number of guides and
    sets the text labels.
    :param int index: Guide index to display

    """
    if index > DISPLAY_NUM_GUIDES:
        raise RuntimeError("Provided index may not be larger than DISPLAY_NUM_GUIDES.")
    print("Obtaining guide info for guide %d..." % index)

    # Traverse JSON data for title
    guide_count = matrixportal.network.json_traverse(als_data.json(), ["guide_count"])

    # Set guide count
    matrixportal.set_text(guide_count, 0)

    guides = matrixportal.network.json_traverse(als_data.json(), TITLE_DATA_LOCATION)
    guide_title = guides[index]["guide"]["title"]
    print("Guide Title", guide_title)

    # Select color for title text
    color_index = randrange(0, len(colors))

    # Set the title text color
    matrixportal.set_text_color(colors[color_index], 1)

    # Set the title text
    matrixportal.set_text(guide_title, 1)


refresh_time = None
guide_idx = 0
prv_hour = 0
while True:
    if (not refresh_time) or (time.monotonic() - refresh_time) > 900:
        try:
            print("obtaining time from adafruit.io server...")
            matrixportal.get_local_time()
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Unable to obtain time from Adafruit IO, retrying - ", e)
            continue

    if time.localtime()[3] != prv_hour:
        print("New Hour, fetching new data...")
        # Fetch and store guide info response
        als_data = matrixportal.network.fetch(DATA_SOURCE)
        prv_hour = time.localtime()[3]

    # Cycle through guides retrieved
    if guide_idx < DISPLAY_NUM_GUIDES:
        get_guide_info(guide_idx)

        # Scroll the scrollable text block
        matrixportal.scroll_text(SCROLL_DELAY)
        guide_idx += 1
    else:
        guide_idx = 0
    time.sleep(0.05)
