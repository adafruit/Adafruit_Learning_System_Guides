# SPDX-FileCopyrightText: 2021 Tim C for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython simple bitmap display demo
"""
import board
from displayio import OnDiskBitmap, TileGrid, Group

main_group = Group()
blinka_img = OnDiskBitmap("images/adafruit_blinka.bmp")

tile_grid = TileGrid(bitmap=blinka_img, pixel_shader=blinka_img.pixel_shader)
main_group.append(tile_grid)

board.DISPLAY.show(main_group)

tile_grid.x = board.DISPLAY.width // 2 - blinka_img.width // 2

while True:
    pass
