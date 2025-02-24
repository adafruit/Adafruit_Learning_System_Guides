# SPDX-FileCopyrightText: Copyright (c) 2024 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import terminalio
import displayio
from adafruit_matrixportal.matrixportal import MatrixPortal
from adafruit_display_text import label

# --- Display setup ---
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=True, width=64, height=64)
# Use the built-in font
font = terminalio.FONT
# Define colors
ORANGE = 0xFFA500
WHITE = 0xFFFFFF
RED = 0xFF0000

# Create a Group to hold all the text areas and the heart
group = displayio.Group()

# Create a small heart bitmap
heart_bitmap = displayio.Bitmap(7, 7, 2)
heart_palette = displayio.Palette(2)
heart_palette[0] = 0x000000  # Black (transparent)
heart_palette[1] = RED  # Red heart

# Draw the heart
heart_pixels = [
    0,1,1,0,1,1,0,
    1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,
    0,1,1,1,1,1,0,
    0,0,1,1,1,0,0,
    0,0,0,1,0,0,0,
]
for heart_idx, pixel in enumerate(heart_pixels):
    heart_bitmap[heart_idx % 7, heart_idx // 7] = pixel

# Create a TileGrid using the heart bitmap and palette
heart_tile = displayio.TileGrid(heart_bitmap, pixel_shader=heart_palette, x=56, y=1)
group.append(heart_tile)

# Add text labels for titles and values
for label_idx in range(3):
    # Title
    title_label = label.Label(font, text="", color=ORANGE, x=2, y=7 + label_idx*21)
    group.append(title_label)
    # Value
    value_label = label.Label(font, text="", color=WHITE, x=2, y=17 + label_idx*21)
    group.append(value_label)

# Add the group to the display
matrixportal.display.show(group)

# Define feed keys for your data
TITLES = ["STEPS", "WORKOUTS", "MILES"]
VALUE_FEEDS = ["stepcount", "numofworkouts", "distance"]
UPDATE_DELAY = 1800  # Update every 30 minutes

def get_feed_data(feed_key):
    try:
        data = matrixportal.get_io_data(feed_key)
        if data:
            return data[0]["value"]
    except (ValueError, RuntimeError) as feed_error:
        print(f"Error fetching data from feed {feed_key}: {feed_error}")
    return None

def update_display():
    for display_idx, (title, value_feed) in enumerate(zip(TITLES, VALUE_FEEDS)):
        value = get_feed_data(value_feed) or "N/A"
        group[display_idx*2 + 1].text = title  # Update title
        group[display_idx*2 + 2].text = str(value)  # Update value

# Initial display update
update_display()

# Main loop
while True:
    try:
        time.sleep(UPDATE_DELAY)
        update_display()
    except (ValueError, RuntimeError) as loop_error:
        print("Some error occurred, retrying! -", loop_error)
        continue
