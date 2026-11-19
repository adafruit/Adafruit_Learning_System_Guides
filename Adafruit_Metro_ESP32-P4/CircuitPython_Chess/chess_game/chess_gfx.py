# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=import-outside-toplevel, too-many-locals
"""Bitmap loading and anti-aliased text drawing for displayio.

Images are indexed BMPs; fonts are 4-bit LVGL binary fonts. Each Text label
blits glyphs into its own 16-level bitmap, giving proportional, anti-aliased
text against the label's background, with no allocation when the text changes.
"""

import struct

import adafruit_imageload
import bitmaptools
import displayio

LEFT, CENTER, RIGHT = 0, 1, 2


def load_bitmap(path):
    """Returns (bitmap, palette) of an indexed BMP. The app supplies its own
    palettes; the file's palette only matters for viewing it on a PC."""
    return adafruit_imageload.load(
        path, bitmap=displayio.Bitmap, palette=displayio.Palette
    )


def blend(bg, fg, t):
    """Mixes two 0xRRGGBB colours: t = 0 gives bg, t = 1 gives fg."""
    r = ((bg >> 16) & 255) + (((fg >> 16) & 255) - ((bg >> 16) & 255)) * t
    g = ((bg >> 8) & 255) + (((fg >> 8) & 255) - ((bg >> 8) & 255)) * t
    b = (bg & 255) + ((fg & 255) - (bg & 255)) * t
    return (int(r + 0.5) << 16) | (int(g + 0.5) << 8) | int(b + 0.5)


def fill_ramp(palette, bg, fg, first=0, levels=16):
    """Fills `levels` palette entries from `first` with a bg-to-fg gradient."""
    for i in range(levels):
        palette[first + i] = blend(bg, fg, i / (levels - 1))


def read_lvgl_fast(path):
    """Fast loader for the LVGL fonts in assets*/. Returns (ascent, descent, glyphs)
    for ASCII 32-126, each glyph (bitmap or None, width, height, x, y, advance).

    Reads each glyph with one bitmaptools.readinto, so it only handles this
    layout: 4 bpp, uncompressed, 8-bit glyph fields, integer advances, 32-bit
    loca, one format-2 cmap range and even glyph widths. Returns None otherwise."""
    with open(path, "rb") as f:
        pos = {}
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            size = struct.unpack("<I", hdr[:4])[0]
            if size < 8:
                break
            pos[bytes(hdr[4:])] = f.tell() - 8
            f.seek(pos[bytes(hdr[4:])] + size)
        if (
            b"head" not in pos
            or b"cmap" not in pos
            or b"loca" not in pos
            or b"glyf" not in pos
        ):
            return None
        f.seek(pos[b"head"] + 8)
        h = f.read(40)
        ascent, descent = struct.unpack_from("<Hh", h, 8)
        # 32-bit loca, integer advance, 4 bpp, 8-bit glyph fields, uncompressed
        if tuple(h[26:34]) != (1, h[27], 0, 4, 8, 8, 8, 0):
            return None
        f.seek(pos[b"cmap"] + 8)
        c = f.read(20)
        _, start, length, gid0, _, fmt = struct.unpack_from("<IIHHHB", c, 4)
        if (
            struct.unpack_from("<I", c)[0] != 1
            or fmt != 2
            or start > 32
            or start + length < 127
        ):
            return None
        f.seek(pos[b"loca"] + 8)
        n = struct.unpack("<I", f.read(4))[0]
        loca = struct.unpack("<%dI" % n, f.read(4 * n))
        glyf = pos[b"glyf"]
        glyphs = []
        for code in range(32, 127):
            f.seek(glyf + loca[gid0 + code - start])
            adv, bx, by, w, gh = struct.unpack("<BbbBB", f.read(5))
            bmp = None
            if w and gh:
                if w & 1:
                    return None
                bmp = displayio.Bitmap(w, gh, 16)
                bitmaptools.readinto(
                    bmp,
                    f,
                    bits_per_pixel=4,
                    element_size=1,
                    reverse_pixels_in_element=True,
                )
            glyphs.append((bmp, w, gh, bx, by, adv))
    return ascent, descent, glyphs


def read_lvgl_lib(path):
    """Fallback for read_lvgl_fast(): loads any LVGL font via adafruit_bitmap_font.
    Much slower, since it reads pixel by pixel in Python."""
    from adafruit_bitmap_font import bitmap_font

    font = bitmap_font.load_font(path, displayio.Bitmap)
    font.load_glyphs(range(32, 127))
    glyphs = []
    for code in range(32, 127):
        g = font.get_glyph(code)
        glyphs.append((g.bitmap, g.width, g.height, g.dx, g.dy, g.shift_x))
    f = getattr(font, "file", None)  # the font keeps its file open; close it
    if f:
        f.close()
    return font.ascent, font.descent, glyphs


class Font:
    """A proportional, anti-aliased LVGL binary font. All of ASCII 32-126 is
    loaded up front, so drawing never reads the file."""

    def __init__(self, path):
        self.ascent, descent, glyphs = read_lvgl_fast(path) or read_lvgl_lib(path)
        self.height = self.ascent - descent
        self.bitmap = [g[0] for g in glyphs]
        self.w = [g[1] for g in glyphs]
        self.h = [g[2] for g in glyphs]
        self.dx = [g[3] for g in glyphs]
        # each glyph's top edge, measured down from the top of the line
        self.top = [self.ascent - g[4] - g[2] for g in glyphs]
        self.adv = [g[5] for g in glyphs]

    def _index(self, ch):
        i = ord(ch) - 32
        return i if 0 <= i < len(self.adv) else 31  # '?'

    def width(self, text):
        n = 0
        for ch in text:
            n += self.adv[self._index(ch)]
        return n

    def draw(self, bmp, text, x, y):
        """Blits text into a 16-level bmp (0 = background) with its top-left at x, y,
        clipping glyphs that overhang the edges."""
        bw, bh = bmp.width, bmp.height
        for ch in text:
            i = self._index(ch)
            w, h = self.w[i], self.h[i]
            if w and h:
                gx, gy = x + self.dx[i], y + self.top[i]
                sx = sy = 0
                if gx < 0:
                    sx, gx = -gx, 0
                if gy < 0:
                    sy, gy = -gy, 0
                ex = min(w, sx + bw - gx)
                ey = min(h, sy + bh - gy)
                if ex > sx and ey > sy:
                    bitmaptools.blit(
                        bmp,
                        self.bitmap[i],
                        gx,
                        gy,
                        x1=sx,
                        y1=sy,
                        x2=ex,
                        y2=ey,
                        skip_source_index=0,
                    )
            x += self.adv[i]


class Text:
    """A text label with its own background colour, drawn as a TileGrid."""

    def __init__(self, font, width, x, y, fg, bg, text="", align=LEFT, height=None):
        self.font = font
        self.align = align
        self.bitmap = displayio.Bitmap(width, height or font.height, 16)
        self.palette = displayio.Palette(16)
        self.fg = self.bg = None
        self.text = None
        self.tile = displayio.TileGrid(self.bitmap, pixel_shader=self.palette, x=x, y=y)
        self.set_colours(fg, bg)
        self.set(text)

    def set_colours(self, fg, bg):
        if fg != self.fg or bg != self.bg:
            self.fg, self.bg = fg, bg
            fill_ramp(self.palette, bg, fg)

    def set(self, text, fg=None):
        if fg is not None:
            self.set_colours(fg, self.bg)
        if text == self.text:
            return
        self.text = text
        bmp, font = self.bitmap, self.font
        bmp.fill(0)
        w = font.width(text)
        while w > bmp.width and text:
            text = text[:-1]
            w = font.width(text)
        if self.align == CENTER:
            x = (bmp.width - w) // 2
        elif self.align == RIGHT:
            x = bmp.width - w
        else:
            x = 0
        font.draw(bmp, text, x, (bmp.height - font.height) // 2)

    def contains(self, x, y, ox=0, oy=0):
        t = self.tile
        return (
            t.x + ox <= x < t.x + ox + self.bitmap.width
            and t.y + oy <= y < t.y + oy + self.bitmap.height
        )


def split_line(font, text, width):
    """Splits text at a space into two lines; the first fits width."""
    if font.width(text) <= width:
        return text, ""
    words = text.split(" ")
    for n in range(len(words) - 1, 0, -1):
        a = " ".join(words[:n])
        if font.width(a) <= width:
            return a, " ".join(words[n:])
    return text, ""


def rect(colour, x, y, w, h):
    """A solid vectorio.Rectangle. Returns (shape, palette)."""
    import vectorio

    p = displayio.Palette(1)
    p[0] = colour
    return vectorio.Rectangle(pixel_shader=p, width=w, height=h, x=x, y=y), p
