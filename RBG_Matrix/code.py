# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# This example shows how to use text and graphics to create custom signage

import time
import adafruit_display_text.label
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio

# If there was a display before (protomatter, LCD, or E-paper), release it so
# we can create ours
displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, bit_depth=4,
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1, board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)

# Associate the RGB matrix with a Display so that we can use displayio features
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
display.rotation = 180

R = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xff0000,
    scale=3, x=2, y=13,
    text="R")
B = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0x0000ff,
    scale=3, x=24, y=13,
    text="B")
G = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0x00ff00,
    scale=3, x=46, y=13,
    text="G")

# Put each line of text into a Group, then show that group.
g = displayio.Group()
g.append(R)
g.append(B)
g.append(G)
display.root_group = g
display.auto_refresh = True

# Setup the filename as the bitmap data source
bitmap = displayio.OnDiskBitmap("/rbg.bmp")
# Create a TileGrid to hold the bitmap
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)

print(dir(tile_grid))

while True:
    while g:
        g.pop()

    g.append(tile_grid)
    for y in range(bitmap.height+32):
        tile_grid.y = 32-y
        time.sleep(0.05)

    g.pop()

    g.append(R)
    time.sleep(1)
    g.append(B)
    time.sleep(1)
    g.append(G)
    time.sleep(1)
