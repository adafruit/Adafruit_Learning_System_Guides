# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Load classic Winamp skins (.wsz) in CircuitPython.
"""

import os
import struct
import array
import zlib
import displayio
import bitmaptools
import terminalio

# helpers
def _to_str(raw):
    try:
        return raw.decode("utf-8")
    except Exception: # pylint: disable=broad-except
        # cp1252 / cp437 names and text files
        return "".join(chr(c) if c < 128 else "?" for c in raw)

def _is_dir(path):
    try:
        return bool(os.stat(path)[0] & 0x4000)
    except OSError:
        return False

def _rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# pylint: disable=too-many-lines, too-many-locals, too-many-branches
# #pylint: disable=too-many-statements, line-too-long
# unpack the .WSZ file
class SkinArchive:
    """Case-insensitive file access to a .wsz"""

    def __init__(self, path):
        self.path = path
        self.is_dir = _is_dir(path)
        self._entries = {}
        if self.is_dir:
            for name in os.listdir(path):
                self._entries[name.lower()] = path.rstrip("/") + "/" + name
        else:
            self._scan_zip()

    def _scan_zip(self):
        with open(self.path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            tail_len = min(size, 65536 + 22)
            f.seek(size - tail_len)
            tail = f.read(tail_len)
            eocd = tail.rfind(b"PK\x05\x06")
            if eocd < 0:
                raise ValueError("%s is not a zip/.wsz file" % self.path)
            count, cd_size, cd_offset = struct.unpack_from("<HII", tail, eocd + 10)
            f.seek(cd_offset)
            cd = f.read(cd_size)
        pos = 0
        for _ in range(count):
            if cd[pos : pos + 4] != b"PK\x01\x02":
                break
            flags, method = struct.unpack_from("<HH", cd, pos + 8)
            csize, usize, nlen, elen, clen = struct.unpack_from("<IIHHH", cd, pos + 20)
            local = struct.unpack_from("<I", cd, pos + 42)[0]
            name = _to_str(cd[pos + 46 : pos + 46 + nlen]).replace("\\", "/")
            pos += 46 + nlen + elen + clen
            if name.endswith("/") or flags & 1:  # folder, or encrypted
                continue
            depth = name.count("/")
            base = name.rsplit("/", 1)[-1].lower()
            old = self._entries.get(base)
            if old is None or depth < old[3]:  # prefer the shallowest copy
                self._entries[base] = (method, csize, usize, depth, local)

    def names(self):
        return list(self._entries.keys())

    def has(self, name):
        return name.lower() in self._entries

    def read(self, name):
        """Return the file's bytes, or None if the skin doesn't have it."""
        entry = self._entries.get(name.lower())
        if entry is None:
            return None
        if self.is_dir:
            with open(entry, "rb") as f:
                return f.read()
        method, csize, _usize, _depth, local = entry
        with open(self.path, "rb") as f:
            f.seek(local)
            hdr = f.read(30)
            if hdr[:4] != b"PK\x03\x04":
                raise ValueError("bad zip local header for " + name)
            nlen, elen = struct.unpack_from("<HH", hdr, 26)
            f.seek(local + 30 + nlen + elen)
            data = f.read(csize)
        if method == 0:
            return data
        if method == 8:
            return zlib.decompress(data, -15)  # raw deflate stream
        raise ValueError("%s uses unsupported zip method %d" % (name, method))

# BMP decoding
def _rle_decode(data, pos, w, h, four_bit):
    """Decode BI_RLE8/BI_RLE4 into a w*h index buffer (row 0 = bottom)."""
    out = bytearray(w * h)
    x = y = 0
    n = len(data)
    while pos + 1 < n and y < h:
        count = data[pos]
        val = data[pos + 1]
        pos += 2
        row = y * w
        if count:  # encoded run
            if four_bit:
                hi, lo = val >> 4, val & 15
                for i in range(count):
                    if x < w:
                        out[row + x] = lo if i & 1 else hi
                    x += 1
            else:
                end = min(x + count, w)
                if x < end:
                    out[row + x : row + end] = bytes((val,)) * (end - x)
                x += count
        elif val == 0:  # end of line
            x = 0
            y += 1
        elif val == 1:  # end of bitmap
            break
        elif val == 2:  # delta
            x += data[pos]
            y += data[pos + 1]
            pos += 2
        else:  # absolute run of `val` pixels, padded to 16 bits
            if four_bit:
                for i in range(val):
                    b = data[pos + (i >> 1)]
                    if x < w:
                        out[row + x] = b & 15 if i & 1 else b >> 4
                    x += 1
                pos += (((val + 1) >> 1) + 1) & ~1
            else:
                end = min(x + val, w)
                if x < end:
                    out[row + x : row + end] = data[pos : pos + end - x]
                x += val
                pos += (val + 1) & ~1
    return out


class Image:
    """A bitmap and what is needed to show it"""

    def __init__(self, bitmap, shader, count, black=0):
        self.bitmap = bitmap
        self.shader = shader
        self.count = count
        self.black = black

def decode_bmp(data):
    """Decode BMP bytes. Returns (bitmap, colors, value_count, black)"""
    if data is None or data[:2] != b"BM":
        raise ValueError("not a BMP file")
    pix_off = struct.unpack_from("<I", data, 10)[0]
    dib = struct.unpack_from("<I", data, 14)[0]
    if dib == 12:  # OS/2 BITMAPCOREHEADER
        w, h, _planes, bpp = struct.unpack_from("<HHHH", data, 18)
        comp, ncolors, entry = 0, 0, 3
    else:
        w, h, _planes, bpp, comp = struct.unpack_from("<iiHHI", data, 18)
        ncolors = struct.unpack_from("<I", data, 46)[0]
        entry = 4
    top_down = h < 0
    h = abs(h)
    pal_off = 14 + dib
    masks = None
    if comp in (3, 6):  # BI_BITFIELDS / BI_ALPHABITFIELDS
        masks = struct.unpack_from("<III", data, 54)
        if dib == 40:
            pal_off += 12 if comp == 3 else 16

    if bpp <= 8:
        count = 1 << bpp
        colors = [0] * count  # unused entries are black
        used = min(ncolors or count, count)
        for i in range(used):
            o = pal_off + i * entry
            if o + 3 > len(data):
                used = i
                break
            colors[i] = (data[o + 2] << 16) | (data[o + 1] << 8) | data[o]
        if 0 in colors:
            black = colors.index(0)
        else:  # palette full and no black in it: use its darkest color
            black = min(range(count), key=lambda i: sum(_rgb888(colors[i])))
    else:
        count, colors, black = 65536, None, 0

    bitmap = displayio.Bitmap(w, h, count)

    if comp in (1, 2):  # RLE8 / RLE4: always bottom-up
        idx = _rle_decode(data, pix_off, w, h, comp == 2)
        for oy in range(h):
            r = (h - 1 - oy) * w
            bitmaptools.arrayblit(bitmap, idx[r : r + w], 0, oy, w, oy + 1)
        return bitmap, colors, count, black

    stride = ((w * bpp + 31) // 32) * 4
    xs = range(w)
    for oy in range(h):
        src_row = oy if top_down else h - 1 - oy
        o = pix_off + src_row * stride
        row = data[o : o + stride]
        if len(row) < stride:
            break  # truncated file; leave the rest as is
        if bpp == 8:
            vals = row[:w]
        elif bpp == 4:
            vals = bytearray((row[x >> 1] & 15) if x & 1 else (row[x >> 1] >> 4) for x in xs)
        elif bpp == 1:
            vals = bytearray((row[x >> 3] >> (7 - (x & 7))) & 1 for x in xs)
        elif bpp == 24:
            vals = array.array("H", [_rgb565(row[3 * x + 2],
                                             row[3 * x + 1], row[3 * x]) for x in xs])
        elif bpp == 32:
            vals = array.array("H", [_rgb565(row[4 * x + 2],
                                             row[4 * x + 1], row[4 * x]) for x in xs])
        elif bpp == 16:
            if masks and masks[1] == 0x07E0:  # already RGB565
                vals = array.array("H", [row[2 * x] | (row[2 * x + 1] << 8) for x in xs])
            else:  # X1R5G5B5
                vals = array.array("H", [0] * w)
                for x in xs:
                    v = row[2 * x] | (row[2 * x + 1] << 8)
                    g = (v >> 5) & 31
                    vals[x] = ((v >> 10) & 31) << 11 | ((g << 1) | (g >> 4)) << 5 | (v & 31)
        else:
            raise ValueError("unsupported BMP depth %d" % bpp)
        bitmaptools.arrayblit(bitmap, vals, 0, oy, w, oy + 1)
    return bitmap, colors, count, black

def _rgb888(value):
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF

# text files
DEFAULT_VISCOLORS = [
    0x000000, 0x182129, 0xEF3110, 0xCE2910, 0xD65A00, 0xD66600, 0xD67300,
    0xC67B08, 0xDEA518, 0xD6B521, 0xBDDE29, 0x94DE21, 0x29CE10, 0x32BE10,
    0x39B510, 0x319C08, 0x299400, 0x188408, 0xFFFFFF, 0xD6D6DE, 0xB5BDBD,
    0xA0AAAF, 0x949CA5, 0x969696,
]

def parse_viscolor(text):
    """24 colors: 0 bg, 1 dots, 2-17 analyzer (top->bottom), 18-22 scope, 23 peaks."""
    colors = []
    for line in text.splitlines():
        nums, cur = [], ""
        for ch in line.split("//")[0] + ",":
            if ch.isdigit():
                cur += ch
            elif cur:
                nums.append(min(int(cur), 255))
                cur = ""
        if len(nums) >= 3:
            colors.append((nums[0] << 16) | (nums[1] << 8) | nums[2])
        if len(colors) == 24:
            break
    return colors + DEFAULT_VISCOLORS[len(colors) :]

def parse_pledit(text):
    """pledit.txt -> {"normal": 0x00FF00, "font": "Arial", ...} (keys lowercase)."""
    out = {}
    for line in text.splitlines():
        stripped = line.strip()
        if "=" not in stripped or stripped[0] in "[;":  # no tuple startswith in MicroPython
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value.startswith("#"):
            try:
                out[key.strip().lower()] = int(value[1:7], 16)
                continue
            except ValueError:
                pass
        out[key.strip().lower()] = value
    return out

# skin
class Skin:
    """A loaded skin. Sprite sheets decode and are cached"""

    def __init__(self, path, fallback=None):
        self.path = path
        self.archive = SkinArchive(path)
        self.fallback = fallback
        self._sheets = {}
        self._cache = {}
        self.converter = displayio.ColorConverter(
            input_colorspace=displayio.Colorspace.RGB565
        )
        txt = self.archive.read("viscolor.txt")
        if txt is not None:
            self.viscolors = parse_viscolor(_to_str(txt))
        elif fallback is not None:
            self.viscolors = fallback.viscolors
        else:
            self.viscolors = list(DEFAULT_VISCOLORS)
        txt = self.archive.read("pledit.txt")
        if txt is not None:
            self.pledit = parse_pledit(_to_str(txt))
        else:
            self.pledit = fallback.pledit if fallback else {}

    def has_sheet(self, name):
        return self.archive.has(name + ".bmp")

    def sheet(self, name):
        """Decoded sheet ("main", "cbuttons", ...) as an Image, or None."""
        name = name.lower()
        if name not in self._sheets:
            img = None
            data = self.archive.read(name + ".bmp")
            if data is not None:
                try:
                    bmp, colors, count, black = decode_bmp(data)
                    if colors is None:
                        shader = self.converter
                    else:  # one Palette per sheet, shared by every sprite cut from it
                        shader = displayio.Palette(count)
                        for i, c in enumerate(colors):
                            shader[i] = c
                    img = Image(bmp, shader, count, black)
                except (ValueError, IndexError) as err:
                    print("winamp_skin: %s.bmp: %s" % (name, err))
            if img is None and self.fallback is not None:
                img = self.fallback.sheet(name)
            self._sheets[name] = img
        return self._sheets[name]

    def release_sheets(self):
        """Drop the decoded sheets and the build cache once the UI is built."""
        self._sheets = {}
        self._cache = {}
        if self.fallback is not None:
            self.fallback.release_sheets()

    def strip(self, sheet, rects, tile_w=None, tile_h=None):
        """Copy sprite rects side by side into a tile strip (an Image)"""
        tile_w = tile_w or max(r[2] for r in rects)
        tile_h = tile_h or max(r[3] for r in rects)
        names = set((r[4] if len(r) > 4 else sheet) for r in rects)
        if len(names) != 1:
            raise ValueError("a strip's sprites must come from one sheet, not %s" % sorted(names))
        name = names.pop()
        src = self.sheet(name)
        if src is None:
            raise ValueError("%s has no usable %s.bmp (and no fallback skin does)"
                             % (self.path, name))
        out = displayio.Bitmap(tile_w * len(rects), tile_h, src.count)
        if src.black:
            out.fill(src.black)
        sb = src.bitmap
        for i, rect in enumerate(rects):
            x, y, w, h = rect[:4]
            x2 = min(x + min(w, tile_w), sb.width)
            y2 = min(y + min(h, tile_h), sb.height)
            if x < x2 and y < y2:
                bitmaptools.blit(out, sb, i * tile_w, 0, x1=x, y1=y, x2=x2, y2=y2)
        return Image(out, src.shader, src.count, src.black)

    def cached(self, key, build):
        """Build-once storage for strips shared by several TileGrids while
        windows are built (fonts, digits). Cleared by release_sheets()."""
        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key]

    def font(self):
        """text.bmp's 31x3 grid of 5x6 characters, see FONT for indices."""
        return self.cached("font", lambda: self.grid("text", 0, 0, 155, 18))

    def grid(self, sheet, x, y, w, h):
        """Copy one region (e.g. a font table) to its own Image."""
        return self.strip(sheet, [(x, y, w, h)])

# visualizer
def _fit(v, rounding):
    """Scaled size: round for tile grids whose spacing matters (text),
    ceil for standalone sprites so neighbours never leave a gap."""
    if rounding:
        return int(v + 0.5)
    n = int(v)
    return n if v - n < 1e-6 else n + 1

class Scaler:
    """Nearest-neighbour scaling of a tiled bitmap by any factor"""

    def __init__(self, tw, th, nx, ny, scale, rounding=False, value_count=65536):
        self._src_tw = tw
        self.tw, self.th = _fit(tw * scale, rounding), _fit(th * scale, rounding)
        self._cols = [t * tw + min(tw - 1, int((i + 0.5) / scale))
                      for t in range(nx) for i in range(self.tw)]
        self._rows = [t * th + min(th - 1, int((j + 0.5) / scale))
                      for t in range(ny) for j in range(self.th)]
        self._mid = displayio.Bitmap(nx * self.tw, ny * th, value_count)
        self.out = displayio.Bitmap(nx * self.tw, ny * self.th, value_count)

    def run(self, src, tile=0):
        """Scale src into self.out. With a one-tile Scaler, `tile` picks which
        tile of a horizontal strip in src is scaled."""
        mid, out = self._mid, self.out
        mh, mw = mid.height, mid.width
        blit = bitmaptools.blit
        off = tile * self._src_tw
        for x, sx in enumerate(self._cols):
            blit(mid, src, x, 0, x1=sx + off, y1=0, x2=sx + off + 1, y2=mh)
        for y, sy in enumerate(self._rows):
            blit(out, mid, 0, y, x1=0, y1=sy, x2=mw, y2=sy + 1)
        return out


def scale_bitmap(src, scale, tw=None, th=None, rounding=False, value_count=65536):
    """(scaled bitmap, tile_w, tile_h) for a bitmap of tw x th tiles.
    value_count must be the source's, so indices or colors copy unchanged."""
    tw = tw or src.width
    th = th or src.height
    sc = Scaler(tw, th, src.width // tw, src.height // th, scale, rounding, value_count)
    return sc.run(src), sc.tw, sc.th


class Visualizer:
    """Winamp-style spectrum / oscilloscope using the skin's viscolor"""

    BARS = 19

    def __init__(self, skin, x=0, y=0, scale=1, width=76, height=16):
        self.s = scale
        w = int(width * scale + 0.5)
        h = int(height * scale + 0.5)
        self.w, self.h = w, h
        self.bitmap = displayio.Bitmap(w, h, 24)
        self.palette = displayio.Palette(24)
        for i, c in enumerate(skin.viscolors):
            self.palette[i] = c
        self.tilegrid = displayio.TileGrid(self.bitmap, pixel_shader=self.palette, x=x, y=y)
        # pre-rendered layers so each frame is a few C-level blits
        dots = displayio.Bitmap(width, height, 24)
        for yy in range(1, height, 2):
            for xx in range(1, width, 2):
                dots[xx, yy] = 1
        if scale != 1:
            dots = Scaler(width, height, 1, 1, scale, True, 24).run(dots)
        self._bg = dots
        self._full = displayio.Bitmap(w, h, 24)
        for yy in range(h):
            color = 2 + min(15, yy * 16 // h)  # 2 = top .. 17 = bottom
            bitmaptools.fill_region(self._full, 0, yy, w, yy + 1, color)
        self._bars = [(int(i * 4 * scale + 0.5), int((i * 4 + 3) * scale + 0.5))
                      for i in range(self.BARS)]
        self._dot = max(1, int(scale + 0.5))
        self.peaks = [0.0] * self.BARS
        self._clear = False
        self.clear()

    def clear(self):
        if not self._clear:  # already blank: nothing to redraw
            bitmaptools.blit(self.bitmap, self._bg, 0, 0)
            self._clear = True

    def draw_bars(self, levels, peak_fall=0.02):
        """levels: up to 19 floats in 0..1 (one per bar)."""
        self._clear = False
        bitmaptools.blit(self.bitmap, self._bg, 0, 0)
        h, d = self.h, self._dot
        for i in range(min(len(levels), self.BARS)):
            lvl = max(0.0, min(1.0, levels[i]))
            x1, x2 = self._bars[i]
            px = int(lvl * h + 0.5)
            if px:
                bitmaptools.blit(self.bitmap, self._full, x1, h - px,
                                 x1=x1, y1=h - px, x2=x2, y2=h)
            pk = max(lvl, self.peaks[i] - peak_fall)
            self.peaks[i] = pk
            if pk > 0:
                py = h - d - int(pk * (h - d) + 0.5)
                bitmaptools.fill_region(self.bitmap, x1, py, x2, py + d, 23)

    def draw_scope(self, samples):
        """samples: floats in -1..1, spread across the width."""
        self._clear = False
        bitmaptools.blit(self.bitmap, self._bg, 0, 0)
        n = len(samples)
        if not n:
            return
        h, d = self.h, self._dot
        mid = (h - d) / 2
        last = None
        for x in range(self.w):
            v = samples[min(n - 1, x * n // self.w)]
            y = int(mid - max(-1.0, min(1.0, v)) * mid + 0.5)
            top, bot = (y, y) if last is None else (min(y, last), max(y, last))
            color = 18 + min(4, int(abs(y - mid) / self.s) // 2)
            bitmaptools.fill_region(self.bitmap, x, top, x + 1, bot + d, color)
            last = y

# text helpers
_FONT_ROWS = (
    'abcdefghijklmnopqrstuvwxyz"@',
    "0123456789\u2026.:()-'!_+\\/[]^&%,=$#",
    "\u00c5\u00d6\u00c4?*",
)
FONT = {}
for _r, _chars in enumerate(_FONT_ROWS):
    for _c, _ch in enumerate(_chars):
        FONT[_ch] = _r * 31 + _c
FONT.update({"<": FONT["["], ">": FONT["]"], "{": FONT["["], "}": FONT["]"]})
SPACE = 30  # row 0, column 30

# accented / typographic characters -> closest ASCII, for fonts without them
_FOLD = {}
for _src, _dst in (
    ("\u00c0\u00c1\u00c2\u00c3\u00c4\u00c5\u00c7\u00c8\u00c9\u00ca\u00cb\u00cc\u00cd\u00ce\u00cf\u00d1"
     "\u00d2\u00d3\u00d4\u00d5\u00d6\u00d8\u00d9\u00da\u00db\u00dc\u00dd", "AAAAAACEEEEIIIINOOOOOOUUUUY"),
    ("\u00e0\u00e1\u00e2\u00e3\u00e4\u00e5\u00e7\u00e8\u00e9\u00ea\u00eb\u00ec\u00ed\u00ee\u00ef\u00f1"
     "\u00f2\u00f3\u00f4\u00f5\u00f6\u00f8\u00f9\u00fa\u00fb\u00fc\u00fd\u00ff","aaaaaaceeeeiiiinoooooouuuuyy"),
    # curly quotes, low quotes, dashes, ellipsis, acute accent, sharp s, ae
    ("\u2018\u2019\u201a\u201c\u201d\u201e\u2013\u2014\u2026\u00b4\u00df\u00e6\u00c6",
     "'''\"\"\"--.'saA"),
):
    for _i, _c in enumerate(_src):
        _FOLD[_c] = _dst[_i]


def _font_index(ch):
    """Tile index in text.bmp for a character (folding accents), or SPACE."""
    i = FONT.get(ch)
    if i is None:
        i = FONT.get(ch.lower())
    if i is None and ch in _FOLD:
        i = FONT.get(_FOLD[ch].lower())
    return SPACE if i is None else i


def mmss(seconds):
    m, s = divmod(int(seconds), 60)
    return "%d:%02d" % (m, s)


def _write(tg, text, n):
    """Write text into a TileGrid built on Skin.font()."""
    for i in range(n):
        tg[i] = _font_index(text[i]) if i < len(text) else SPACE


def _spline(ys, step):
    """Natural cubic spline through evenly spaced ys, sampled every pixel."""
    n = len(ys) - 1
    h = float(step)
    # solve M[i-1] + 4M[i] + M[i+1] = 6(y[i+1] - 2y[i] + y[i-1]) / h^2
    m = [0.0] * (n + 1)
    c = [0.0] * (n + 1)
    d = [0.0] * (n + 1)
    for i in range(1, n):
        rhs = 6.0 * (ys[i + 1] - 2 * ys[i] + ys[i - 1]) / (h * h)
        denom = 4.0 - c[i - 1]
        c[i] = 1.0 / denom
        d[i] = (rhs - d[i - 1]) / denom
    for i in range(n - 1, 0, -1):
        m[i] = d[i] - c[i] * m[i + 1]
    out = []
    for i in range(n):
        y0, y1, m0, m1 = ys[i], ys[i + 1], m[i], m[i + 1]
        for t in range(step if i < n - 1 else step + 1):
            a = h - t
            out.append(
                (m0 * a * a * a + m1 * t * t * t) / (6 * h)
                + (y0 / h - m0 * h / 6) * a
                + (y1 / h - m1 * h / 6) * t
            )
    return out


class Frames:
    """A sprite showing one of many same-size frames"""

    def __init__(self, win, strip, tw, th, x, y):
        self.strip = strip.bitmap
        self.frame = None
        if win.k == 1:
            self.scaler = None
            self.tilegrid = win._add(strip, x, y, tw, th)
        else:
            self.scaler = Scaler(tw, th, 1, 1, win.k, value_count=strip.count)
            self.tilegrid = win._add(Image(self.scaler.out, strip.shader, strip.count),
                                     x, y, native=True)

    def show(self, i):
        if i == self.frame:
            return
        self.frame = i
        if self.scaler is None:
            self.tilegrid[0] = i
        else:
            self.scaler.run(self.strip, i)

# window base class
class SkinWindow(displayio.Group):
    """Shared sprite placement, buttons, focus, touch"""

    def __init__(self, skin, x, y, scale, width, height):
        whole = scale == int(scale)
        super().__init__(x=x, y=y, scale=int(scale) if whole else 1)
        self.s = scale  # screen pixels per skin pixel
        self.k = 1 if whole else scale  # multiplier for positions in this group
        self.skin = skin
        self.win_w = width
        self.win_h = height
        self._hot = []  # (name, x, y, w, h); later entries win
        self._buttons = {}  # name -> (TileGrid, kind)
        self._toggled = {}
        self._focus_tgs = []
        self._focused = None

    # ---- construction helpers ----
    def P(self, v):
        """Skin coordinate -> coordinate inside this group."""
        return int(v * self.k + 0.5)

    def _add(self, img, x, y, tw=None, th=None, width=1, height=1,
             rounding=False, key=None, native=False):
        """Place an Image of tw x th tiles at skin position (x, y)"""
        bmp = img.bitmap
        tw = tw or bmp.width
        th = th or bmp.height
        if self.k != 1 and not native:
            k = self.k
            def build(b=bmp, tw=tw, th=th, count=img.count):
                return scale_bitmap(b, k, tw, th, rounding, count)
            if key is not None:
                bmp, tw, th = self.skin.cached((key, k, rounding), build)
            else:
                bmp, tw, th = build()
        tg = displayio.TileGrid(bmp, pixel_shader=img.shader,
                                x=self.P(x), y=self.P(y),
                                tile_width=tw, tile_height=th,
                                width=width, height=height)
        self.append(tg)
        return tg

    def _sprite(self, sheet, rects, x, y, width=1, height=1):
        """TileGrid whose tile N shows rects[N]; width/height repeat tile 0."""
        tw = max(r[2] for r in rects)
        th = max(r[3] for r in rects)
        return self._add(self.skin.strip(sheet, rects, tw, th), x, y, tw, th, width, height)

    def _hotspot(self, name, x, y, w, h):
        self._hot.append((name, x, y, w, h))

    def _button(self, name, tg, x, y, w, h, kind="push"):
        """kind: 'push' (tiles normal/pressed), 'toggle' (tile = lit*2 + pressed),
        or 'overlay' (single pressed tile, hidden when released)."""
        self._buttons[name] = (tg, kind)
        self._toggled[name] = False
        if kind == "overlay":
            tg.hidden = True
        self._hotspot(name, x, y, w, h)

    def _focusable(self, tg):
        self._focus_tgs.append(tg)
        return tg

    # ---- state ----
    def press(self, name, down=True):
        """Show a button held down / released (no-op for plain hotspots)."""
        if name not in self._buttons:
            return
        tg, kind = self._buttons[name]
        if kind == "overlay":
            tg.hidden = not down
        else:
            tg[0] = (2 if kind == "toggle" and self._toggled[name] else 0) + (1 if down else 0)

    def set_toggle(self, name, on):
        self._toggled[name] = bool(on)
        self.press(name, False)

    def toggled(self, name):
        return self._toggled.get(name, False)

    def set_focused(self, focused):
        """Winamp draws the focused window's title bar highlighted."""
        if focused == self._focused:
            return  # title bars are wide: don't redraw them for nothing
        self._focused = focused
        for tg in self._focus_tgs:
            for i in range(tg.width * tg.height):
                tg[i] = 1 if focused else 0

    # ---- touch ----
    def to_skin(self, sx, sy):
        """Screen pixel -> window skin pixel."""
        return int((sx - self.x) // self.s), int((sy - self.y) // self.s)

    def contains(self, sx, sy):
        if self.hidden:
            return False
        x, y = self.to_skin(sx, sy)
        return 0 <= x < self.win_w and 0 <= y < self.win_h

    def hit_test(self, x, y):
        """(name, fx, fy) for a point in skin pixels, else (None, 0, 0).

        fx/fy are 0..1 across the control, handy for sliders.
        """
        for name, hx, hy, hw, hh in reversed(self._hot):
            if hx <= x < hx + hw and hy <= y < hy + hh:
                return name, (x - hx) / max(1, hw - 1), (y - hy) / max(1, hh - 1)
        return None, 0.0, 0.0

    def fraction(self, name, x, y):
        """(fx, fy) of a skin point relative to a named control, clamped to
        0..1, so a slider keeps tracking when the finger drifts off it."""
        for hname, hx, hy, hw, hh in self._hot:
            if hname == name:
                fx = (x - hx) / max(1, hw - 1)
                fy = (y - hy) / max(1, hh - 1)
                return max(0.0, min(1.0, fx)), max(0.0, min(1.0, fy))
        return 0.0, 0.0

# main window
_CBUTTONS = (  # name, sheet x, normal y, pressed y, w, h, window x, window y
    ("previous", 0, 0, 18, 23, 18, 16, 88),
    ("play", 23, 0, 18, 23, 18, 39, 88),
    ("pause", 46, 0, 18, 23, 18, 62, 88),
    ("stop", 69, 0, 18, 23, 18, 85, 88),
    ("next", 92, 0, 18, 22, 18, 108, 88),
    ("eject", 114, 0, 16, 22, 16, 136, 89),
)
_TITLE_BUTTONS = (  # name, normal (x, y), pressed (x, y), window x
    ("options", (0, 0), (0, 9), 6),
    ("minimize", (9, 0), (9, 9), 244),
    ("shade", (0, 18), (9, 18), 254),
    ("close", (18, 0), (18, 9), 264),
)


class MainWindow(SkinWindow):
    """The 275x116 Winamp main window."""

    WIDTH = 275
    HEIGHT = 116

    def __init__(self, skin, x=0, y=0, scale=1):
        super().__init__(skin, x, y, scale, 275, 116)
        self._title = None  # so the first set_title() always draws
        self._title_pos = 0

        self._add(skin.grid("main", 0, 0, 275, 116), 0, 0)
        self._focusable(self._sprite("titlebar", [(27, 15, 275, 14), (27, 0, 275, 14)], 0, 0))
        self._hotspot("titlebar", 0, 0, 275, 14)
        for name, normal, pressed, wx in _TITLE_BUTTONS:
            tg = self._sprite("titlebar", [normal + (9, 9), pressed + (9, 9)], wx, 3)
            self._button(name, tg, wx, 3, 9, 9)
        self._add(skin.grid("titlebar", 304, 0, 8, 43), 10, 22)  # clutter bar

        # status: play/pause/stop indicator, "working" sliver, time
        self._status = self._sprite("playpaus", [(0, 0, 9, 9), (9, 0, 9, 9), (18, 0, 9, 9)], 26, 28)
        self._work = self._sprite("playpaus", [(36, 0, 3, 9), (39, 0, 3, 9)], 24, 28)
        digits = "nums_ex" if skin.has_sheet("nums_ex") else "numbers"
        dstrip = skin.strip(digits, [(9 * i, 0, 9, 13) for i in range(11)])  # 10 = blank
        self._digits = [self._add(dstrip, dx, 26, 9, 13, key="digits")
                        for dx in (48, 60, 78, 90)]
        self._hotspot("time", 36, 26, 63, 13)

        # text: marquee, kbps, khz
        font = skin.font()
        self._marquee = self._add(font, 111, 27, 5, 6, width=31, rounding=True, key="font")
        self._kbps = self._add(font, 111, 43, 5, 6, width=3, rounding=True, key="font")
        self._khz = self._add(font, 156, 43, 5, 6, width=2, rounding=True, key="font")
        self._hotspot("marquee", 111, 24, 154, 12)

        self._mono = self._sprite("monoster", [(29, 12, 27, 12), (29, 0, 27, 12)], 212, 41)
        self._stereo = self._sprite("monoster", [(0, 12, 29, 12), (0, 0, 29, 12)], 239, 41)

        # volume / balance / seek bar
        self._vol_bg = Frames(self, skin.strip("volume", [(0, 15 * i, 68, 13) for i in range(28)]),
                              68, 13, 107, 57)
        self._vol_thumb = self._sprite("volume", [(15, 422, 14, 11), (0, 422, 14, 11)], 107, 58)
        self._hotspot("volume", 107, 57, 68, 13)
        self._bal_bg = Frames(self, skin.strip("balance", [(9, 15 * i, 38, 13) for i in range(28)]),
                              38, 13, 177, 57)
        self._bal_thumb = self._sprite("balance", [(15, 422, 14, 11), (0, 422, 14, 11)], 177, 58)
        self._hotspot("balance", 177, 57, 38, 13)
        # skins that cut the thumb rows off volume/balance.bmp show no thumb
        self._vol_thumb.hidden = not self._sheet_covers("volume", 433)
        self._bal_thumb.hidden = not self._sheet_covers("balance", 433)
        self._add(skin.grid("posbar", 0, 0, 248, 10), 16, 72)
        self._pos_thumb = self._sprite("posbar", [(248, 0, 29, 10), (278, 0, 29, 10)], 16, 72)
        self._hotspot("position", 16, 72, 248, 10)

        for name, sx, ny, py, w, h, wx, wy in _CBUTTONS:
            tg = self._sprite("cbuttons", [(sx, ny, w, h), (sx, py, w, h)], wx, wy)
            self._button(name, tg, wx, wy, w, h)

        for name, rects, wx, wy in (
            ("shuffle", [(28, 15 * i, 47, 15) for i in range(4)], 164, 89),
            ("repeat", [(0, 15 * i, 28, 15) for i in range(4)], 210, 89),
            ("eq", [(0, 61, 23, 12), (46, 61, 23, 12), (0, 73, 23, 12), (46, 73, 23, 12)], 219, 58),
            ("playlist", [(23, 61, 23, 12), (69, 61, 23, 12),
                          (23, 73, 23, 12), (69, 73, 23, 12)], 242, 58),
        ):
            tg = self._sprite("shufrep", rects, wx, wy)
            self._button(name, tg, wx, wy, rects[0][2], rects[0][3], kind="toggle")

        self.vis = Visualizer(skin, self.P(24), self.P(43), scale=self.k)
        self.append(self.vis.tilegrid)
        self._hotspot("visualizer", 24, 43, 76, 16)

        self.set_focused(True)
        self.set_state("stop")
        self.set_time(None)
        self.set_title("")
        self.set_info(None, None, None)
        self.set_volume(75)
        self.set_balance(0)

    def _sheet_covers(self, sheet, min_height):
        img = self.skin.sheet(sheet)
        return img is not None and img.bitmap.height >= min_height

    def set_state(self, state):
        """'play', 'pause' or 'stop'."""
        if state == getattr(self, "state", None):
            return
        self._status[0] = {"play": 0, "pause": 1}.get(state, 2)
        # (hidden = False redraws a TileGrid even if it was already showing)
        if self._work.hidden != (state != "play"):
            self._work.hidden = state != "play"
        if self._pos_thumb.hidden != (state == "stop"):
            self._pos_thumb.hidden = state == "stop"
        self.state = state

    def set_time(self, seconds):
        """Elapsed time in seconds, or None to blank the display."""
        if seconds is None:
            vals = (10, 10, 10, 10)
        else:
            m, s = divmod(int(seconds), 60)
            m %= 100
            vals = (m // 10, m % 10, s // 10, s % 10)
        if vals == getattr(self, "_time_vals", None):
            return  # unchanged: don't make the display redraw it
        self._time_vals = vals
        for tg, v in zip(self._digits, vals):
            tg[0] = v

    def set_title(self, text):
        if text == self._title:
            return  # same title: leave it (and its scroll position) alone
        self._title = text
        self._title_pos = 0
        _write(self._marquee, text, 31)

    def scroll_title(self):
        """Advance the marquee one character (call every ~0.2 s)."""
        if len(self._title) <= 31:
            return
        t = self._title + "  ***  "
        self._title_pos = (self._title_pos + 1) % len(t)
        p = self._title_pos
        _write(self._marquee, (t[p:] + t[:p])[:31], 31)

    def set_info(self, kbps, khz, stereo):
        if (kbps, khz, stereo) == getattr(self, "_info", 0):
            return
        self._info = (kbps, khz, stereo)
        _write(self._kbps, "" if kbps is None else "%3d" % kbps, 3)
        _write(self._khz, "" if khz is None else "%2d" % khz, 2)
        self._mono[0] = 1 if stereo is False else 0
        self._stereo[0] = 1 if stereo else 0

    def set_volume(self, percent):
        percent = max(0, min(100, int(percent)))
        self._vol_bg.show(percent * 27 // 100)
        self._vol_thumb.x = self.P(107 + percent * 51 / 100)
        self.volume = percent

    def set_balance(self, value):
        """-100 (left) .. 100 (right)."""
        value = max(-100, min(100, int(value)))
        self._bal_bg.show(abs(value) * 27 // 100)
        self._bal_thumb.x = self.P(177 + (value + 100) * 24 / 200)
        self.balance = value

    def set_position(self, fraction):
        """Seek bar thumb, 0.0 .. 1.0."""
        fraction = max(0.0, min(1.0, fraction))
        x = self.P(16 + fraction * (248 - 29))
        if x != self._pos_thumb.x:  # only redraw when it moves a pixel
            self._pos_thumb.x = x

    def press(self, name, down=True):
        thumbs = {"volume": self._vol_thumb, "balance": self._bal_thumb,
                  "position": self._pos_thumb}
        if name in thumbs:
            thumbs[name][0] = 1 if down else 0
        else:
            super().press(name, down)

# equalizer window
EQ_BANDS = ("60", "170", "310", "600", "1K", "3K", "6K", "12K", "14K", "16K")
EQ_SLIDERS = ("preamp",) + tuple("band%d" % i for i in range(10))

class EqWindow(SkinWindow):
    """The 275x116 equalizer window. Slider values are 0..100, 50 = 0 dB."""

    WIDTH = 275
    HEIGHT = 116

    def __init__(self, skin, x=0, y=0, scale=1):
        super().__init__(skin, x, y, scale, 275, 116)
        self._add(skin.grid("eqmain", 0, 0, 275, 116), 0, 0)
        self._focusable(self._sprite("eqmain", [(0, 149, 275, 14), (0, 134, 275, 14)], 0, 0))
        self._hotspot("eq_titlebar", 0, 0, 275, 14)
        self._button("eq_close", self._sprite("eqmain", [(0, 116, 9, 9), (0, 125, 9, 9)], 264, 3),
                     264, 3, 9, 9)
        # the shade button's normal look is part of the title bar; only the
        # pressed look is a sprite (eq_ex.bmp, or a spot in eqmain.bmp)
        if skin.has_sheet("eq_ex"):
            shade = (1, 38, 9, 9, "eq_ex")
        else:
            shade = (254, 152, 9, 9)
        self._button("eq_shade", self._sprite("eqmain", [shade], 254, 3),
                     254, 3, 9, 9, kind="overlay")

        self._button("eq_on", self._sprite("eqmain", [
            (10, 119, 26, 12), (128, 119, 26, 12), (69, 119, 26, 12), (187, 119, 26, 12)], 14, 18),
            14, 18, 26, 12, kind="toggle")
        self._button("eq_auto", self._sprite("eqmain", [
            (36, 119, 32, 12), (154, 119, 32, 12), (95, 119, 32, 12), (213, 119, 32, 12)], 40, 18),
            40, 18, 32, 12, kind="toggle")
        self._button("eq_presets", self._sprite("eqmain",
                                                [(224, 164, 44, 12), (224, 176, 44, 12)], 217, 18),
                     217, 18, 44, 12)

        bg = skin.grid("eqmain", 0, 294, 113, 19)
        self._graph_bg = bg.bitmap
        self._graph = displayio.Bitmap(113, 19, bg.count)  # drawn at 1x
        if self.k != 1:  # ... then scaled into what's shown
            self._graph_scaler = Scaler(113, 19, 1, 1, self.k, value_count=bg.count)
            self._add(Image(self._graph_scaler.out, bg.shader, bg.count), 86, 17, native=True)
        else:
            self._graph_scaler = None
            self._add(Image(self._graph, bg.shader, bg.count), 86, 17)
        colors = skin.grid("eqmain", 115, 294, 1, 19).bitmap
        self._line_colors = [colors[0, y] for y in range(19)]
        self._preamp_line = skin.grid("eqmain", 0, 314, 113, 1).bitmap

        # 11 sliders share one 28-frame background strip and one thumb strip
        frames = [(13 + (n % 14) * 15, 164 + (n // 14) * 65, 14, 63) for n in range(28)]
        bg_strip = skin.strip("eqmain", frames)
        thumb_strip = skin.strip("eqmain", [(0, 164, 11, 11), (0, 176, 11, 11)])
        self._sliders = {}
        self.values = {}
        for i, name in enumerate(EQ_SLIDERS):
            bx = 21 if i == 0 else 78 + 18 * (i - 1)
            bg = Frames(self, bg_strip, 14, 63, bx, 38)  # the 11 sliders share the 1x strip
            thumb = self._add(thumb_strip, bx + 1, 38, 11, 11, key="eqthumb")
            self._sliders[name] = (bg, thumb)
            self._hotspot(name, bx, 38, 14, 63)
            self.values[name] = 50
        for name in EQ_SLIDERS:
            self.set_slider(name, 50, redraw=False)
        self._draw_graph()

    @staticmethod
    def value_from_fy(fy):
        """Slider value for a touch at fraction fy down the 63px slider."""
        y = fy * 62 - 5.5  # center the 11px thumb under the finger
        return max(0, min(100, int(100 - y * 100 / 51 + 0.5)))

    def set_slider(self, name, value, redraw=True):
        """name: 'preamp' or 'band0'..'band9'; value 0 (-12 dB) .. 100 (+12 dB)."""
        value = max(0, min(100, int(value)))
        if redraw and value == self.values.get(name):
            return  # unchanged during a drag; skip the graph redraw
        bg, thumb = self._sliders[name]
        bg.show((value * 27 + 50) // 100)
        thumb.y = self.P(38 + (100 - value) * 51 / 100)
        self.values[name] = value
        if redraw:
            self._draw_graph()

    def set_bands(self, values, preamp=None):
        """Set all 10 bands (and optionally preamp) with one graph redraw."""
        for i, v in enumerate(values[:10]):
            self.set_slider("band%d" % i, v, redraw=False)
        if preamp is not None:
            self.set_slider("preamp", preamp, redraw=False)
        self._draw_graph()

    def press(self, name, down=True):
        if name in self._sliders:
            self._sliders[name][1][0] = 1 if down else 0
        else:
            super().press(name, down)

    def _draw_graph(self):
        g = self._graph
        bitmaptools.blit(g, self._graph_bg, 0, 0)
        # Webamp's placement for the preamp line (its y grows with the value)
        py = (self.values["preamp"] * 18 + 50) // 100
        bitmaptools.blit(g, self._preamp_line, 0, py)
        ys = [(100 - self.values["band%d" % i]) * 18 / 100 for i in range(10)]
        colors = self._line_colors
        last = int(ys[0] + 0.5)
        for x, yv in enumerate(_spline(ys, 12)):
            y = max(0, min(18, int(yv + 0.5)))
            for yy in range(min(y, last), max(y, last) + 1):
                g[2 + x, yy] = colors[yy]
            last = y
        if self._graph_scaler is not None:
            self._graph_scaler.run(g)

# playlist window
_PL_DEFAULT_COLORS = {"normal": 0x00FF00, "current": 0xFFFFFF,
                      "normalbg": 0x000000, "selectedbg": 0x0000C6}
_PL_MINI_BUTTONS = ("previous", "play", "pause", "stop", "next", "eject")
_glyph_cache = {}

def _glyph(font, ch):
    idx = _glyph_cache.get(ch)
    if idx is None:
        g = font.get_glyph(ord(ch))
        if g is None and ch in _FOLD:
            g = font.get_glyph(ord(_FOLD[ch]))
        if g is None:
            g = font.get_glyph(ord("?"))
        idx = g.tile_index
        _glyph_cache[ch] = idx
    return idx

class PlaylistWindow(SkinWindow):

    ROW_PITCH = 13

    def __init__(self, skin, x=0, y=0, scale=1, width=275, height=116):

        width = 275 + max(0, (width - 275) // 25) * 25
        height = 116 + max(0, (height - 116) // 29) * 29
        super().__init__(skin, x, y, scale, width, height)
        W, H = width, height
        mid_h = H - 58  # between the 20px top and 38px bottom
        self.tracks = []  # (title, seconds, ...) - extra items are ignored
        self._total = 0
        self.current = None
        self.selected = set()
        self.offset = 0

        # frame: tiles first, then corners and title over them
        across = (W + 24) // 25
        self._focusable(self._sprite("pledit",
                                     [(127, 21, 25, 20), (127, 0, 25, 20)], 0, 0, width=across))
        self._focusable(self._sprite("pledit", [(0, 21, 25, 20), (0, 0, 25, 20)], 0, 0))
        self._focusable(self._sprite("pledit",
                                     [(26, 21, 100, 20), (26, 0, 100, 20)], (W - 100) // 2, 0))
        self._focusable(self._sprite("pledit", [(153, 21, 25, 20), (153, 0, 25, 20)], W - 25, 0))
        self._hotspot("pl_titlebar", 0, 0, W, 20)
        self._sprite("pledit", [(0, 42, 12, 29)], 0, 20, height=mid_h // 29)
        self._sprite("pledit", [(31, 42, 20, 29)], W - 20, 20, height=mid_h // 29)
        self._sprite("pledit", [(179, 0, 25, 38)], 0, H - 38, width=across)
        self._sprite("pledit", [(0, 72, 125, 38)], 0, H - 38)
        if W >= 350:
            self._sprite("pledit", [(205, 0, 75, 38)], W - 225, H - 38)
        self._sprite("pledit", [(126, 72, 150, 38)], W - 150, H - 38)

        # title bar buttons: only their pressed look is a sprite
        self._button("pl_close", self._sprite("pledit", [(52, 42, 9, 9)], W - 11, 3),
                     W - 11, 3, 9, 9, kind="overlay")
        self._button("pl_shade", self._sprite("pledit", [(62, 42, 9, 9)], W - 21, 3),
                     W - 21, 3, 9, 9, kind="overlay")

        # track list area
        colors = dict(_PL_DEFAULT_COLORS)
        for k in colors:
            if isinstance(skin.pledit.get(k), int):
                colors[k] = skin.pledit[k]
        self.colors = colors
        list_w = W - 32
        area_pal = displayio.Palette(1)
        area_pal[0] = colors["normalbg"]
        area = displayio.Bitmap(_fit(list_w * self.k, False), _fit(mid_h * self.k, False), 1)
        self._add(Image(area, area_pal, 1), 12, 20, native=True)

        # Track text: terminalio at a whole-number scale (2x on screen when
        # the window is 2x or more), placed at the window's scaled positions.
        self._font = terminalio.FONT
        fw, fh = self._font.get_bounding_box()[:2]
        ts = 1 if self.k == 1 else max(1, int(self.k))
        pitch = max(self.P(self.ROW_PITCH), fh * ts + 1)
        top = self.P(23)
        self.cols = self.P(list_w - 4) // (fw * ts)
        self.rows = []
        self._drawn = []
        for i in range((self.P(20 + mid_h) - top) // pitch):
            pal = displayio.Palette(2)
            ry = top + i * pitch
            row = displayio.Group(scale=ts, x=self.P(14), y=ry)
            tg = displayio.TileGrid(self._font.bitmap, pixel_shader=pal,
                                    tile_width=fw, tile_height=fh, width=self.cols)
            row.append(tg)
            self.append(row)
            self.rows.append((tg, pal))
            self._drawn.append(None)
            self._hotspot("row%d" % i, 12, ry / self.k, list_w, pitch / self.k)

        # scrollbar
        self._scroll_range = (20, mid_h - 18)
        self._handle = self._sprite("pledit", [(52, 53, 8, 18), (61, 53, 8, 18)], W - 15, 20)
        self._hotspot("pl_scroll", W - 20, 20, 20, mid_h)

        # bottom: menu buttons (menus are up to the app), mini transport, times
        for name, mx in (("pl_add", 14), ("pl_remove", 43), ("pl_select", 72),
                         ("pl_misc", 101), ("pl_list", W - 44)):
            self._hotspot(name, mx, H - 30, 22, 18)
        for i, name in enumerate(_PL_MINI_BUTTONS):
            self._hotspot(name, W - 147 + 9 * i, H - 16, 9, 10)
        font = skin.font()
        self._running = self._add(font, W - 143, H - 28, 5, 6, width=15, rounding=True, key="font")
        self._mini_time = self._add(font, W - 84, H - 15, 5, 6, width=5, rounding=True, key="font")

        self.set_focused(False)
        self.set_mini_time(None)
        self._render()

    # ---- data ----
    def set_tracks(self, tracks):
        """tracks: sequences starting (title, seconds); extra items are kept
        in self.tracks for the app (path, bitrate...) but not displayed."""
        self.tracks = list(tracks)
        self._total = sum(t[1] for t in self.tracks)
        self.selected = set()
        self.current = None if not tracks else 0
        self.offset = 0
        self._render()

    def add_tracks(self, tracks):
        """Append tracks (e.g. while a scan is running). Only rows whose
        text changes are redrawn, so this stays cheap."""
        if not tracks:
            return
        self.tracks.extend(tracks)
        self._total += sum(t[1] for t in tracks)
        if self.current is None:
            self.current = 0
        self._render()

    def update_track(self, index, track):
        """Replace one track, e.g. once its duration is known."""
        self._total += track[1] - self.tracks[index][1]
        self.tracks[index] = track
        self._render()  # only rows whose text changed are redrawn

    def set_current(self, index):
        self.current = index
        if index is not None:
            self.scroll_into_view(index)
        self._render()

    def select(self, index, add=False):
        if not add:
            self.selected = set()
        if index is not None and 0 <= index < len(self.tracks):
            self.selected.add(index)
        self._render()

    def row_index(self, hot_name):
        """Track index for a 'rowN' hotspot name, or None for an empty row."""
        i = self.offset + int(hot_name[3:])
        return i if i < len(self.tracks) else None

    def max_offset(self):
        return max(0, len(self.tracks) - len(self.rows))

    def set_offset(self, offset):
        offset = max(0, min(self.max_offset(), int(offset)))
        if offset != self.offset:  # redraws are the slow part of a drag
            self.offset = offset
            self._render()

    def scroll_into_view(self, index):
        if index < self.offset:
            self.offset = index
        elif index >= self.offset + len(self.rows):
            self.offset = index - len(self.rows) + 1

    def scroll_to_fraction(self, fy):
        self.set_offset(fy * self.max_offset() + 0.5)

    def set_mini_time(self, seconds):
        text = "" if seconds is None else "%5s" % mmss(seconds)
        if text != getattr(self, "_mini_text", None):  # skip redundant redraws
            self._mini_text = text
            _write(self._mini_time, text, 5)

    def press(self, name, down=True):
        if name == "pl_scroll":
            self._handle[0] = 1 if down else 0
        else:
            super().press(name, down)

    # ---- drawing ----
    def refresh(self):
        """Redraw after changing tracks/current/selected/offset directly."""
        self._total = sum(t[1] for t in self.tracks)
        self.offset = max(0, min(self.max_offset(), self.offset))
        self._render()

    def _render(self):
        c = self.colors
        cols = self.cols
        font = self._font
        for i, (tg, pal) in enumerate(self.rows):
            idx = self.offset + i
            if idx < len(self.tracks):
                track = self.tracks[idx]
                title, secs = track[0], track[1]
                dur = mmss(secs) if secs > 0 else ""
                left = ("%d. %s" % (idx + 1, title))[: cols - len(dur) - 1]
                line = left + " " * (cols - len(left) - len(dur)) + dur
            else:
                line = ""
            bg = c["selectedbg"] if idx in self.selected else c["normalbg"]
            fg = c["current"] if idx == self.current else c["normal"]
            state = (line, bg, fg)
            if self._drawn[i] == state:
                continue  # row unchanged; skip ~50 tile writes
            self._drawn[i] = state
            pal[0] = bg
            pal[1] = fg
            for col in range(cols):
                tg[col] = _glyph(font, line[col] if col < len(line) else " ")
        top, span = self._scroll_range
        m = self.max_offset()
        self._handle.y = self.P(top + (span * self.offset / m if m else 0))
        sel = sum(self.tracks[i][1] for i in self.selected)
        running = "%s/%s" % (mmss(sel), mmss(self._total))
        if running != getattr(self, "_running_text", None):
            self._running_text = running
            _write(self._running, running, 15)
