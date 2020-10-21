import time
import board
import terminalio
import rtc
from adafruit_matrixportal.matrixportal import MatrixPortal

# --- Data Setup --- #
GUIDE_INDEX = 0
# Number of guides to fetch and display from the Adafruit Learning System
DISPLAY_NUM_GUIDES = 5
DATA_SOURCE = "https://learn.adafruit.com/api/guides/new.json?count=%d"%DISPLAY_NUM_GUIDES
TITLE_DATA_LOCATION = ["guides", GUIDE_INDEX, "guide", "title"]
TAGLINE_DATA_LOCATION = ["guides", GUIDE_INDEX, "guide", "tagline"]

# the current working directory (where this file is)
cwd = ("/" + __file__).rsplit("/", 1)[0]

matrixportal = MatrixPortal(
    url=DATA_SOURCE,
    json_path=TITLE_DATA_LOCATION,
    status_neopixel=board.NEOPIXEL,
    debug=True
)

print(matrixportal.graphics.display.height)
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 4),
    text_color=0xFFFFFF,
    scrolling=True,
)



refresh_time = None
while True:
    # Query local time every hour and on first run
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("Getting time from internet!")
            matrixportal.get_local_time()
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue
 
    the_time = time.localtime()
    print("Time: ", the_time)

    try:
        print("Index is ", GUIDE_INDEX)
        # Update title location index
        TITLE_DATA_LOCATION = ["guides", GUIDE_INDEX, "guide", "title"]
        matrixportal.json_path=TITLE_DATA_LOCATION
        value = matrixportal.fetch()
        print("Response is", value)
    except (ValueError, RuntimeError) as e:
        print("Some error occured, retrying! -", e)
    matrixportal.scroll_text(0.01)
    if GUIDE_INDEX == DISPLAY_NUM_GUIDES - 1: # reached the end of the guides
        # reset the index
        print("Reached the end of the new guides, resetting!")
        GUIDE_INDEX = 0
    GUIDE_INDEX += 1
    time.sleep(0.5)