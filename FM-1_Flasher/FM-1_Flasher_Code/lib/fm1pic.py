# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""The hub's card pictures (PNG) as the device's thumb.bmp, on CircuitPython.

thumb.bmp is an 80x80, 8-bit indexed BMP of at most 16 colours (fm1ui.ui
reads it). tools/make_sd.py makes it with Pillow; this does the same on the
device: decode the PNG, centre it on a square, sample it nearest-neighbour
(the pictures are mostly 480 px pixel art, a 6x multiple) and reduce it to 16
colours by median cut.

PNG rows are stored filtered, each against the row before (Up, Average,
Paeth) and/or its left neighbour (Sub), so every row has to be unfiltered to
reach the ones sampled. A per-byte Python loop is slow on a microcontroller
(~20 us a byte on the Metro), so rows are unfiltered a whole row at a time
with big-int arithmetic: byte-wise addition without carries between bytes,
and Sub as a running sum in log2(width) steps. Paeth picks the left byte
wherever the row above is flat (its byte equals the one to its left), which
makes it Sub there; only where the row above changes does a byte need its own
work, and it feeds the running sum as a correction. Average rows (rare in
the hub's pictures) go byte by byte.

convert() is a generator that yields every few rows, so the UI stays live.
Handles 8-bit greyscale, RGB, palette, grey+alpha and RGBA, not interlaced.
"""
# Disabled for the Learn Guides lint check: modules are imported where they're needed, to keep RAM
# free and start-up quick; some drawing and protocol functions are long by nature.
# pylint: disable=import-outside-toplevel,too-many-locals
import zlib

try:
    from ulab import numpy as _np  # CircuitPython: finds the Paeth bytes in C
except ImportError:
    _np = None

SIDE = 80
COLOURS = 16
BG = 0x0E0C0D  # what the square is padded with (make_sd.py's)
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _u32(b, o):
    return (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]


def read_png(data):
    """(width, height, colour type, palette or None, zlib data)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, palette = 8, [], None
    w = h = ct = None
    while pos + 8 <= len(data):
        n = _u32(data, pos)
        kind = bytes(data[pos + 4:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            w, h, depth, ct, interlace = _u32(body, 0), _u32(body, 4), body[8], body[9], body[12]
            if depth != 8 or interlace or ct not in _CHANNELS:
                raise ValueError(
                    "unsupported PNG (depth %d, colour type %d, interlace %d)"
                    % (depth, ct, interlace)
                )
        elif kind == b"PLTE":
            palette = [
                (body[i] << 16) | (body[i + 1] << 8) | body[i + 2]
                for i in range(0, len(body) - 2, 3)
            ]
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if w is None or not idat:
        raise ValueError("truncated PNG")
    return w, h, ct, palette, b"".join(idat)


def _sum(a):
    return _np.sum(a) if _np is not None and len(a) else sum(a)


class _Rows:
    """Unfilters a PNG's rows in order; keeps only the previous one."""

    def __init__(self, raw, width, bpp):
        self.raw = raw
        self.bpp = bpp
        self.n = width * bpp  # bytes in a row, without the filter byte
        n = self.n
        self.high = int.from_bytes(b"\x80" * n, "little")
        self.low = int.from_bytes(b"\x7f" * n, "little")
        self.full = (1 << (8 * n)) - 1
        self.prev = bytes(n)
        self.prev_int = 0
        self.pos = 0

    def _add(self, a, b):
        """Byte-wise (a + b) mod 256 of two n-byte little-endian ints."""
        return ((a & self.low) + (b & self.low)) ^ ((a ^ b) & self.high)

    def _scan(self, x):
        """Byte-wise running sum every bpp bytes: byte i gets the sum of
        bytes i, i - bpp, i - 2 bpp, ... (mod 256), doubling the stride."""
        k, n = self.bpp, self.n
        while k < n:
            x = self._add(x, (x << (8 * k)) & self.full)
            k *= 2
        return x

    def _changes(self):
        """Positions i where the row above differs from its byte bpp to the
        left (and the first pixel): where Paeth isn't simply Sub."""
        bpp = self.bpp
        d = (self.prev_int ^ (self.prev_int << (8 * bpp))) & self.full
        d |= (1 << (8 * bpp)) - 1  # the first pixel: no left neighbour
        b = d.to_bytes(self.n, "little")
        if _np is not None:
            return _np.nonzero(_np.frombuffer(b, dtype=_np.uint8))[0]
        return [i for i in range(self.n) if b[i]]

    def _paeth(self, line):
        """Paeth = Sub (a running sum of the row) plus, at each byte where the
        row above changes, a correction that makes that byte come out right.
        The running sum of raw + corrections is then the whole row. Sub's
        sums are needed only at those bytes, so they're kept per channel
        from the bytes in between (summed in C) rather than for the row."""
        bpp, prev = self.bpp, self.prev
        changes = self._changes()
        if len(changes) * 3 > self.n:  # a busy row (photos): byte by byte is quicker
            return self._paeth_bytes(line)
        # CircuitPython's bytes can't slice with a step; ulab arrays can
        src = _np.frombuffer(line, dtype=_np.uint8) if _np is not None else line
        fix = bytearray(self.n)
        left = [0] * bpp  # per channel: the row's value so far (byte i - bpp)
        upto = list(range(bpp))  # per channel: the next byte not yet in left
        for i in changes:
            i = int(i)
            ch = i % bpp
            if i >= bpp:
                # Sub over the bytes since this channel's last change
                a = (left[ch] + int(_sum(src[upto[ch]:i:bpp]))) & 0xFF
                c = prev[i - bpp]
            else:
                a = c = 0
            b = prev[i]
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
            fix[i] = (pred - a) & 0xFF  # what Sub would add here is a
            left[ch] = (line[i] + pred) & 0xFF
            upto[ch] = i + bpp
        return self._scan(self._add(int.from_bytes(line, "little"), int.from_bytes(fix, "little")))

    def _paeth_bytes(self, line):
        row = bytearray(line)
        prev, bpp = self.prev, self.bpp
        for i in range(bpp):
            row[i] = (row[i] + prev[i]) & 0xFF
        for i in range(bpp, self.n):
            a = row[i - bpp]
            b = prev[i]
            c = prev[i - bpp]
            pa = b - c
            pb = a - c
            pc = pa + pb
            if pa < 0:
                pa = -pa
            if pb < 0:
                pb = -pb
            if pc < 0:
                pc = -pc
            if pa <= pb and pa <= pc:
                row[i] = (row[i] + a) & 0xFF
            elif pb <= pc:
                row[i] = (row[i] + b) & 0xFF
            else:
                row[i] = (row[i] + c) & 0xFF
        return int.from_bytes(row, "little")

    def next(self):
        """The next row's bytes, unfiltered."""
        n, bpp = self.n, self.bpp
        ftype = self.raw[self.pos]
        line = self.raw[self.pos + 1:self.pos + 1 + n]
        self.pos += n + 1
        if ftype == 0:
            x = int.from_bytes(line, "little")
        elif ftype == 1:  # Sub
            x = self._scan(int.from_bytes(line, "little"))
        elif ftype == 2:  # Up
            x = self._add(int.from_bytes(line, "little"), self.prev_int)
        elif ftype == 4:
            x = self._paeth(line)
        elif ftype == 3:  # Average
            row = bytearray(line)
            prev = self.prev
            for i in range(n):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((left + prev[i]) >> 1)) & 0xFF
            x = int.from_bytes(row, "little")
        else:
            raise ValueError("bad PNG filter %d" % ftype)
        row = x.to_bytes(n, "little")
        self.prev_int = x
        self.prev = row
        return row


def sample(data, side=SIDE, step=None):
    """A generator: the PNG `data` centred on a square and sampled to
    side x side. Yields None now and then while it works; the last thing it
    yields is the list of side*side 0xRRGGBB pixels, row by row (ints:
    CircuitPython hashes tuples slowly, and quantize() counts colours)."""
    w, h, ct, palette, z = read_png(data)
    raw = zlib.decompress(z)
    del z
    ch = _CHANNELS[ct]
    big = max(w, h)
    ox, oy = (big - w) // 2, (big - h) // 2
    # source column/row for each output pixel, or -1 outside the picture
    pick = lambda i, off, lim: ((2 * i + 1) * big // (2 * side)) - off  # noqa: E731
    cols = [pick(i, ox, w) for i in range(side)]
    want = {}
    for j in range(side):
        y = pick(j, oy, h)
        if 0 <= y < h:
            want.setdefault(y, []).append(j)
    pixels = [BG] * (side * side)
    rows = _Rows(raw, w, ch)
    last = max(want) if want else -1
    for y in range(last + 1):
        row = rows.next()
        outs = want.get(y)
        if outs:
            line = []
            for x in cols:
                if 0 <= x < w:
                    o = x * ch
                    if ct == 3:
                        px = palette[row[o]] if palette and row[o] < len(palette) else BG
                    elif ch >= 3:
                        px = (row[o] << 16) | (row[o + 1] << 8) | row[o + 2]
                    else:
                        px = row[o] * 0x010101
                    line.append(px)
                else:
                    line.append(BG)
            for j in outs:
                pixels[j * side:(j + 1) * side] = line
        if y % (step or 8) == 0:
            yield None
    yield pixels


def _box(items):
    """(score, shift) to split a box of (0xRRGGBB, count) on: its widest
    channel (as a shift), weighted by its pixel count."""
    total = sum(v for _, v in items)
    best, at = -1, 0
    for shift in (16, 8, 0):
        vals = [(k >> shift) & 0xFF for k, _ in items]
        score = (max(vals) - min(vals)) * total
        if score > best:
            best, at = score, shift
    return (best if len(items) > 1 else -1), at


def median_cut(counts, n=COLOURS):
    """[(0xRRGGBB, [colours it stands for])]: up to n palette colours for
    {colour: count}, by median cut."""
    items = list(counts.items())
    boxes = [(_box(items), items)]
    while len(boxes) < n:
        bi = max(range(len(boxes)), key=lambda i: boxes[i][0][0])
        (score, shift), box = boxes[bi]
        if score <= 0:
            break
        boxes.pop(bi)
        box.sort(key=lambda kv: (kv[0] >> shift) & 0xFF)
        total = sum(v for _, v in box)
        acc, cut = 0, len(box) - 1
        for i, (_, v) in enumerate(box):
            acc += v
            if acc * 2 >= total:
                cut = min(i + 1, len(box) - 1)
                break
        for part in (box[:cut], box[cut:]):
            boxes.append((_box(part), part))
    out = []
    for _, box in boxes:
        t = sum(v for _, v in box)
        colour = 0
        for shift in (16, 8, 0):
            colour |= ((sum(((k >> shift) & 0xFF) * v for k, v in box) + t // 2) // t) << shift
        out.append((colour, [k for k, _ in box]))
    return out


def quantize(pixels, n=COLOURS):
    """(palette, indices): 0xRRGGBB pixels reduced to at most n colours, each
    colour standing in for the ones in its median-cut box."""
    counts = {}
    for p in pixels:
        counts[p] = counts.get(p, 0) + 1
    if len(counts) <= n:
        palette = sorted(counts)
        index = dict((c, i) for i, c in enumerate(palette))
    else:
        palette, index = [], {}
        for i, (colour, members) in enumerate(median_cut(counts, n)):
            palette.append(colour)
            for k in members:
                index[k] = i
    return palette, bytes(index[p] for p in pixels)


def bmp(palette, indices, side=SIDE):
    """An 8-bit indexed BMP, bottom-up, as fm1ui.ui.load_tiles reads it."""
    def le(v, k):
        return bytes((v >> (8 * i)) & 0xFF for i in range(k))
    pal = b"".join(bytes((c & 0xFF, (c >> 8) & 0xFF, c >> 16, 0)) for c in palette)
    offset = 14 + 40 + len(pal)
    size = offset + side * side
    head = (
        b"BM"
        + le(size, 4)
        + le(0, 4)
        + le(offset, 4)
        + le(40, 4)
        + le(side, 4)
        + le(side, 4)
        + le(1, 2)
        + le(8, 2)
        + le(0, 4)
        + le(side * side, 4)
        + le(2835, 4)
        + le(2835, 4)
        + le(len(palette), 4)
        + le(len(palette), 4)
    )
    rows = [indices[y * side:(y + 1) * side] for y in range(side - 1, -1, -1)]
    return head + pal + b"".join(rows)


def convert(data, out_path):
    """A generator: write PNG `data` as thumb.bmp at out_path (via a .part
    file). Yields None while it works."""
    pixels = None
    for pixels in sample(data):
        if pixels is None:
            yield None
    palette, indices = quantize(pixels)
    del pixels
    yield None
    with open(out_path + ".part", "wb") as f:
        f.write(bmp(palette, indices))
    import os
    try:
        os.remove(out_path)
    except OSError:
        pass
    os.rename(out_path + ".part", out_path)
