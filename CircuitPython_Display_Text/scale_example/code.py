# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Illustrate how the scale parameter of displayio.Group can be used to
change the size of label and bitmap_label
"""
import board
import displayio
import terminalio
from adafruit_display_text import label

# Built-in display
display = board.DISPLAY

# Make the display context
main_group = displayio.Group()
display.root_group = main_group

font = terminalio.FONT

reg_label = label.Label(font=font, text="scale=1", scale=1)
reg_label.anchor_point = (0, 0)
reg_label.anchored_position = (20, 20)

scale2_lbl = label.Label(font=font, text="scale=2", scale=2)

scale2_lbl.anchor_point = (0, 0)
scale2_lbl.anchored_position = (20, 40)

scale3_lbl = label.Label(font=font, text="scale=3", scale=3)

scale3_lbl.anchor_point = (0, 0)
scale3_lbl.anchored_position = (20, 70)

main_group.append(reg_label)
main_group.append(scale3_lbl)
main_group.append(scale2_lbl)
while True:
    pass
