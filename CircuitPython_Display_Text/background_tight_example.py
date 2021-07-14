# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Illustrates the background_tight parameter of display_text label and bitmap_label
"""
import board
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label


# Built-in display
display = board.DISPLAY

# Make the display context
main_group = displayio.Group()
display.show(main_group)

font = bitmap_font.load_font("fonts/Fayette-HandwrittenScript-48.bdf")

reg_label = label.Label(
    font=font, text="False", scale=2, background_color=0xDD00DD, background_tight=False
)

reg_label.anchor_point = (0, 0)
reg_label.anchored_position = (20, 20)

j_label = label.Label(
    font=font, text="joy", scale=2, background_color=0xDD00DD, background_tight=False
)

j_label.anchor_point = (0, 0)
j_label.anchored_position = (150, 36)

main_group.append(j_label)
main_group.append(reg_label)

tight_label = label.Label(
    font=font, text="True", scale=2, background_color=0xDD00DD, background_tight=True
)

tight_label.anchor_point = (0, 0)
tight_label.anchored_position = (20, 120)

main_group.append(tight_label)


while True:
    pass
