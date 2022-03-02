# SPDX-FileCopyrightText: 2021 Tim C for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython simple sensor data display demo using LC709203 battery monitor and TFT display
"""
import time
import board
import terminalio
from displayio import Group
from adafruit_display_text import bitmap_label
from adafruit_lc709203f import LC709203F

text_area = bitmap_label.Label(terminalio.FONT, scale=2)
text_area.anchor_point = (0.5, 0.5)
text_area.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height // 2)

main_group = Group()

main_group.append(text_area)

print("LC709203F test")
print("Make sure LiPoly battery is plugged into the board!")

sensor = LC709203F(board.I2C())

print("IC version:", hex(sensor.ic_version))

board.DISPLAY.show(main_group)

while True:
    text_area.text = "Battery:\n{:.1f} Volts \n{}%".format(sensor.cell_voltage, sensor.cell_percent)
    time.sleep(1)
