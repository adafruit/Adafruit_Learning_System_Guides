# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
This examples shows the use custom fonts
"""
import board
import displayio
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label


# built-in display
display = board.DISPLAY

# Make the display context
main_group = displayio.Group()
display.show(main_group)

font = bitmap_font.load_font("fonts/LeagueSpartan-Bold-16.bdf")
# font = terminalio.FONT

reg_label = label.Label(font=terminalio.FONT, text="Blinka_Displayio", scale=2)
reg_label.anchor_point = (0, 0)
reg_label.anchored_position = (20, 20)

custom_font_lbl = label.Label(font=font, text="League Spartan", scale=1)

custom_font_lbl.anchor_point = (0, 0)
custom_font_lbl.anchored_position = (20, 50)

main_group.append(reg_label)
main_group.append(custom_font_lbl)

while True:
    pass
