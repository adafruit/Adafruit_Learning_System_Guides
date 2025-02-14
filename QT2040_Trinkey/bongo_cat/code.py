# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import displayio
import i2cdisplaybus
import adafruit_displayio_ssd1306
import adafruit_imageload

#display setup
displayio.release_displays()

i2c = board.STEMMA_I2C()
# oled
oled_reset = board.D9
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3D, reset=oled_reset)
WIDTH = 128
HEIGHT = 64
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# default group
group = displayio.Group()
display.root_group = group

# graphics bitmap
bitmap, palette_bit = adafruit_imageload.load(
    "/bongo.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette,
)
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette_bit,
                                width=1, height=1,
                                tile_height=64, tile_width=105,
                                default_tile=0, x = 7)
group.append(tile_grid)

bongo = 0
index = 0
delay = 0.15

while True:
    if (bongo + delay) < time.monotonic():
        tile_grid[0] = index
        index = 1 if index == 0 else 0
        bongo = time.monotonic()
