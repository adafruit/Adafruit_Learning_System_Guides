# Quote board matrix display
# uses AdafruitIO to serve up a quote text feed and color feed
# random quotes are displayed, updates periodically to look for new quotes
# avoids repeating the same quote twice in a row

import time
import random
import board
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal

# --- Display setup ---
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=True)

# Create a new label with the color and text selected
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(0, (matrixportal.graphics.display.height // 2) - 1),
    scrolling=True,
)

# Static 'Connecting' Text
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, (matrixportal.graphics.display.height // 2) - 1),
)

QUOTES_FEED = "sign-quotes.signtext"
COLORS_FEED = "sign-quotes.signcolor"
SCROLL_DELAY = 0.02
UPDATE_DELAY = 600

quotes = []
colors = []
last_color = None
last_quote = None


def update_data():
    print("Updating data from Adafruit IO")
    matrixportal.set_text("Connecting", 1)

    try:
        quotes_data = matrixportal.get_io_data(QUOTES_FEED)
        quotes.clear()
        for json_data in quotes_data:
            quotes.append(matrixportal.network.json_traverse(json_data, ["value"]))
        print(quotes)
    # pylint: disable=broad-except
    except Exception as error:
        print(error)

    try:
        color_data = matrixportal.get_io_data(COLORS_FEED)
        colors.clear()
        for json_data in color_data:
            colors.append(matrixportal.network.json_traverse(json_data, ["value"]))
        print(colors)
    # pylint: disable=broad-except
    except Exception as error:
        print(error)

    if not quotes or not colors:
        raise "Please add at least one quote and color to your feeds"
    matrixportal.set_text(" ", 1)


update_data()
last_update = time.monotonic()
matrixportal.set_text(" ", 1)
quote_index = None
color_index = None

while True:
    # Choose a random quote from quotes
    if len(quotes) > 1 and last_quote is not None:
        while quote_index == last_quote:
            quote_index = random.randrange(0, len(quotes))
    else:
        quote_index = random.randrange(0, len(quotes))
    last_quote = quote_index

    # Choose a random color from colors
    if len(colors) > 1 and last_color is not None:
        while color_index == last_color:
            color_index = random.randrange(0, len(colors))
    else:
        color_index = random.randrange(0, len(colors))
    last_color = color_index

    # Set the quote text
    matrixportal.set_text(quotes[quote_index])

    # Set the text color
    matrixportal.set_text_color(colors[color_index])

    # Scroll it
    matrixportal.scroll_text(SCROLL_DELAY)

    if time.monotonic() > last_update + UPDATE_DELAY:
        update_data()
        last_update = time.monotonic()
