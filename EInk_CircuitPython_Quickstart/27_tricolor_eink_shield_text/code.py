# SPDX-FileCopyrightText: 2019 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
  Simple text script for 2.7" 264x176 Tri-Color display shield
  Supported products:
  * Adafruit 2.7" Tri-Color ePaper Display Shield
    https://www.adafruit.com/product/4229
  This program requires the adafruit_il91874 and the
  adafruit_display_text library in /lib on the CIRCUITPY drive
  for CircuitPython 5.0 and above which has displayio support.
"""

import time
import board
import displayio
import adafruit_il91874
import terminalio
from adafruit_display_text import label

BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

# Change text colors, choose from the following values:
# BLACK, WHITE, RED (note red on this display is not vivid)

FOREGROUND_COLOR = BLACK
BACKGROUND_COLOR = WHITE

# Used to ensure the display is free in CircuitPython
displayio.release_displays()

# Define the pins needed for display use on the Metro
spi = board.SPI()
epd_cs = board.D10
epd_dc = board.D9

# Create the displayio connection to the display pins
display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs,
                                 baudrate=1000000)
time.sleep(1)  # Wait a bit

# Create the display object - the third color is red (0xff0000)
DISPLAY_WIDTH = 264
DISPLAY_HEIGHT = 176

# Create the display object - the third color is red (0xff0000)
display = adafruit_il91874.IL91874(display_bus, width=DISPLAY_WIDTH,
                                   height=DISPLAY_HEIGHT,
                                   highlight_color=0xff0000, rotation=90)

# Create a display group for our screen objects
g = displayio.Group()

# Set a white background
background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
# Map colors in a palette
palette = displayio.Palette(1)
palette[0] = BACKGROUND_COLOR

# Create a Tilegrid with the background and put in the displayio group
t = displayio.TileGrid(background_bitmap, pixel_shader=palette)
g.append(t)

# Draw simple text using the built-in font into a displayio group
text_group = displayio.Group(scale=2, x=40, y=40)
text = "Hello World!"
text_area = label.Label(terminalio.FONT, text=text, color=FOREGROUND_COLOR)
text_group.append(text_area)  # Add this text to the text group
g.append(text_group)

# Place the display group on the screen
display.root_group = g

# Refresh the display to have everything show on the display
# NOTE: Do not refresh eInk displays more often than 180 seconds!
display.refresh()

time.sleep(180)
while True:
    pass
