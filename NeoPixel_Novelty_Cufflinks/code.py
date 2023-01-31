# SPDX-FileCopyrightText: Copyright (c) 2023 Erin St. Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
from random import randint
import board
import neopixel
import fontio
from adafruit_display_text.bitmap_label import Label
from adafruit_bitmap_font import bitmap_font
from displayio import Bitmap
from rainbowio import colorwheel

tom_thumb = bitmap_font.load_font("tom-thumb.pcf", Bitmap)

_glyph_keys = ['bitmap', 'tile_index', 'width', 'height', 'dx', 'dy', 'shift_x', 'shift_y']
def patch_glyph(base, **kw):
    d = {}
    for k in _glyph_keys:
        d[k] = kw.get(k, getattr(base, k))
    return fontio.Glyph(**d)

class PatchedFont:
    def __init__(self, base_font, patches):
        self.base_font = base_font
        self.patches = patches

    def get_glyph(self, glyph):
        g = self.base_font.get_glyph(glyph)
        patch = self.patches.get(glyph)
        if patch is not None:
            # print("patching", repr(chr(glyph)), g)
            g = patch_glyph(g, **patch)
            # print("patched", g)
        return g

    def get_bounding_box(self):
        return self.base_font.get_bounding_box()

font = PatchedFont(tom_thumb,
                   {32: {'shift_x': 1, 'dx': 0},
                    105: {'dx': 0, 'shift_x': 2},
                    33: {'dx': 0, 'shift_x': 2},
                    })

# List of text strings
text_strings = ["     love bun     ", "     dear me     ", "     my bear     ",
                "     my my     ", "     you are babe     "]
# Create a label object
label = Label(text="text", font=font)
bitmap = label.bitmap
heart_bitmap = [
    0, 1, 1, 0, 0,
    1, 1, 1, 1, 0,
    0, 1, 1, 1, 1,
    1, 1, 1, 1, 0,
    0, 1, 1, 0, 0
]
pixels = neopixel.NeoPixel(board.A1, 5*5, brightness=.08, auto_write=False)
while True:
    for hue in range(0, 255, 3):
        color = colorwheel(hue)
        pixels[:] = [pixel * color for pixel in heart_bitmap]
        pixels.show()
        time.sleep(.05)
    hue = 0
    string_index = randint(0, 4)
    label.text = text_strings[string_index]
    bitmap = label.bitmap
    print(string_index)
    for i in range(bitmap.width):
        # Use a rainbow of colors, shifting each column of pixels
        hue = hue + 7
        if hue >= 256:
            hue = hue - 256
        color = colorwheel(hue)
        # Scoot the old text left by 1 pixel
        pixels[:20] = pixels[5:]
        # Draw in the next line of text
        for y in range(5):
            # Select black or color depending on the bitmap pixel
            pixels[20+y] = color * bitmap[i,y]
        pixels.show()
        time.sleep(.2)
