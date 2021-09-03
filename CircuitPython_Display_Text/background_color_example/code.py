# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
Illustrates the background_color parameter of display_text label and bitmap_label
"""
import board
import displayio
import terminalio
from adafruit_display_text import label

# Make the display context. Change size if you want
display = board.DISPLAY

# Make the display context
main_group = displayio.Group()
display.show(main_group)

reg_label = label.Label(
    font=terminalio.FONT,
    text="CircuitPython",
    scale=3,
    background_color=0xDD00DD,
)

reg_label.anchor_point = (0, 0)
reg_label.anchored_position = (20, 20)

main_group.append(reg_label)

while True:
    pass
