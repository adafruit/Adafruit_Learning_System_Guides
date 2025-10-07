# SPDX-FileCopyrightText: 2025 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""Simple test script for 7.5" 800x480 monochrome display"""

import time

import board
import busio
import displayio
from fourwire import FourWire

import adafruit_uc8179

displayio.release_displays()

if "EPD_MOSI" in dir(board): # Feather RP2040 ThinkInk
    spi = busio.SPI(board.EPD_SCK, MOSI=board.EPD_MOSI, MISO=None)
    epd_cs = board.EPD_CS
    epd_dc = board.EPD_DC
    epd_reset = board.EPD_RESET
    epd_busy = board.EPD_BUSY
else:
    spi = board.SPI()  # Uses SCK and MOSI
    epd_cs = board.D9
    epd_dc = board.D10
    epd_reset = board.D8  # Set to None for FeatherWing
    epd_busy = board.D7  # Set to None for FeatherWing

display_bus = FourWire(spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000)
time.sleep(1)

display = adafruit_uc8179.UC8179(
    display_bus,
    width=800,
    height=480,
    busy_pin=epd_busy,
    rotation=180,
    black_bits_inverted=True,
    colstart=0,
)

g = displayio.Group()

pic = displayio.OnDiskBitmap("/display-ruler-1280x720.bmp")
t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
g.append(t)

display.root_group = g

display.refresh()

print("refreshed")

time.sleep(display.time_to_refresh + 5)
print("waited correct time")

# Keep the display the same
while True:
    time.sleep(10)
