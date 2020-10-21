import time
import board
import rtc
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal

# --- Data Setup --- #
GUIDE_INDEX = 0
# Number of guides to fetch and display from the Adafruit Learning System
DISPLAY_NUM_GUIDES = 5
DATA_SOURCE = "https://learn.adafruit.com/api/guides/new.json?count=%d"%DISPLAY_NUM_GUIDES
TITLE_DATA_LOCATION = ["guides"]
TAGLINE_DATA_LOCATION = ["guides", GUIDE_INDEX, "guide", "tagline"]

# the current working directory (where this file is)
cwd = ("/" + __file__).rsplit("/", 1)[0]

matrixportal = MatrixPortal(
    url=DATA_SOURCE,
    json_path=TITLE_DATA_LOCATION,
    status_neopixel=board.NEOPIXEL,
    debug=True
)

# --- Display Setup --- #
# Delay for scrolling the text
SCROLL_DELAY = 0.03
# id = 0, title
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=((matrixportal.graphics.display.width // 3) - 1, (matrixportal.graphics.display.height // 3) - 1),
    text_color=0x800000,
    text_scale = 2
)

# id = 1, author
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 25),
    text_color=0x000080,
    scrolling = True
)

def get_guide_info(index):
    if index > DISPLAY_NUM_GUIDES:
        raise RuntimeError("Provided index may not be larger than DISPLAY_NUM_GUIDES.")
    print("Obtaining guide info for guide %d..."%index)
    # Traverse JSON data for title
    guide_count = matrixportal.network.json_traverse(als_data.json(), ["guide_count"])
    guides = matrixportal.network.json_traverse(als_data.json(), TITLE_DATA_LOCATION)
    guide_title = guides[index]["guide"]["title"]
    print("Guide Title", guide_title)
    return (guide_count, guide_title)


idx = 0
prv_hour = 0
refresh_time = None
while True:

    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("obtaining time from adafruit.io server...")
            matrixportal.get_local_time()
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Retrying! - ", e)
            continue

    if time.localtime()[3] != prv_hour:
        # Fetch and store guide info response
        als_data = matrixportal.network.fetch(DATA_SOURCE)
        prv_hour = time.localtime()[3]

    # Cycle through guides retrieved
    if idx < DISPLAY_NUM_GUIDES:
        guide_count, guide_title = get_guide_info(idx)
        # Set title text
        matrixportal.set_text(guide_count, 0)

        # Set author text
        matrixportal.set_text(guide_title, 1)

        # Scroll the scrollable text blocks
        matrixportal.scroll_text(SCROLL_DELAY)
        idx += 1
    else:
        idx = 0
    time.sleep(0.5)
