# SPDX-FileCopyrightText: 2020 FoamyGuy for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import displayio
import adafruit_imageload
import ugame

display = board.DISPLAY
player_loc = {"x": 4, "y": 3}

# Load the sprite sheet (bitmap)
sprite_sheet, palette = adafruit_imageload.load(
    "tilegame_assets/castle_sprite_sheet_edited.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette,
)
# make the color at 0 index transparent.
palette.make_transparent(0)

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
sprite.x = 16 * player_loc["x"]
sprite.y = 16 * player_loc["y"]

# Add the Group to the Display
display.root_group = group

prev_btn_vals = ugame.buttons.get_pressed()

while True:
    cur_btn_vals = ugame.buttons.get_pressed()
    if not prev_btn_vals & ugame.K_UP and cur_btn_vals & ugame.K_UP:
        player_loc["y"] = max(1, player_loc["y"] - 1)
    if not prev_btn_vals & ugame.K_DOWN and cur_btn_vals & ugame.K_DOWN:
        player_loc["y"] = min(6, player_loc["y"] + 1)

    if not prev_btn_vals & ugame.K_RIGHT and cur_btn_vals & ugame.K_RIGHT:
        player_loc["x"] = min(8, player_loc["x"] + 1)
    if not prev_btn_vals & ugame.K_LEFT and cur_btn_vals & ugame.K_LEFT:
        player_loc["x"] = max(1, player_loc["x"] - 1)

    # update the the player sprite position
    sprite.x = 16 * player_loc["x"]
    sprite.y = 16 * player_loc["y"]

    # update the previous values
    prev_btn_vals = cur_btn_vals
