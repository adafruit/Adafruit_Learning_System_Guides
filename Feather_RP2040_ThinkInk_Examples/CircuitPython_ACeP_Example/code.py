# SPDX-FileCopyrightText: Copyright (c) 2023 Scott Shawcroft for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

'''Simple test for a 5.65" ACeP eInk Display
with the Feather RP2040 ThinkInk'''

import board
import displayio
import busio
import adafruit_spd1656

displayio.release_displays()

# this pinout is for the Feather RP2040 ThinkInk
spi = busio.SPI(board.EPD_SCK, MOSI=board.EPD_MOSI, MISO=None)
epd_cs = board.EPD_CS
epd_dc = board.EPD_DC
epd_reset = board.EPD_RESET
epd_busy = board.EPD_BUSY
display_bus = displayio.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000
)

display = adafruit_spd1656.SPD1656(
    display_bus, width=600, height=448, busy_pin=epd_busy
)

g = displayio.Group()

fn = "/display-ruler-720p.bmp"

with open(fn, "rb") as f:
    pic = displayio.OnDiskBitmap(f)
    t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)

    display.show(g)

    display.refresh()

while True:
    pass
