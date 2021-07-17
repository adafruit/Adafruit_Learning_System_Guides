# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Illustrate padding parameters of label and bitmap_label
"""
import board
import displayio
import terminalio
from adafruit_display_text import label

# Built-in display
display = board.DISPLAY

# Make the display context
main_group = displayio.Group()
display.show(main_group)

# font = bitmap_font.load_font("Fayette-HandwrittenScript-48.bdf")
font = terminalio.FONT

reg_label = label.Label(
    font=font, text="top", scale=2, background_color=0xDD00DD, padding_top=6
)

reg_label.anchor_point = (0, 0)
reg_label.anchored_position = (20, 20)

bottom_label = label.Label(
    font=font, text="bottom", scale=2, background_color=0xDD00DD, padding_bottom=6
)

bottom_label.anchor_point = (0, 0)
bottom_label.anchored_position = (80, 20)

left_label = label.Label(
    font=font, text="left", scale=2, background_color=0xDD00DD, padding_left=6
)

left_label.anchor_point = (0, 0)
left_label.anchored_position = (20, 70)

right_label = label.Label(
    font=font, text="right", scale=2, background_color=0xDD00DD, padding_right=6
)

right_label.anchor_point = (0, 0)
right_label.anchored_position = (80, 70)

all_label = label.Label(
    font=font,
    text="all",
    scale=2,
    background_color=0xDD00DD,
    padding_right=6,
    padding_top=6,
    padding_bottom=6,
    padding_left=6,
)

all_label.anchor_point = (0, 0)
all_label.anchored_position = (40, 140)

main_group.append(left_label)
main_group.append(right_label)
main_group.append(all_label)
main_group.append(reg_label)
main_group.append(bottom_label)
while True:
    pass
