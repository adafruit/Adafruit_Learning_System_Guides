"""
Simple badge script for Adafruit 2.13" 212x104 tri-color display
Supported products:
  * Adafruit 2.13" Tri-Color Display Breakout
  * https://www.adafruit.com/product/4086 (breakout) or
  * https://www.adafruit.com/product/4128 (FeatherWing)

  This program requires the adafruit_il0373 library and the
  adafruit_display_text library in the CIRCUITPY /lib folder
  for CircuitPython 5.0 and above which has displayio support.
"""

import time
import board
import displayio
import adafruit_il0373
import terminalio
from adafruit_display_text import label

BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

# Change text colors, choose from the following values:
# BLACK, RED, WHITE

TEXT_COLOR = BLACK
BACKGROUND_COLOR = WHITE

# Used to ensure the display is free in CircuitPython
displayio.release_displays()

# Define the pins needed for display use
# This pinout is for a Feather M4 and may be different for other boards
spi = board.SPI()  # Uses SCK and MOSI
epd_cs = board.D9
epd_dc = board.D10
epd_reset = board.D5
epd_busy = board.D6

# Create the displayio connection to the display pins
display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs,
                                 reset=epd_reset, baudrate=1000000)
time.sleep(1)  # Wait a bit

DISPLAY_WIDTH = 212
DISPLAY_HEIGHT = 104
# Create the display object - the third color is red (0xff0000)
display = adafruit_il0373.IL0373(display_bus, width=DISPLAY_WIDTH,
                                 height=DISPLAY_HEIGHT,
                                 rotation=90, busy_pin=epd_busy,
                                 highlight_color=0xff0000)

# Create a display group for our screen objects
g = displayio.Group()

# Set a background
background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
# Map colors in a palette
palette = displayio.Palette(1)
palette[0] = BACKGROUND_COLOR

# Put the background into the display group
bg_sprite = displayio.TileGrid(background_bitmap,
                               pixel_shader=palette,
                               x=0, y=0)
g.append(bg_sprite)

# Display a picture from the root directory of the CIRCUITPY drive
# Picture should be HEIGHTxHEIGHT square ideally for a portrait
# But could be the entire WIDTHxHEIGHT for a non-portrait
filename = "/picture.bmp"

# Create a Tilegrid with the bitmap and put in the displayio group

# CircuitPython 6 & 7 compatible
pic = displayio.OnDiskBitmap(open(filename, "rb"))
t = displayio.TileGrid(
    pic, pixel_shader=getattr(pic, 'pixel_shader', displayio.ColorConverter())
)
g.append(t)

# # CircuitPython 7+ compatible
# pic = displayio.OnDiskBitmap(filename)
# t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
# g.append(t)

# Draw simple text using the built-in font into a displayio group
# For smaller text, change scale=2 to scale=1
text_group = displayio.Group(scale=2,
                             x=DISPLAY_HEIGHT + 10,
                             y=int(DISPLAY_HEIGHT/2) - 13)
first_name = "Limor"
text_area = label.Label(terminalio.FONT, text=first_name,
                        color=TEXT_COLOR)
text_group.append(text_area)  # Add this text to the text group
g.append(text_group)

# Draw simple text using the built-in font into a displayio group
text_group = displayio.Group(scale=2,
                             x=DISPLAY_HEIGHT + 10,
                             y=int(DISPLAY_HEIGHT/2) + 13)
last_name = "Ladyada"
text_area = label.Label(terminalio.FONT, text=last_name,
                        color=TEXT_COLOR)
text_group.append(text_area)  # Add this text to the text group
g.append(text_group)

# Place the display group on the screen
display.show(g)

# Refresh the display to have it actually show
# NOTE: Do not refresh eInk displays more often than 180 seconds!
display.refresh()

# Wait the minimum 3 minutes between refreshes. Then loop to freeze.
time.sleep(180)
while True:
    pass
