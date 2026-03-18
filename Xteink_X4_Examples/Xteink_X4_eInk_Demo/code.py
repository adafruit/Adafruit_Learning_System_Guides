# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Xteink X4 bitmap test
"""
import os
import board
import displayio
from adafruit_xteink_x4 import InputManager

display = board.DISPLAY

groups = []
images = []
for filename in os.listdir('/'):
    if filename.lower().endswith('.bmp') and not filename.startswith('.'):
        images.append("/"+filename)
print(images)

for i in range(len(images)):
    splash = displayio.Group()
    bitmap = displayio.OnDiskBitmap(images[i])
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
    splash.append(tile_grid)
    groups.append(splash)

index = 0

display.root_group = groups[index]
display.refresh()

buttons = InputManager()

while True:
    buttons.update()

    if buttons.any_pressed:
        for i in range(7):
            if buttons.was_pressed(i):
                index = i

    if buttons.any_released:
        for i in range(7):
            if buttons.was_released(i):
                held = buttons.held_time
                print(f"Released: {buttons.button_name(i)} (held {held:.2f}s)")
                print("updating display..")
                display.root_group = groups[index]
                display.refresh()
                print(f"showing {images[index]}")
