# SPDX-FileCopyrightText: Copyright (c) 2022 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
import board
import neopixel
from adafruit_display_text.bitmap_label import Label
from adafruit_bitmap_font import bitmap_font
from displayio import Bitmap
from rainbowio import colorwheel

font = bitmap_font.load_font("tom-thumb.pcf", Bitmap)
label = Label(text="Hello World!!  Adafruit QT Py RP2040 + NeoPixel BFF  ", font=font)
bitmap = label.bitmap

pixels = neopixel.NeoPixel(board.A2, 5*5, brightness=.07, auto_write=False)
pixels.fill(0)
pixels.show()
colors = [0, 0]
hue = 0
while True:
    for i in range(bitmap.width):
        # Use a rainbow of colors, shifting each column of pixels
        hue = hue + 7
        if hue >= 256:
            hue = hue - 256

        colors[1] = colorwheel(hue)
        # Scoot the old text left by 1 pixel
        pixels[0:20] = pixels[5:25]

        # Draw in the next line of text
        for y in range(5):
            # Select black or color depending on the bitmap pixel
            pixels[20+y] = colors[bitmap[i,y]]
        pixels.show()
        time.sleep(.1)
