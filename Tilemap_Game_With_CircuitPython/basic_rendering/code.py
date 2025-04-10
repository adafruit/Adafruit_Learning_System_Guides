# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
# SPDX-FileCopyrightText: 2020 FoamyGuy for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import displayio
import adafruit_imageload

display = board.DISPLAY

# Load the sprite sheet (bitmap)
sprite_sheet, palette = adafruit_imageload.load(
    "tilegame_assets/castle_sprite_sheet.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette,
)

# Create the sprite TileGrid
sprite = displayio.TileGrid(
    sprite_sheet,
    pixel_shader=palette,
    width=1,
    height=1,
    tile_width=16,
    tile_height=16,
    default_tile=0,
)

# Create the castle TileGrid
castle = displayio.TileGrid(
    sprite_sheet,
    pixel_shader=palette,
    width=10,
    height=8,
    tile_width=16,
    tile_height=16,
)

# Create a Group to hold the sprite and add it
sprite_group = displayio.Group()
sprite_group.append(sprite)

# Create a Group to hold the castle and add it
castle_group = displayio.Group(scale=1)
castle_group.append(castle)

# Create a Group to hold the sprite and castle
group = displayio.Group()

# Add the sprite and castle to the group
group.append(castle_group)
group.append(sprite_group)

# Castle tile assignments
# corners
castle[0, 0] = 3  # upper left
castle[9, 0] = 5  # upper right
castle[0, 7] = 9  # lower left
castle[9, 7] = 11  # lower right
# top / bottom walls
for x in range(1, 9):
    castle[x, 0] = 4  # top
    castle[x, 7] = 10  # bottom
# left/ right walls
for y in range(1, 7):
    castle[0, y] = 6  # left
    castle[9, y] = 8  # right
# floor
for x in range(1, 9):
    for y in range(1, 7):
        castle[x, y] = 7  # floor

# put the sprite somewhere in the castle
sprite.x = 16 * 4
sprite.y = 16 * 3

# Add the Group to the Display
display.root_group = group
while True:
    pass
