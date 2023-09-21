# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: Unlicense

'''Simple test for the Adafruit 2.13" Tri-Color eInk Display
with the Feather RP2040 ThinkInk'''

import time
import board
import displayio
import busio
import adafruit_ssd1680

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
time.sleep(1)

display = adafruit_ssd1680.SSD1680(
    display_bus,
    colstart=8,
    width=250,
    height=122,
    highlight_color=0xFF0000,
    rotation=270,
)

g = displayio.Group()

with open("/display-ruler.bmp", "rb") as f:
    pic = displayio.OnDiskBitmap(f)

    t = displayio.TileGrid(
        pic, pixel_shader=getattr(pic, "pixel_shader", displayio.ColorConverter())
    )

    g.append(t)

    display.show(g)

    display.refresh()

    print("refreshed")

while True:
    pass
