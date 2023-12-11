# SPDX-FileCopyrightText: 2020 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time

import board
import displayio

display = board.DISPLAY

# The bmp files on the sd card will be shown in alphabetical order
bmpfiles = sorted("/sd/" + fn for fn in os.listdir("/sd") if fn.lower().endswith("bmp"))

while True:
    if len(bmpfiles) == 0:
        print("No BMP files found")
        break

    for filename in bmpfiles:
        print("showing", filename)

        # CircuitPython 6 & 7 compatible
        bitmap_file = open(filename, "rb")
        bitmap = displayio.OnDiskBitmap(bitmap_file)
        tile_grid = displayio.TileGrid(
            bitmap,
            pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter())
        )

        # # CircuitPython 7+ compatible
        # bitmap = displayio.OnDiskBitmap(filename)
        # tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)

        group = displayio.Group()
        group.append(tile_grid)
        display.root_group = group

        # Show the image for 10 seconds
        time.sleep(10)
