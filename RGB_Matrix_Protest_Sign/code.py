# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import displayio
import framebufferio
import rgbmatrix
from adafruit_slideshow import SlideShow

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64,
    height=32,
    bit_depth=5,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13,
    latch_pin=board.D0,
    output_enable_pin=board.D1,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

slideshow = SlideShow(
    display,
    backlight_pwm=None,
    folder="/images",
    loop=True,
    order=0,
    fade_effect=False,
    dwell=8,
    auto_advance=True,
)


while slideshow.update():
    pass
