"""
Simple bitmap script for Adafruit 2.13" 212x104 tri-color display
Supported products:
  * Adafruit 2.13" Tri-Color Display Breakout
  * https://www.adafruit.com/product/4086 (breakout) or
  * https://www.adafruit.com/product/4128 (FeatherWing)

  This program requires the adafruit_il0373 library in the
  CIRCUITPY /lib folder for CircuitPython 5.0 and above
  which has displayio support.
"""

import time
import board
import displayio
import adafruit_il0373

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

# Create the display object - the third color is red (0xff0000)
display = adafruit_il0373.IL0373(display_bus, width=212, height=104,
                                 rotation=90, busy_pin=epd_busy,
                                 highlight_color=0xff0000)

# Create a display group for our screen objects
g = displayio.Group()

# Display a ruler graphic from the root directory of the CIRCUITPY drive
f = open("/display-ruler.bmp", "rb")

pic = displayio.OnDiskBitmap(f)
# Create a Tilegrid with the bitmap and put in the displayio group
t = displayio.TileGrid(pic, pixel_shader=displayio.ColorConverter())
g.append(t)

# Place the display group on the screen
display.show(g)

# Refresh the display to have it actually show
display.refresh()

# NOTE: Do not refresh eInk displays more often than 180 seconds!
time.sleep(180)
while True:
    pass
