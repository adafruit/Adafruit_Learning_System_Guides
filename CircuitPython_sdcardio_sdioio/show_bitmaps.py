import os
import time

import board
import digitalio
import displayio
import mount_sd

display = board.DISPLAY

# The bmp files on the sd card will be shown in alphabetical order
bmpfiles = sorted("/sd/" + filename for filename in os.listdir("/sd")
    if filename.lower().endswith("bmp"))

while True:
    for filename in bmpfiles:
        print("showing", filename)

        bitmap_file = open(filename, "rb")
        bitmap = displayio.OnDiskBitmap(bitmap_file)
        tile_grid = displayio.TileGrid(bitmap,
            pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter()))
        group = displayio.Group()
        group.append(tile_grid)
        display.show(group)

        # Show the image for 10 seconds
        time.sleep(10)
