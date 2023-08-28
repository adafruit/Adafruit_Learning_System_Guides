# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from adafruit_matrixportal.matrix import Matrix
from messageboard import MessageBoard
from messageboard.fontpool import FontPool
from messageboard.message import Message

matrix = Matrix(width=128, height=16, bit_depth=5)
messageboard = MessageBoard(matrix)
messageboard.set_background("images/background.bmp")
fontpool = FontPool()
fontpool.add_font("arial", "fonts/Arial-10.pcf")

# Create the message ahead of time
message = Message(fontpool.find_font("arial"), mask_color=0xFF00FF, opacity=0.8)
message.add_image("images/maskedstar.bmp")
message.add_text("Hello World!", color=0xFFFF00, x_offset=2, y_offset=2)

while True:
    # Animate the message
    messageboard.animate(message, "Scroll", "in_from_right")
    time.sleep(1)
    messageboard.animate(message, "Scroll", "out_to_left")
