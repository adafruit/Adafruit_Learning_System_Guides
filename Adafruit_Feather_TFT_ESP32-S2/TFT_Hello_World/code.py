# SPDX-FileCopyrightText: 2021 Tim C for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython simple text display demo
"""
import board
import terminalio
from adafruit_display_text import bitmap_label

# Update this to change the text displayed.
text = "Hello, World!"
# Update this to change the size of the text displayed. Must be a whole number.
scale = 3

text_area = bitmap_label.Label(terminalio.FONT, text=text, scale=scale)
text_area.x = 10
text_area.y = 10
board.DISPLAY.show(text_area)

while True:
    pass
