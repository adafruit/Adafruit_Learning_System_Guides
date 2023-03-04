# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import terminalio
from adafruit_display_text import label

display = board.DISPLAY

# Set text, font, and color
text = "HELLO WORLD"
font = terminalio.FONT
color = 0x0000FF

# Create the text label
text_area = label.Label(font, text=text, color=color)

# Set the location
text_area.x = 100
text_area.y = 80

# Show the group. displayio API for versions <= 7.3.3
# display.show(text_area)

# Show the group. displayio API for versions >= 8.0.0
display.root_group = text_area

# Loop forever so you can enjoy your image
while True:
    pass
