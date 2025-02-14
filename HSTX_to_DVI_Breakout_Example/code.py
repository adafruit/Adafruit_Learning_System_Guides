# SPDX-FileCopyrightText: 2024 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import picodvi
import framebufferio
import displayio

displayio.release_displays()

fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                                   red_dp=board.D0P, red_dn=board.D0N,
                                   green_dp=board.D1P, green_dn=board.D1N,
                                   blue_dp=board.D2P, blue_dn=board.D2N,
                                   color_depth=16)
display = framebufferio.FramebufferDisplay(fb)

# Initialize the display in the display variable
ruler = displayio.OnDiskBitmap("/display-ruler-rgb-720p.bmp")

t = displayio.TileGrid(ruler, pixel_shader=ruler.pixel_shader)

g = displayio.Group()
g.append(t)

display.root_group = g

display.refresh()

while True:
    pass
