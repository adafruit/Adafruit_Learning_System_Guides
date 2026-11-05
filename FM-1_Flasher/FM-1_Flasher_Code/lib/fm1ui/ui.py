# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Look and drawing helpers: the Firmware Hub's colours, fonts, panels, text,
buttons and icons, as plain displayio objects (CircuitPython or Blinka)."""
# Disabled for the Learn Guides lint check: modules are imported where they're needed, to keep RAM
# free and start-up quick; some drawing and protocol functions are long by nature.
# pylint: disable=import-outside-toplevel,too-many-locals
import bitmaptools
import displayio
import vectorio

# thefirmwarehub.com palette
BG = 0x151213
PANEL = 0x221E1F
LINE = 0x3A3435
FG = 0xEFE8E1
TEXT = 0xD8D0C9
DIM = 0xA39A94
CYAN = 0x42F5F5
OK = 0x5FE3A1
WARN = 0xF2C46D
BAD = 0xFF6A5C
PINK = 0xF4C0CB
HEART = 0xFF60BE
BEIGE = 0xE6D1B9
THUMB_BG = 0x0E0C0D
# Pressed: a lit outline and a lighter fill (a darker one on cyan buttons)
PRESSED = 0x34484A
CYAN_PRESSED = 0x2AB3B3

KIND_COLORS = {
    "groove": CYAN, "synth": PINK, "drums": 0xFF9A5C, "chords": 0xA870E8,
    "tracker": OK, "dev": 0xAFD9F4, "official": BEIGE, "other": 0xC3CBD6,
}

FONT_DIR = "/fonts"
TITLE = "inter-bold-22"
NAME = "inter-bold-14"
BODY = "inter-regular-14"
SMALL = "mono-bold-12"

_fonts = {}
_palettes = {}
_text_palettes = {}


def kind_color(kind):
    return KIND_COLORS.get(kind, BEIGE)


class Font:
    """A packed 1-bit font from tools/make_fonts.py (.fmf): one sheet Bitmap
    plus a metrics table, so a font costs a few KB however many glyphs it has."""

    def __init__(self, path):
        with open(path, "rb") as f:
            head = f.read(12)
            if head[:4] != b"FMF1":
                raise ValueError("not an FMF1 font: " + path)
            self.ascent, self.descent, self.cap = head[4], head[5], head[6]
            self.count = head[8] | (head[9] << 8)
            sheet_w = head[10] | (head[11] << 8)
            self.table = bytearray(f.read(8 * self.count))
            # Give each glyph at least the room its ink takes. Advances are
            # rounded per glyph, and the 1-bit "m" of inter-regular-14 ends
            # 1 px past its advance: "from the" read as "fromthe". Not in the
            # monospace font, whose columns must stay even.
            t = self.table
            proportional = t[(ord("i") - 32) * 8 + 6] != t[(ord("m") - 32) * 8 + 6]
            for o in range(0, len(t) if proportional else 0, 8):
                left = t[o + 5] - 256 if t[o + 5] > 127 else t[o + 5]
                if t[o + 4] and left + t[o + 4] > t[o + 6]:
                    t[o + 6] = left + t[o + 4]
            if proportional:
                t[6] += 1  # and 1 px more word space (row 0 is the space)
            self.height = self.ascent + self.descent
            self.sheet = displayio.Bitmap(sheet_w, self.height, 2)
            bitmaptools.readinto(self.sheet, f, 1, reverse_pixels_in_element=True)  # MSB first
        self.fallback = self._find(ord("?"))

    def _find(self, code):
        """Offset of a glyph's table row. ASCII is stored first, in order."""
        if 32 <= code < 127:
            return (code - 32) * 8
        t = self.table
        lo, hi = code & 0xFF, code >> 8
        for o in range(95 * 8, len(t), 8):
            if t[o] == lo and t[o + 1] == hi:
                return o
        return self.fallback

    def width(self, s):
        t = self.table
        w = 0
        for ch in s:
            w += t[self._find(ord(ch)) + 6]
        return w

    def render(self, s):
        """(Bitmap, x offset): the text in a fresh 1-bit bitmap. The offset is
        where the pen started, for glyphs that reach left of it."""
        t = self.table
        rows = [self._find(ord(ch)) for ch in s]
        pad = 0
        if rows:
            left = t[rows[0] + 5]
            pad = (256 - left) if left > 127 else 0
        w = pad
        for o in rows:
            w += t[o + 6]
        bmp = displayio.Bitmap(max(1, w + 2), self.height, 2)
        pen = pad
        for o in rows:
            gw = t[o + 4]
            if gw:
                left = t[o + 5]
                left = left - 256 if left > 127 else left
                sx = t[o + 2] | (t[o + 3] << 8)
                x = pen + left
                if x >= 0 and x + gw <= bmp.width:
                    bitmaptools.blit(bmp, self.sheet, x, 0, x1=sx, y1=0, x2=sx + gw, y2=self.height)
            pen += t[o + 6]
        return bmp, pad


def font(name):
    f = _fonts.get(name)
    if f is None:
        f = _fonts[name] = Font("%s/%s.fmf" % (FONT_DIR, name))
    return f


def title_font(s):
    """TITLE, or NAME for text it can't draw: TITLE is ASCII only."""
    for ch in s:
        if not 32 <= ord(ch) < 127:
            return NAME
    return TITLE


def width(name, s):
    return font(name).width(s)


def palette(color):
    """One shared single-colour palette per colour."""
    p = _palettes.get(color)
    if p is None:
        p = displayio.Palette(1)
        p[0] = color
        _palettes[color] = p
    return p


def text_palette(color):
    """Transparent background, `color` ink; shared per colour."""
    p = _text_palettes.get(color)
    if p is None:
        p = displayio.Palette(2)
        p.make_transparent(0)
        p[1] = color
        _text_palettes[color] = p
    return p


def rect(x, y, w, h, color):
    return vectorio.Rectangle(pixel_shader=palette(color), width=w, height=h, x=x, y=y)


def panel(x, y, w, h, color, cut=4):
    """A rectangle with chamfered corners, the hub's rounded cards at this size."""
    pts = [
        (cut, 0),
        (w - cut, 0),
        (w, cut),
        (w, h - cut),
        (w - cut, h),
        (cut, h),
        (0, h - cut),
        (0, cut),
    ]
    return vectorio.Polygon(pixel_shader=palette(color), points=pts, x=x, y=y)


def outlined(x, y, w, h, fill, edge, cut=4):
    g = displayio.Group()
    g.append(panel(x, y, w, h, edge, cut))
    g.append(panel(x + 1, y + 1, w - 2, h - 2, fill, cut - 1 if cut > 1 else 0))
    return g


class Text(displayio.Group):
    """One line of text, placed by its ink: anchor (ax, ay) is a fraction of
    the text's width and cap height (ay 0 = top of the capitals, 1 = baseline).
    A Group holding one TileGrid, replaced when the text changes (a TileGrid
    can't take a bitmap of another size)."""

    def __init__(self, name, s, color, x, y, anchor=(0, 0)):
        super().__init__()
        self.font_name = name
        self.text = s
        self.anchor = anchor
        self.at = (x, y)
        self._color = color
        self._draw()

    def _draw(self):
        f = font(self.font_name)
        bmp, pad = f.render(self.text)
        if len(self):
            self.pop()
        self.append(displayio.TileGrid(bmp, pixel_shader=text_palette(self._color)))
        ax, ay = self.anchor
        self.x = int(self.at[0] - ax * f.width(self.text)) - pad
        self.y = int(self.at[1] - ay * f.cap) - (f.ascent - f.cap)

    def set(self, s):
        """Change the text and keep it anchored."""
        if s != self.text:
            self.text = s
            self._draw()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._color = c
        self[0].pixel_shader = text_palette(c)


def text(name, s, color, x, y, anchor=(0, 0)):
    return Text(name, s, color, x, y, anchor)


def gear(cx, cy, r, color, hole):
    """An eight-toothed gear of outer radius r centred at (cx, cy), with a
    hole in the colour `hole` (the button's fill)."""
    import math
    inner = r * 0.72
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        for rad, da in ((inner, -0.30), (r, -0.17), (r, 0.17), (inner, 0.30)):
            pts.append((round(rad * math.cos(a + da)), round(rad * math.sin(a + da))))
    g = displayio.Group()
    g.append(vectorio.Polygon(pixel_shader=palette(color), points=pts, x=cx, y=cy))
    g.append(vectorio.Circle(pixel_shader=palette(color), radius=round(inner), x=cx, y=cy))
    g.append(vectorio.Circle(pixel_shader=palette(hole), radius=max(2, round(r * 0.3)), x=cx, y=cy))
    return g


def triangle(x, y, w, h, color, left):
    pts = [(w, 0), (0, h // 2), (w, h)] if left else [(0, 0), (w, h // 2), (0, h)]
    return vectorio.Polygon(pixel_shader=palette(color), points=pts, x=x, y=y)


# 13x11 heart: '#' is the outline, '+' is filled in only for a favourite
_HEART = (
    "..###...###..",
    ".#+++#.#+++#.",
    "#+++++#+++++#",
    "#+++++++++++#",
    "#+++++++++++#",
    ".#+++++++++#.",
    "..#+++++++#..",
    "...#+++++#...",
    "....#+++#....",
    ".....#+#.....",
    "......#......",
)
_hearts = {}


def heart(filled, color=HEART, dim=DIM):
    """A TileGrid-ready (bitmap, palette) heart; filled or outline."""
    key = filled
    if key not in _hearts:
        bmp = displayio.Bitmap(13, len(_HEART), 2)
        for y, row in enumerate(_HEART):
            for x, c in enumerate(row):
                if c == "#" or (filled and c == "+"):
                    bmp[x, y] = 1
        pal = displayio.Palette(2)
        pal.make_transparent(0)
        pal[1] = color if filled else dim
        _hearts[key] = (bmp, pal)
    return _hearts[key]


def heart_tile(filled, x, y):
    bmp, pal = heart(filled)
    return displayio.TileGrid(bmp, pixel_shader=pal, x=x, y=y)


def set_heart(tile, filled):
    bmp, pal = heart(filled)
    tile.bitmap = bmp
    tile.pixel_shader = pal


def press(group):
    """Show an outlined() group (a button, card or tab) as pressed. Returns
    what release() needs to put it back. The shapes get other shared
    palettes; the palettes themselves never change."""
    if hasattr(group, "press"):  # e.g. fm1ui.flat.Highlight
        return group.press()
    edge, fill = group[0], group[1]
    old = (edge.pixel_shader, fill.pixel_shader)
    cyan = fill.pixel_shader is palette(CYAN)
    edge.pixel_shader = palette(FG if cyan else CYAN)
    fill.pixel_shader = palette(CYAN_PRESSED if cyan else PRESSED)
    return old


def release(group, old):
    if hasattr(group, "release"):
        group.release(old)
        return
    group[0].pixel_shader, group[1].pixel_shader = old


class Button:
    """A panel with a centred label; `rect` is its hit area."""

    def __init__(self, label, x, y, w, h, fill=PANEL, edge=LINE, color=FG, name=NAME):
        self.rect = (x, y, w, h)
        self.group = outlined(x, y, w, h, fill, edge)
        self.label = text(name, label, color, x + w // 2, y + h // 2, (0.5, 0.5))
        self.group.append(self.label)

    def hit(self, x, y, slack=10):
        """In the button, or within `slack` px: a fingertip lands 10-15 px
        from where it's aimed. Buttons are laid out at least 2 * slack apart."""
        rx, ry, rw, rh = self.rect
        return rx - slack <= x < rx + rw + slack and ry - slack <= y < ry + rh + slack


# Pictures go into a fixed pool of 80x80, 16-colour bitmaps made once, at
# startup, and reused by every screen: allocated per screen, they fragment
# the heap until a 3 KB thumbnail no longer fits. A page's six thumbnails
# take one slot each; the detail screen's 160 px picture takes four. Each
# slot is 3.2 KB, so six cards a page rather than eight saves 6.4 KB.
TILE = 80
SLOTS = 6
_slots = []


def slots():
    if not _slots:
        for _ in range(SLOTS):
            _slots.append(displayio.Bitmap(TILE, TILE, 16))
    return _slots


def load_tiles(path, bitmaps):
    """Read an 8-bit indexed BMP of TILE-wide tiles stacked top to bottom
    (tools/make_sd.py) into `bitmaps`, one tile each; returns its Palette.
    The pictures are read into RAM because the card can't be read while the
    display draws (they share one SPI bus), so OnDiskBitmap won't do."""
    with open(path, "rb") as f:
        head = f.read(54)
        if head[:2] != b"BM":
            raise ValueError("not a BMP")
        u32 = (
            lambda o: head[o] | (head[o + 1] << 8) | (head[o + 2] << 16) | (head[o + 3] << 24)
        )  # noqa: E731
        offset, size, w, h = u32(10), u32(14), u32(18), u32(22)
        bpp, compression, colours = head[28], u32(30), u32(46) or 256
        if bpp != 8 or compression or colours > 16 or w != TILE or h != TILE * len(bitmaps):
            raise ValueError(
                "needs an 8-bit BMP of %d %dx%d tiles, 16 colours" % (len(bitmaps), TILE, TILE)
            )
        f.seek(14 + size)
        pal_bytes = f.read(4 * colours)
        pal = displayio.Palette(colours)
        for i in range(colours):
            pal[i] = (pal_bytes[4 * i + 2] << 16) | (pal_bytes[4 * i + 1] << 8) | pal_bytes[4 * i]
        f.seek(offset)
        for bmp in reversed(bitmaps):  # bottom-up: the last tile comes first
            bitmaptools.readinto(bmp, f, 8, reverse_rows=True)
    return pal


def shrink(src, factor):
    """A new bitmap `factor` times smaller, nearest neighbour: the pictures
    are 480 px pixel art at 6x in a tile, so 2x keeps them sharp. A fresh
    bitmap per call, which only the Metro's 320x240 layout uses (PSRAM)."""
    w, h = src.width // factor, src.height // factor
    dst = displayio.Bitmap(w, h, 16)
    for yy in range(h):
        sy = yy * factor
        for xx in range(w):
            dst[xx, yy] = src[xx * factor, sy]
    return dst


def thumbnail(path, x, y, size, placeholder, first_slot=0):
    """The firmware's picture in pool slots from `first_slot` (one for an
    80 px thumbnail, four for a 160 px picture), or a placeholder panel with
    `placeholder` text when there is no picture."""
    n = size // TILE
    try:
        if n == 0:  # smaller than a tile (the 320x240 layout): shrink one
            tile = slots()[first_slot]
            pal = load_tiles(path, [tile])
            g = displayio.Group()
            g.append(displayio.TileGrid(shrink(tile, TILE // size), pixel_shader=pal, x=x, y=y))
            return g
        tiles = slots()[first_slot:first_slot + n * n]
        pal = load_tiles(path, tiles)
        g = displayio.Group()
        for i, bmp in enumerate(tiles):
            g.append(
                displayio.TileGrid(
                    bmp, pixel_shader=pal, x=x + (i % n) * TILE, y=y + (i // n) * TILE
                )
            )
        return g
    except (OSError, ValueError) as e:
        if getattr(e, "errno", None) != 2:  # a missing picture is normal (stock)
            print("no picture:", path, repr(e))
        g = displayio.Group()
        g.append(rect(x, y, size, size, THUMB_BG))
        g.append(
            text(
                TITLE if size > 100 else NAME,
                placeholder,
                BEIGE,
                x + size // 2,
                y + size // 2,
                (0.5, 0.5),
            )
        )
        return g
