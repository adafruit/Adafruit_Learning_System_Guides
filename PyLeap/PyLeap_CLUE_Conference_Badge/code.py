# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries (Adapted for CLUE)
#
# SPDX-License-Identifier: MIT

import board
from adafruit_pybadger import pybadger

pybadger.badge_background(
    background_color=pybadger.WHITE,
    rectangle_color=pybadger.PURPLE,
    rectangle_drop=0.2,
    rectangle_height=0.6,
)

pybadger.badge_line(
    text="@circuitpython", color=pybadger.BLINKA_PURPLE, scale=2, padding_above=2
)
pybadger.badge_line(text="Blinka", color=pybadger.WHITE, scale=5, padding_above=6)
pybadger.badge_line(
    text="CircuitPythonista", color=pybadger.WHITE, scale=2, padding_above=2
)
pybadger.badge_line(
    text="she/her", color=pybadger.BLINKA_PINK, scale=4, padding_above=7
)

display = board.DISPLAY
display.rotation = 180

pybadger.show_custom_badge()

while True:
    if pybadger.button.a:
        pybadger.show_qr_code("https://circuitpython.org")

    if pybadger.button.b:
        pybadger.show_custom_badge()
