# SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Minimal example displaying an image tiled across multiple RGB LED matrices.
# This is written for MatrixPortal and four 64x32 pixel matrices, but could
# be adapted to different boards and matrix combinations.
# No additional libraries required, just uses displayio.
# Image wales.bmp should be in CIRCUITPY root directory.

import board
import displayio
import framebufferio
import rgbmatrix

displayio.release_displays() # Release current display, we'll create our own

# Create RGB matrix object for a chain of four 64x32 matrices tiled into
# a single 128x64 pixel display -- two matrices across, two down, with the
# second row being flipped. width and height args are the combined size of
# all the tiled sub-matrices. tile arg is the number of rows of matrices in
# the chain (horizontal tiling is implicit from the width argument, doesn't
# need to be specified, but vertical tiling must be explicitly stated).
# The serpentine argument indicates whether alternate rows are flipped --
# cabling is easier this way, downside is colors may be slightly different
# when viewed off-angle. bit_depth and pins are same as other examples.
MATRIX = rgbmatrix.RGBMatrix(
    width=128, height=64, bit_depth=6, tile=2, serpentine=True,
    rgb_pins=[board.MTX_R1,
              board.MTX_G1,
              board.MTX_B1,
              board.MTX_R2,
              board.MTX_G2,
              board.MTX_B2],
    addr_pins=[board.MTX_ADDRA,
               board.MTX_ADDRB,
               board.MTX_ADDRC,
               board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE)

# Associate matrix with a Display to use displayio features
DISPLAY = framebufferio.FramebufferDisplay(MATRIX, auto_refresh=False,
                                           rotation=0)

# Load BMP image, create Group and TileGrid to hold it
FILENAME = "wales.bmp"

# CircuitPython 6 & 7 compatible
BITMAP = displayio.OnDiskBitmap(open(FILENAME, "rb"))
TILEGRID = displayio.TileGrid(
    BITMAP,
    pixel_shader=getattr(BITMAP, 'pixel_shader', displayio.ColorConverter()),
    tile_width=BITMAP.width,
    tile_height=BITMAP.height
)

# # CircuitPython 7+ compatible
# BITMAP = displayio.OnDiskBitmap(FILENAME)
# TILEGRID = displayio.TileGrid(
#     BITMAP,
#     pixel_shader=BITMAP.pixel_shader,
#     tile_width=BITMAP.width,
#     tile_height=BITMAP.height
# )

GROUP = displayio.Group()
GROUP.append(TILEGRID)
DISPLAY.show(GROUP)
DISPLAY.refresh()

# Nothing interactive, just hold the image there
while True:
    pass
