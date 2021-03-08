# SPDX-FileCopyrightText: 2021 Jose David Montoya for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
This example shows the use of base_alignment parameter.
"""

import board
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label as label

# Built-in display
display = board.DISPLAY

# Make the display context
main_group = displayio.Group(max_size=10)
display.show(main_group)


# Font definition. You can choose any two fonts available in your system
MEDIUM_FONT = bitmap_font.load_font("fonts/LeagueSpartan-Bold-16.bdf")
BIG_FONT = bitmap_font.load_font("fonts/LeagueGothic-Regular-36.bdf")

TEXT_RIGHT = "MG"
TEXT_LEFT = "32.47"

main_group = displayio.Group()

# Create labels
# Base Alignment parameter False
left_text = label.Label(
    BIG_FONT,
    text=TEXT_LEFT,
    color=0xDD00DD,
    x=10,
    y=50,
    base_alignment=False,
)
main_group.append(left_text)

right_text = label.Label(
    MEDIUM_FONT,
    text=TEXT_RIGHT,
    color=0xDD00DD,
    x=90,
    y=50,
    base_alignment=False,
)
main_group.append(right_text)

# Base Alignment parameter True
left_text_aligned = label.Label(
    BIG_FONT,
    text=TEXT_LEFT,
    color=0xDD00DD,
    x=10,
    y=160,
    base_alignment=True,
)
main_group.append(left_text_aligned)

right_text_aligned = label.Label(
    MEDIUM_FONT,
    text=TEXT_RIGHT,
    color=0xDD00DD,
    x=90,
    y=160,
    base_alignment=True,
)

main_group.append(right_text_aligned)
display.show(main_group)

while True:
    pass
