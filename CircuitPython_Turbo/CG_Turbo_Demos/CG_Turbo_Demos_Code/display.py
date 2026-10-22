# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""320x240 RGB565 HDMI (pixel-doubled to 640x480) with a 320x200 back buffer.

The back buffer has to be in internal SRAM, which only has about 147 KB left
after the framebuffer: create the Display before allocating anything else big.
`scratch` reserves a little more SRAM, ahead of the back buffer, for a demo's
hot per-frame data.
"""

import array

import board
import displayio
import picodvi
import terminalio

import mem
import mem_asm

WIDTH = 320
HEIGHT = 240
BACK_HEIGHT = 200
TITLE = 0xFF08  # rgb565: the demo's name, button names
HINT = 0x9CF3  # what the buttons do


class Display:
    def __init__(self, scratch=0, back=True, back_width=WIDTH):
        """back=False: no back buffer, for demos that draw straight to the
        screen. back_width < WIDTH: a narrower back buffer (less SRAM),
        shown in the middle of the screen."""
        displayio.release_displays()
        self.framebuffer = picodvi.Framebuffer(
            WIDTH,
            HEIGHT,
            clk_dp=board.CKP,
            clk_dn=board.CKN,
            red_dp=board.D0P,
            red_dn=board.D0N,
            green_dp=board.D1P,
            green_dn=board.D1N,
            blue_dp=board.D2P,
            blue_dn=board.D2N,
            color_depth=16,
        )
        self.screen = memoryview(self.framebuffer).cast("B")
        self.scratch = bytearray(scratch)
        self.back_width = back_width
        self.back = bytearray(back_width * BACK_HEIGHT * 2 if back else 0)
        for name in ("scratch", "back"):
            if not len(getattr(self, name)):
                continue
            where = mem.address(getattr(self, name))
            if 0 < where < mem.SRAM:
                print(
                    "warning: %s buffer is in PSRAM (0x%08x): rendering will be slow"
                    % (name, where)
                )
        top = (HEIGHT - BACK_HEIGHT) // 2 * WIDTH * 2
        self.letterbox = self.screen[top : top + len(self.back)] if back else None
        if back and back_width < WIDTH:
            # rows of the narrow back buffer go to the middle of each screen row
            left = (WIDTH - back_width) // 2 * 2
            self.letterbox = None
            if back_width % 8:
                raise ValueError("back_width must be a multiple of 8")
            # mem_asm.copy_rows_asm's dst, src, rows, words per row, dst stride
            dst = mem.address(self.screen) + top + left
            self.copy = array.array(
                "i", (dst, mem.address(self.back), BACK_HEIGHT, back_width // 2, WIDTH * 2)
            )
            self.copy_address = mem.address(self.copy)
        self.wait_for_vblank = getattr(self.framebuffer, "wait_for_vblank", None)
        row = bytes(WIDTH * 2)
        for y in range(HEIGHT):
            self.screen[y * WIDTH * 2 : (y + 1) * WIDTH * 2] = row
        self.pixels = memoryview(self.framebuffer).cast("H")

    def flip(self):
        """Show the back buffer: starts at vblank and outruns the beam, so no tearing."""
        if self.wait_for_vblank:
            self.wait_for_vblank()
        if self.letterbox is not None:
            self.letterbox[:] = self.back
        else:
            mem_asm.copy_rows_asm(self.copy_address)

    def text(self, x, y, string, color=HINT):  # pylint: disable=too-many-locals
        """Draw string with the built-in 6 x 12 font straight onto the screen,
        top left at (x, y). For the borders around a demo's image: frames only
        copy into the image, so text there stays put and costs nothing per
        frame."""
        font = terminalio.FONT
        pixels = self.pixels
        for i, character in enumerate(string):
            glyph = font.get_glyph(ord(character))
            if glyph is None:
                continue
            bitmap = glyph.bitmap
            per_row = bitmap.width // glyph.width
            tx = (glyph.tile_index % per_row) * glyph.width
            ty = (glyph.tile_index // per_row) * glyph.height
            left = x + i * glyph.width
            for gy in range(glyph.height):
                at = (y + gy) * WIDTH + left
                for gx in range(glyph.width):
                    if bitmap[tx + gx, ty + gy]:
                        pixels[at + gx] = color

    def fill(self, x, y, width, height, color=0):
        """A rectangle of the screen, e.g. to clear text before rewriting it."""
        row = array.array("H", [color] * width)
        for yy in range(y, y + height):
            at = yy * WIDTH + x
            self.pixels[at : at + width] = row

    def lines(self, x, y, strings, colors=None, spacing=12):
        """Several lines of text, one under the other."""
        for i, string in enumerate(strings):
            self.text(x, y + i * spacing, string, colors[i] if colors else HINT)
