# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import supervisor
from displayio import Group, OnDiskBitmap, TileGrid, Palette
from tilepalettemapper import TilePaletteMapper

# use the default built-in display,
# the HSTX / PicoDVI display for the Metro RP2350
display = supervisor.runtime.display

# a group to hold all other visual elements
main_group = Group(scale=4, x=30, y=30)

# set the main group to show on the display
display.root_group = main_group

# load the sprite sheet bitmap
spritesheet_bmp = OnDiskBitmap("match3_cards_spritesheet.bmp")

# create a TilePaletteMapper
tile_palette_mapper = TilePaletteMapper(
    spritesheet_bmp.pixel_shader,  # input pixel_shader
    5,  # input color count
    3,  # grid width
    1  # grid height
)

# create a TileGrid to show some cards
cards_tilegrid = TileGrid(spritesheet_bmp, pixel_shader=tile_palette_mapper,
                          width=3, height=1, tile_width=24, tile_height=32)

# set each tile in the grid to a different sprite index
cards_tilegrid[0, 0] = 10
cards_tilegrid[1, 0] = 25
cards_tilegrid[2, 0] = 2

# re-map each tile in the grid to use a different color for index 1
# all other indexes remain their default values
tile_palette_mapper[0, 0] = [0, 2, 2, 3, 4]
tile_palette_mapper[1, 0] = [0, 3, 2, 3, 4]
tile_palette_mapper[2, 0] = [0, 4, 2, 3, 4]

# add the tilegrid to the main group
main_group.append(cards_tilegrid)

# wait forever so it remains visible on the display
while True:
    pass
