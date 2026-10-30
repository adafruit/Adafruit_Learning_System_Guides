# SPDX-FileCopyrightText: Copyright (c) 2026 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import bitmaptools
import displayio
import raspberry_pi_touch_display_2 as display_init

displayio.release_displays()

# create display
i2c = board.I2C()
display = display_init.make_display(i2c)

# colors: white, yellow, cyan, green, magenta, red, blue, black
palette = displayio.Palette(8)
palette[0] = 0xFFFFFF
palette[1] = 0xFFFF00
palette[2] = 0x00FFFF
palette[3] = 0x00FF00
palette[4] = 0xFF00FF
palette[5] = 0xFF0000
palette[6] = 0x0000FF
palette[7] = 0x000000

# create bitmap, add color bars to bitmap
bitmap = displayio.Bitmap(1280, 720, 8)
for index in range(8):
    bitmaptools.fill_region(bitmap, index * 160, 0, (index + 1) * 160, 720, index)

# display group
bars = displayio.Group()
bars.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = bars

while True:
    pass
