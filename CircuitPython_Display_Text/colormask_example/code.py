# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Illustrates the advanced usage of bitmap_label with transparency to
create a color mask cutout
"""

import board
import displayio
from rainbowio import colorwheel
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label as label

# Make the display context. Change size if you want
display = board.DISPLAY

background = displayio.Bitmap(320, 240, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = 0xDDDD00

# Make the display context
main_group = displayio.Group()
display.show(main_group)

font = bitmap_font.load_font("fonts/LeagueSpartan-Bold-16.bdf")
reg_label = label.Label(
    font=font,
    text="CIRCUIT PYTHON",
    padding_bottom=20,
    color=None,
    scale=1,
    background_color=0x000000,
)

reg_label.anchor_point = (0.5, 0.5)
reg_label.anchored_position = (display.width // 2, display.height // 2)

rainbow_bitmap = displayio.Bitmap(
    reg_label.bounding_box[2] * reg_label.scale,
    reg_label.bounding_box[3] * reg_label.scale,
    255,
)
rainbow_palette = displayio.Palette(255)

for i in range(0, 255):
    rainbow_palette[i] = int("".join("%02x" % i for i in colorwheel(i)), 16)

for y in range(rainbow_bitmap.height):
    for x in range(rainbow_bitmap.width):
        rainbow_bitmap[x, y] = max(1, (x + 1) % 255)

bg_tilegrid = displayio.TileGrid(rainbow_bitmap, pixel_shader=rainbow_palette)

print(reg_label.bounding_box[0])
bg_tilegrid.x = reg_label.x + 1
bg_tilegrid.y = reg_label.y - 8

main_group.append(bg_tilegrid)
main_group.append(reg_label)

while True:
    pass
