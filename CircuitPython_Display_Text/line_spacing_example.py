# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Illustrates the line_spacing parameter of label and bitmap_label
"""
import board
import displayio
import terminalio
from adafruit_display_text import label

# Make the display context. Change size if you want
display = board.DISPLAY

# Make the display context
main_group = displayio.Group(max_size=10)
display.show(main_group)

# font = bitmap_font.load_font("Fayette-HandwrittenScript-48.bdf")
font = terminalio.FONT

reg_label = label.Label(
    font=font, text="Line1\nLine2\nLine3\n1.25", scale=2, line_spacing=1.25
)

reg_label.anchor_point = (0, 0)
reg_label.anchored_position = (20, 20)

bottom_label = label.Label(
    font=font, text="Line1\nLine2\nLine3\n2.0", scale=2, line_spacing=2.25
)

bottom_label.anchor_point = (0, 0)
bottom_label.anchored_position = (110, 20)

main_group.append(reg_label)
main_group.append(bottom_label)

while True:
    pass
