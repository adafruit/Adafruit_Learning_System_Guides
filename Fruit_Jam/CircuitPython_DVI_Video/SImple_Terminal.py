# SPDX-FileCopyrightText: Copyright (c) 2021 Randall Bohn (dexter)
# SPDX-FileCopyrightText: Copyright (c) 2021 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Simple terminalio.Terminal use with the built-in terminalio.FONT
#  for a DVI display from an RP2350 HSTX connection
#
# Modeled on https://github.com/circuitpython/CircuitPython_Module_Examples/
#   blob/801475f745fe2a61738f1abed3bd01007118efa3/terminalio/
#   terminalio_terminal_example.py#L5

import board
import displayio
import terminalio
import picodvi
import framebufferio

displayio.release_displays()
# Set up a 320x240x8 bit display space
fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                         red_dp=board.D0P, red_dn=board.D0N,
                         green_dp=board.D1P, green_dn=board.D1N,
                         blue_dp=board.D2P, blue_dn=board.D2N,
                         color_depth=8)
display = framebufferio.FramebufferDisplay(fb)

group = displayio.Group()
display.root_group = group

palette = displayio.Palette(2)  # A simple color palette
palette[0] = 0x220000  # not so dark Black
palette[1] = 0x00FFFF  # Cyan

ROWS = 12
COLS = 40

w, h = terminalio.FONT.get_bounding_box()

termgrid = displayio.TileGrid(
    terminalio.FONT.bitmap,
    pixel_shader=palette,
    y=20,
    width=COLS,
    height=ROWS,
    tile_width=w,
    tile_height=h,
)
group.append(termgrid)
term = terminalio.Terminal(termgrid, terminalio.FONT)

term.write("Terminal %dx%d:\r\n" % (COLS, ROWS))
term.write("  %dx%d pixels.\r\n" % (COLS * w, ROWS * h))
term.write("Both carriage return and line feed \r\n   are required.\r\n")

while True:
    pass
