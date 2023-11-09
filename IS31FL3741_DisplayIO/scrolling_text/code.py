# SPDX-FileCopyrightText: 2022 Mark Komus
#
# SPDX-License-Identifier: MIT

import random
import time
import board
import busio
import displayio
import framebufferio
import is31fl3741
from adafruit_is31fl3741.led_glasses_map import glassesmatrix_ledmap
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font

# List of possible messages to display.
MESSAGES = (
    "DISPLAYIO AMAZES",
    "CIRCUITPYTHON RULES",
    "HELLO WORLD!",
)

TEXT_COLOR = (220, 210, 0) # Yellow

# Remove any existing displays
displayio.release_displays()

# Initialize the LED Glasses
#
# In this example scale is set to True. When True the logical display is
# three times the physical display size and scaled down to allow text to
# look more natural for small display sizes. Hence the display is created
# as 54x15 when the physical display is 18x5.
#
i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)
is31 = is31fl3741.IS31FL3741(i2c=i2c)
is31_framebuffer = is31fl3741.IS31FL3741_FrameBuffer(
    is31, 54, 15, glassesmatrix_ledmap, scale=True, gamma=True
)
display = framebufferio.FramebufferDisplay(is31_framebuffer, auto_refresh=True)

# Dim the display. Full brightness is BRIGHT
is31_framebuffer.brightness = 0.2

# Load the font to be used - scrolly only has upper case letters
font = bitmap_font.load_font("/fonts/scrolly.bdf")

# Set up the displayio elements
text_area = label.Label(font, text="", color=TEXT_COLOR)
text_area.y = 8
group = displayio.Group()
group.append(text_area)
display.root_group = group

# Continue to scroll messages forever
while True:
    # Pick a random message to display
    text_area.text = random.choice(MESSAGES)

    # Reset the text to start just off the right side
    x = display.width
    text_area.x = x

    # Determine the width of the message to scroll
    width = text_area.bounding_box[2]

    # Scroll the message across the glasses
    while x != -width:
        x = x - 1
        text_area.x = x
        time.sleep(0.05) # adjust to change scrolling speed
