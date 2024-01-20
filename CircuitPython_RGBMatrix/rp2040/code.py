# SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from math import sin
import board
import displayio
import rgbmatrix
import framebufferio
import adafruit_imageload
import terminalio
from adafruit_display_text.label import Label

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64, bit_depth=6,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.D25, board.D24, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1,
    doublebuffer=True)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

g = displayio.Group()
b, p = adafruit_imageload.load("pi-logo32b.bmp")
t = displayio.TileGrid(b, pixel_shader=p)
t.x = 20
g.append(t)

l = Label(text="Feather\nRP2040", font=terminalio.FONT, color=0xffffff, line_spacing=.7)
g.append(l)

display.root_group = g

target_fps = 50
ft = 1/target_fps
now = t0 = time.monotonic_ns()
deadline = t0 + ft

p = 1
q = 17
while True:
    tm = (now - t0) * 1e-9
    x = l.x - 1
    if x < -40:
        x = 63
    y =  round(12 + sin(tm / p) * 6)
    l.x = x
    l.y = y
    display.refresh(target_frames_per_second=target_fps, minimum_frames_per_second=0)
    while True:
        now = time.monotonic_ns()
        if now > deadline:
            break
        time.sleep((deadline - now) * 1e-9)
    deadline += ft
