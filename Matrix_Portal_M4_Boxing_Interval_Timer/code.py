# SPDX-FileCopyrightText: 2023 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import displayio
import terminalio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.matrix import Matrix

# set the timer length
TIMER_LENGTH = 180  # 3 minutes

BLINK = True
DEBUG = False

# --- Display setup ---
matrix = Matrix()
display = matrix.display

# --- Drawing setup ---
group = displayio.Group()  # Create a Group
bitmap = displayio.Bitmap(64, 32, 2)  # Create a bitmap object,width, height, bit depth
color = displayio.Palette(4)  # Create a color palette
color[0] = 0x000000  # black background
color[1] = 0xFF0000  # red
color[2] = 0xFF8C00  # yellow
color[3] = 0x3DEB34  # green

# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=color)
group.append(tile_grid)  # Add the TileGrid to the Group
display.show(group)

if not DEBUG:
    font = bitmap_font.load_font("/IBMPlexMono-Medium-24_jep.bdf")
else:
    font = terminalio.FONT

clock_label = Label(font)

def update_time(remaining_time):
    now = time.localtime()  # Get the time values we need

    # calculate remaining time in seconds
    seconds = remaining_time % 60
    minutes = remaining_time // 60

    if BLINK:
        colon = ":" if now[5] % 2 else " "
    else:
        colon = ":"

    clock_label.text = "{minutes:02d}{colon}{seconds:02d}".format(
        minutes=minutes, seconds=seconds, colon=colon
    )

    if remaining_time < 60:
        clock_label.color = color[1]
    elif remaining_time < 90:
        clock_label.color = color[2]
    elif remaining_time > 90:
        clock_label.color = color[3]

    bbx, bby, bbwidth, bbh = clock_label.bounding_box
    # Center the label
    clock_label.x = round(display.width / 2 - bbwidth / 2)
    clock_label.y = display.height // 2
    if DEBUG:
        print("Label bounding box: {},{},{},{}".format(bbx, bby, bbwidth, bbh))
        print("Label x: {} y: {}".format(clock_label.x, clock_label.y))

    # decrement remaining time
    remaining_time -= 1
    if remaining_time < 0:
        remaining_time = TIMER_LENGTH

    return remaining_time

def main():
    remaining_time = TIMER_LENGTH
    update_time(remaining_time)
    group.append(clock_label)

    while True:
        remaining_time = update_time(remaining_time)
        time.sleep(1)

if __name__ == "__main__":
    main()
