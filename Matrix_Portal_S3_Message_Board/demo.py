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
fontpool.add_font("comic", "fonts/Comic-10.pcf")
fontpool.add_font("dejavu", "fonts/DejaVuSans-10.pcf")

message = Message(fontpool.find_font("terminal"), opacity=0.8)
message.add_image("images/maskedstar.bmp")
message.add_text("Hello World!", color=0xFFFF00, x_offset=2, y_offset=2)

message1 = Message(fontpool.find_font("dejavu"))

message2 = Message(fontpool.find_font("comic"), mask_color=0x00FF00)
print("add blinka")
message2.add_image("images/maskedblinka.bmp")
print("add text")
message2.add_text("CircuitPython", color=0xFFFF00, y_offset=-2)

message3 = Message(fontpool.find_font("dejavu"))
message3.add_text("circuitpython.com", color=0xFF0000)

message4 = Message(fontpool.find_font("arial"))
message4.add_text("Buy Electronics", color=0xFFFFFF)

while True:
    message1.clear()
    message1.add_text("Scroll Text In", color=0xFF0000)

    messageboard.animate(message1, "Scroll", "in_from_left")
    time.sleep(1)
    message1.clear()
    message1.add_text("Change Messages")
    messageboard.animate(message1, "Static", "show")
    time.sleep(1)
    message1.clear()
    message1.add_text("And Scroll Out")

    messageboard.animate(message1, "Static", "show")
    messageboard.animate(message1, "Scroll", "out_to_right")
    time.sleep(1)

    message1.clear()
    message1.add_text("Or more effects like looping   ", color=0xFFFF00)
    messageboard.animate(
        message1, "Split", "in_vertically"
    )  # Split never completely joins
    messageboard.animate(
        message1, "Loop", "left"
    )  # Text too high (probably from split)
    messageboard.animate(
        message1, "Static", "flash", count=3
    )  # Flashes in weird positions

    messageboard.animate(message1, "Split", "out_vertically")
    time.sleep(1)

    messageboard.animate(message2, "Static", "fade_in")
    time.sleep(1)
    messageboard.animate(message2, "Static", "fade_out")

    messageboard.set_background(0x00FF00)
    messageboard.animate(message3, "Scroll", "in_from_top")
    time.sleep(1)
    messageboard.animate(message3, "Scroll", "out_to_bottom")
    messageboard.set_background("images/background.bmp")

    messageboard.animate(message4, "Scroll", "in_from_right")
    time.sleep(1)
