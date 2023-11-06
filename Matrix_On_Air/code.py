# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# ON AIR sign for YouTube livestreaming
# Runs on Airlift Metro M4 with 64x32 RGB Matrix display & shield

import time
import board
import displayio
import adafruit_display_text.label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.polygon import Polygon
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set up where we'll be fetching data from
# Adafruit YouTube channel:
CHANNEL_ID = (
    "UCpOlOeQjj7EsVnDh3zuCgsA"  # this isn't a secret but you have to look it up
)

DATA_SOURCE = (
    "https://www.googleapis.com/youtube/v3/search?part=snippet&channelId="
    + CHANNEL_ID
    + "&type=video&eventType=live&key="
    + secrets["youtube_token"]
)
DATA_LOCATION1 = ["items"]

# Number of seconds between checking, if this is too quick the query quota will run out
UPDATE_DELAY = 300

# Times are in 24-hour format for simplification
OPERATING_TIME_START = "12:00"  # what hour to start checking
OPERATING_TIME_END = "19:00"  # what hour to stop checking

# --- Display setup ---
matrix = Matrix()
display = matrix.display
network = Network(status_neopixel=board.NEOPIXEL, debug=False)

# --- Drawing setup ---
# Create a Group
group = displayio.Group()
# Create a bitmap object
bitmap = displayio.Bitmap(64, 32, 2)  # width, height, bit depth
# Create a color palette
color = displayio.Palette(4)
color[0] = 0x000000  # black
color[1] = 0xFF0000  # red
color[2] = 0x444444  # dim white
color[3] = 0xDD8000  # gold
# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=color)
# Add the TileGrid to the Group
group.append(tile_grid)

# draw the frame for startup
rect1 = Rect(0, 0, 2, 32, fill=color[2])
rect2 = Rect(62, 0, 2, 32, fill=color[2])
rect3 = Rect(2, 0, 9, 2, fill=color[0])
rect4 = Rect(53, 0, 9, 2, fill=color[0])
rect5 = Rect(2, 30, 12, 2, fill=color[0])
rect6 = Rect(50, 30, 12, 2, fill=color[0])

group.append(rect1)
group.append(rect2)
group.append(rect3)
group.append(rect4)
group.append(rect5)
group.append(rect6)


def redraw_frame():  # to adjust spacing at bottom later
    rect3.fill = color[2]
    rect4.fill = color[2]
    rect5.fill = color[2]
    rect6.fill = color[2]


# draw the wings w polygon shapes
wing_polys = []

wing_polys.append(Polygon([(3, 3), (9, 3), (9, 4), (4, 4)], outline=color[1]))
wing_polys.append(Polygon([(5, 6), (9, 6), (9, 7), (6, 7)], outline=color[1]))
wing_polys.append(Polygon([(7, 9), (9, 9), (9, 10), (8, 10)], outline=color[1]))
wing_polys.append(Polygon([(54, 3), (60, 3), (59, 4), (54, 4)], outline=color[1]))
wing_polys.append(Polygon([(54, 6), (58, 6), (57, 7), (54, 7)], outline=color[1]))
wing_polys.append(Polygon([(54, 9), (56, 9), (55, 10), (54, 10)], outline=color[1]))

for wing_poly in wing_polys:
    group.append(wing_poly)


def redraw_wings(index):  # to change colors
    for wing in wing_polys:
        wing.outline = color[index]


# --- Content Setup ---
deco_font = bitmap_font.load_font("/BellotaText-Bold-21.bdf")

# Create two lines of text. Besides changing the text, you can also
# customize the color and font (using Adafruit_CircuitPython_Bitmap_Font).

# text positions
on_x = 15
on_y = 9
off_x = 12
off_y = 9
air_x = 15
air_y = 25


text_line1 = adafruit_display_text.label.Label(deco_font, color=color[3], text="OFF")
text_line1.x = off_x
text_line1.y = off_y

text_line2 = adafruit_display_text.label.Label(deco_font, color=color[1], text="AIR")
text_line2.x = air_x
text_line2.y = air_y

# Put each line of text into the Group
group.append(text_line1)
group.append(text_line2)


def startup_text():
    text_line1.text = "ADA"
    text_line1.x = 10
    text_line1.color = color[2]
    text_line2.text = "FRUIT"
    text_line2.x = 2
    text_line2.color = color[2]
    redraw_wings(0)
    display.root_group = group


startup_text()  # display the startup text


def update_text(state):
    if state:  # if switch is on, text is "ON" at startup
        text_line1.text = "ON"
        text_line1.x = on_x
        text_line1.color = color[1]
        text_line2.text = "AIR"
        text_line2.x = air_x
        text_line2.color = color[1]
        redraw_wings(1)
        redraw_frame()
        display.root_group = group
    else:  # else, text if "OFF" at startup
        text_line1.text = "OFF"
        text_line1.x = off_x
        text_line1.color = color[3]
        text_line2.text = "AIR"
        text_line2.x = air_x
        text_line2.color = color[3]
        redraw_wings(3)
        redraw_frame()
        display.root_group = group


def get_status():
    """
    Get the status whether we are on/off air within operating hours
    If outside of hours, return False
    """
    # Get the time values we need
    now = time.localtime()
    start_hour, start_minute = OPERATING_TIME_START.split(":")
    end_hour, end_minute = OPERATING_TIME_END.split(":")

    # Convert time into a float for easy calculations
    start_time = int(start_hour) + (int(start_minute) / 60)
    end_time = int(end_hour) + (int(end_minute) / 60)
    current_time = now[3] + (now[4] / 60)

    if start_time <= current_time < end_time:
        try:
            on_air = network.fetch_data(DATA_SOURCE, json_path=(DATA_LOCATION1,))
            if len(on_air) > 0:
                return True
        except RuntimeError:
            return False

    return False


# Synchronize Board's clock to Internet
network.get_local_time()
mode_state = get_status()
update_text(mode_state)
last_check = None


while True:
    if last_check is None or time.monotonic() > last_check + UPDATE_DELAY:
        try:
            status = get_status()
            if status:
                if mode_state == 0:  # state has changed, toggle it
                    update_text(1)
                    mode_state = 1
            else:
                if mode_state == 1:
                    update_text(0)
                    mode_state = 0
            print("On Air:", status)
            last_check = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
