# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple test script for 2.13" 250x122 monochrome display."""

import time

import board
import busio
import displayio
from fourwire import FourWire

import adafruit_ssd1680

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

display = adafruit_ssd1680.SSD1680(
    display_bus,
    width=250,
    height=122,
    busy_pin=epd_busy,
    highlight_color=0xFF0000,
    rotation=270,
    colstart=0,
)

g = displayio.Group()

pic = displayio.OnDiskBitmap("/display-ruler-640x360.bmp")
t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
g.append(t)

display.root_group = g

display.refresh()

print("refreshed")

time.sleep(display.time_to_refresh + 5)
print("waited correct time")

while True:
    time.sleep(10)
