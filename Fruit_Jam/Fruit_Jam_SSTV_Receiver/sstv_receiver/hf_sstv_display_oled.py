# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""SH1107 128x64 OLED (I2C) display for hf_sstv_iss.py.

hf_sstv_iss.py imports this module only when the OLED answers at its
I2C address; hf_sstv_display_hdmi.py has the same methods for HDMI. Text
is in the built-in 6x12 font.
Two views:

    picture (the default)                  details
    +--------------+-------+               +---------------------+
    |              |RX 123 |  inverse      |RX Martin 1 123/256  |  inverse
    | 86 x 64      |14.2300|  dial         |14.230.00 USB -28dB  |
    | dithered     |-28dB  |  level        |Martin 1 VIS +57 Hz  |
    | picture      |Mart 1 |  mode / pics  |saved 3 pics 3 29G   |
    |              |#0003  |  last saved   |#0003 Martin 1 256 ln|
    |              |=====  |  signal bar   +---------------------+
    +--------------+-------+

The signal bar is thick while a picture is coming in and thin otherwise.

The picture: the live preview draws RGB565 pixels into `image`, which is
not shown; image_rows() dithers it (bitmaptools.dither, native code) and
copies only the rows just drawn to the shown 1-bit `thumb`, so a new
picture wipes down over the last one, as on a real SSTV screen. The
decoded picture replaces it: picture_begin() and picture_row() average its
luma from the decoder's BMP buffer one row per call (in the receive loop's
idle time), and picture_show() stretches the contrast (weak pictures come
out grey), dithers it and sends the whole picture.

Sending to the display is the expensive part: an I2C refresh busy-waits,
about 10 ms per whole text row at 400 kHz, two to three times that while
USB streams, and a whole screen 50 ms or more. The demodulator and the
detector leave the receive loop only 2-3 ms of every 16, so only the
characters (and the part of the bar, and the picture rows) that changed
are sent, and with the stream running (live) the methods only note what
changed: service(), called by the receive loop when it has caught up,
sends one of them at a time. Otherwise (the stream paused: saving)
changes are shown at once. Switching views and picture_show() redraw the
whole screen, so the receiver does those with the stream paused.
"""
# pylint: disable=too-many-branches, too-many-locals, attribute-defined-outside-init
import displayio
import terminalio
import bitmaptools
from i2cdisplaybus import I2CDisplayBus
from adafruit_displayio_sh1107 import SH1107

ROTATION = 90  # 270 turns the picture upside down
THUMB_W, THUMB_H = 86, 64  # 86: a 16-bit Bitmap row of 86 pixels has no padding,
# as the decoder's RGB565 output needs
COLUMN = 7  # characters beside the picture (86 + 7 * 6 = 128)
COLUMNS = 21  # characters across the details view
BAR_W = 42
LEVEL_RANGE = (-70, -10)  # dB at the ends of the signal bar (-63 dB with no antenna)
# Text rows: 0-4 beside the picture, 5-9 the details view. Each is a
# one-row terminal: writing the last column of a multi-row terminal scrolls it.
DETAILS = 5
# Order in which service() sends queued changes: state, bar, picture first.
ORDER = (0, 5, "bar", "thumb", 1, 2, 3, 4, 6, 7, 8, 9)
# Mode names for the 7-character column beside the picture.
SHORT = {
    "Martin 1": "Mart 1",
    "Martin 2": "Mart 2",
    "Scottie 1": "Scot 1",
    "Scottie 2": "Scot 2",
    "Scottie DX": "ScotDX",
    "Robot 36": "Rob 36",
}


def format_frequency(hz):
    """14230000 -> '14.230.00' (MHz, 10 Hz resolution)."""
    hz = int(hz)
    return "%d.%03d.%02d" % (hz // 1000000, hz // 1000 % 1000, hz // 10 % 100)


def fit(width, height):
    """(ow, oh, ox, oy): a width x height picture fitted into the
    thumbnail, centred, as the decoder fits it."""
    if THUMB_W * height <= THUMB_H * width:
        ow, oh = THUMB_W, THUMB_W * height // width
    else:
        ow, oh = THUMB_H * width // height, THUMB_H
    return ow, oh, (THUMB_W - ow) // 2, (THUMB_H - oh) // 2


def _palette(inverse=False):
    pal = displayio.Palette(2)
    pal[0] = 0xFFFFFF if inverse else 0x000000
    pal[1] = 0x000000 if inverse else 0xFFFFFF
    return pal


class OledDisplay:
    NAME = "oled"
    W, H = THUMB_W, THUMB_H  # the live preview draws into W x H
    DECODE_SIZE = (320, 240)  # (the decoder draws nothing here: decode_image)
    VIEWS = 2

    def __init__(self, i2c, address):
        # Also frees the HDMI framebuffer the board starts with: its SRAM is
        # needed for the USB bulk ring and the audio DMA buffers.
        displayio.release_displays()
        bus = I2CDisplayBus(i2c, device_address=address)
        self.display = SH1107(
            bus, width=128, height=64, rotation=ROTATION, auto_refresh=False
        )
        self.term = []
        self.width = []
        self._shown = {}
        # The live preview writes RGB565 pixels straight into this bitmap's
        # buffer; it is dithered into _dith, and rows of that go to thumb.
        self.image = displayio.Bitmap(THUMB_W, THUMB_H, 65536)
        # The decoded picture is made from the BMP buffer instead.
        self.decode_image = None
        self._dith = displayio.Bitmap(THUMB_W, THUMB_H, 2)
        self.thumb = displayio.Bitmap(THUMB_W, THUMB_H, 2)
        self.group = displayio.Group()
        self.group.append(displayio.TileGrid(self.thumb, pixel_shader=_palette()))
        for k in range(5):
            self._text(self.group, THUMB_W, 12 * k, COLUMN, k == 0)
        self.signal_bar = displayio.Bitmap(BAR_W, 3, 2)
        self.group.append(
            displayio.TileGrid(self.signal_bar, pixel_shader=_palette(), x=THUMB_W, y=61)
        )
        self.details = displayio.Group()
        for k in range(5):
            self._text(self.details, 0, 2 + 12 * k, COLUMNS, k == 0)
        self.view = 0  # 0 picture, 1 details
        self.live = False  # see set_live()
        self._want = {}  # row, 'bar' or 'thumb' -> not yet shown
        self._level = -1
        self._top = 0  # thumb rows above this show the new picture
        self._key = None  # what show() last formatted
        self.luma = bytearray(THUMB_W * THUMB_H)
        self._hist = [0] * 64
        self._fit = None  # decoded picture's fit and size, for picture_row()
        self._ty = 0
        self.display.root_group = self.group
        self.display.refresh(minimum_frames_per_second=0)

    def _text(self, group, x, y, columns, inverse=False):
        fw, fh = terminalio.FONT.get_bounding_box()[:2]
        grid = displayio.TileGrid(
            terminalio.FONT.bitmap,
            pixel_shader=_palette(inverse),
            width=columns,
            height=1,
            tile_width=fw,
            tile_height=fh,
        )
        g = displayio.Group(x=x, y=y)
        g.append(grid)
        group.append(g)
        self.term.append(terminalio.Terminal(grid, terminalio.FONT))
        self.width.append(columns)
        self.term[-1].write(" " * columns)

    def _visible(self, key):
        if key in ("bar", "thumb"):
            return self.view == 0
        return (key >= DETAILS) == (self.view == 1)

    def _write(self, row, text):
        """Write only the characters that differ: every tile written is sent
        to the display, changed or not."""
        old = self._shown.get(row, " " * len(text))
        self._shown[row] = text
        a, b = 0, len(text)
        while a < b and old[a] == text[a]:
            a += 1
        while b > a and old[b - 1] == text[b - 1]:
            b -= 1
        if a < b:
            self.term[row].write("\x1b[1;%dH%s" % (a + 1, text[a:b]))

    def _draw_bar(self, level):
        """level = length * 2 + thick. Only the part that changed is drawn."""
        old, self._level = self._level, level
        n, thick = level >> 1, level & 1
        y0, y1 = (0, 3) if thick else (1, 2)
        if old >= 0 and old & 1 == thick:
            m = old >> 1
            if n > m:
                bitmaptools.fill_region(self.signal_bar, m, y0, n, y1, 1)
            elif n < m:
                bitmaptools.fill_region(self.signal_bar, n, y0, m, y1, 0)
            return
        self.signal_bar.fill(0)
        if n:
            bitmaptools.fill_region(self.signal_bar, 0, y0, n, y1, 1)

    def _draw_rows(self, band):
        """Dither the whole image (rows above a band do not depend on rows
        below it) and copy the band's rows to the shown thumbnail."""
        y0, y1 = band
        bitmaptools.dither(
            self._dith,
            self.image,
            displayio.Colorspace.RGB565,
            bitmaptools.DitherAlgorithm.Atkinson,
        )
        bitmaptools.blit(self.thumb, self._dith, 0, y0, x1=0, y1=y0, x2=THUMB_W, y2=y1)

    def _apply(self, key, value):
        if key == "bar":
            self._draw_bar(value)
        elif key == "thumb":
            self._draw_rows(value)
        else:
            self._write(key, value)

    def _queue(self, key, value):
        """Show a change now, or (live) note it for service()."""
        if self.live:
            self._want[key] = value
            return
        self._apply(key, value)
        if self._visible(key):
            self.display.refresh(minimum_frames_per_second=0)

    def set_live(self, live):
        """True while the USB stream runs; False shows what is queued."""
        self.live = live
        if not live and self._want:
            for key in ORDER:
                if key in self._want:
                    self._apply(key, self._want.pop(key))
            self.display.refresh(minimum_frames_per_second=0)

    def service(self):
        """Live: send the first queued change; changes to the view not shown
        are only written. Call when the receive loop has caught up. Returns
        True if it refreshed the display."""
        if not self._want:
            return False
        for key in ORDER:
            if key in self._want:
                self._apply(key, self._want.pop(key))
                if self._visible(key):
                    self.display.refresh(minimum_frames_per_second=0)
                    return True
        return False

    def text(self, row, text):
        """Rows 0-4: the column beside the picture (7 characters); 5-9: the
        details view (21). Only a changed row is queued or shown."""
        width = self.width[row]
        text = ("%-*s" % (width, text))[:width]
        if self._shown.get(row) == text:
            self._want.pop(row, None)
        elif self._want.get(row) != text:
            self._queue(row, text)

    def meter(self, fraction, thick):
        """Signal bar (0..1), thick while a picture is coming in."""
        n = min(BAR_W, max(0, int(fraction * BAR_W))) & ~1
        level = n * 2 + (1 if thick else 0)
        if level == self._level:
            self._want.pop("bar", None)
        else:
            self._queue("bar", level)

    def set_view(self, view):
        """0: picture, 1: details. Redraws everything: call with the stream
        paused."""
        if view != self.view:
            self.view = view
            self.set_live(False)
            self.display.root_group = self.details if view else self.group
            self.display.refresh(minimum_frames_per_second=0)
        return self.view

    def show(self, st):
        """The receiver's status (a hf_sstv_iss.Status)."""
        mute = " M" if st.muted else ""
        self.text(2, "%ddB%s" % (st.level, mute))
        self.text(
            6, "%s %s %ddB%s" % (format_frequency(st.dial), st.demod, st.level, mute)
        )
        self.meter(
            (st.level - LEVEL_RANGE[0]) / (LEVEL_RANGE[1] - LEVEL_RANGE[0]),
            st.state == "rx",
        )
        # The other rows only when what they show changed (formatting them
        # allocates, and this runs every 0.5 s).
        key = (
            st.state,
            st.mode,
            st.line,
            st.progress,
            st.trigger,
            st.offset,
            st.dial,
            st.label,
            st.note,
            st.last,
            st.sd,
            st.saved,
            st.pictures,
            st.free_mb,
            st.record_all,
        )
        if key == self._key:
            return
        self._key = key
        mode = st.mode
        if st.state == "rx":
            state, state_long = "RX %d" % st.line, "RX %s %d/%d" % (
                mode[0],
                st.line,
                mode[4],
            )
        elif st.state == "decode":
            state, state_long = "DEC %d%%" % st.progress, "DECODING %s %d%%" % (
                mode[0],
                st.progress,
            )
        elif st.state == "save":
            state, state_long = "SAVING", "SAVING %s" % mode[0]
        else:
            state, state_long = "LISTEN", "LISTENING" + (
                "  keep all" if st.record_all else ""
            )
        last_short = last_long = ""
        if st.last:
            name, mode_name, lines = st.last
            last_short = "#" + name[-4:]
            if mode_name:
                last_long = "%s %s %d ln" % (last_short, mode_name, lines)
            else:
                last_long = "%s no picture" % last_short
        if not st.sd:
            sd_text = "NO SD CARD: no saving"
        else:
            free = st.free_mb
            sd_text = "saved %d pics %d %s" % (
                st.saved,
                st.pictures,
                "%dG" % (free // 1024) if free >= 10000 else "%dM" % free,
            )
        self.text(0, state)
        # (7 characters: 1 kHz resolution from 100 MHz up)
        if st.dial >= 100000000:
            self.text(1, "%d.%03d" % (st.dial // 1000000, st.dial // 1000 % 1000))
        else:
            self.text(1, "%d.%04d" % (st.dial // 1000000, st.dial // 100 % 10000))
        # Listening: pictures saved since this run started, in place of the
        # band (the dial shows it).
        pics = st.pictures
        self.text(
            3,
            (
                SHORT.get(mode[0], mode[0])
                if mode
                else (
                    ("%d pic%s" % (pics, "" if pics == 1 else "s"))
                    if pics < 100
                    else "%dpic" % pics
                )
            ),
        )
        self.text(4, st.note[1] if st.note else last_short)
        self.text(5, state_long)
        if mode:
            self.text(
                7,
                "%s %s%s"
                % (
                    mode[0],
                    "VIS" if st.trigger == "vis" else st.trigger,
                    "" if st.offset is None else " %+d Hz" % st.offset,
                ),
            )
        else:
            self.text(7, st.label)
        self.text(8, sd_text)
        self.text(9, st.note[0] if st.note else last_long)

    def connecting(self):
        self.text(0, "USB")
        self.text(5, "CONNECTING")
        self.text(6, "looking for RTL-SDR")

    def file_begin(self, path):
        """decode_wav() is decoding the file at path."""
        name = path.split("/")[-1]
        self.text(0, "DECODE")
        self.text(1, name[-11:-4] if name.lower().endswith(".wav") else name[-7:])
        self.text(5, "DECODING")
        self.text(6, name)

    def file_done(self, info):
        """decode_wav() is done: info is the decoder's result, or None if
        there was no picture."""
        if info:
            self.text(0, "DONE")
            self.text(2, SHORT.get(info["mode"], info["mode"]))
            self.text(3, "%d ln" % info["lines"])
            self.text(4, "VIS" if info["vis"] else "sync")
            self.text(5, "DECODED")
            self.text(
                7,
                "%s %d lines%s"
                % (info["mode"], info["lines"], ", VIS" if info["vis"] else ""),
            )
            self.text(8, "offset %+d Hz" % info["offset_hz"])
        else:
            self.text(0, "NO IMG")
            self.text(5, "NO IMAGE")
            self.text(7, "no SSTV header or")
            self.text(8, "line syncs found")

    def rows(self, width, height, row0, row1):
        """Thumbnail rows (y0, y1) that show rows row0..row1-1 of a width x
        height picture, or None if none does (the preview fits the picture
        into W x H, centred, and gives each thumbnail row the picture row
        nearest its centre)."""
        f = fit(width, height)
        oh, oy = f[1], f[3]
        rows = [
            d
            for d in range(
                max(0, row0 * oh // height - 1), min(oh, row1 * oh // height + 2)
            )
            if row0 <= (2 * d + 1) * height // (2 * oh) < row1
        ]
        return (oy + rows[0], oy + rows[-1] + 1) if rows else None

    def new_picture(self):
        """A new live picture: its rows will wipe down over the last one."""
        self.image.fill(0)
        self._top = 0
        self._want.pop("thumb", None)

    def image_rows(self, y0, y1):
        """Show thumbnail rows y0..y1-1 after the preview wrote them, and the
        rows above them not shown yet for this picture (lines skipped)."""
        y0 = max(0, min(y0, self._top))
        y1 = min(THUMB_H, y1)
        if y1 <= y0:
            return
        self._top = max(self._top, y1)
        band = self._want.get("thumb")
        self._queue("thumb", (min(y0, band[0]), max(y1, band[1])) if band else (y0, y1))

    def picture_begin(self, width, height):
        """Start a thumbnail of a decoded width x height picture."""
        self._fit = f = fit(width, height) + (width, height)
        self._ty = 0
        # Byte offsets in a BMP row of the three sample columns of each pixel.
        self._cols = [(2 * k + 1) * width // (6 * f[0]) * 3 for k in range(3 * f[0])]
        luma = self.luma
        for i in range(len(luma)):
            luma[i] = 0
        hist = self._hist
        for k in range(64):
            hist[k] = 0

    def picture_row(self, bgr):
        """One thumbnail row from the decoder's BMP buffer (BGR, rows
        bottom-up): luma averaged over 3 x 3 samples spread over each
        pixel's area (weak pictures are mostly noise; fewer samples leave
        too little of the picture at this size). Returns True when all rows
        are done."""
        ow, oh, ox, oy, w, h = self._fit
        y = self._ty
        if y < oh:
            r0 = (h - 1 - (6 * y + 1) * h // (6 * oh)) * w * 3
            r1 = (h - 1 - (6 * y + 3) * h // (6 * oh)) * w * 3
            r2 = (h - 1 - (6 * y + 5) * h // (6 * oh)) * w * 3
            luma, hist, cols = self.luma, self._hist, self._cols
            i = (oy + y) * THUMB_W + ox
            # (No tuple assignments or tuples: building one allocates, and
            # allocating here would bring on a garbage collection.)
            for x in range(ow):
                v = 0
                for k in range(3 * x, 3 * x + 3):
                    c = cols[k]
                    a = r0 + c
                    b = r1 + c
                    d = r2 + c
                    v += (
                        29 * (bgr[a] + bgr[b] + bgr[d])
                        + 150 * (bgr[a + 1] + bgr[b + 1] + bgr[d + 1])
                        + 77 * (bgr[a + 2] + bgr[b + 2] + bgr[d + 2])
                    )
                v //= 2304
                luma[i] = v
                if v:
                    # Lines never received are black: leave them out of
                    # the contrast stretch.
                    hist[v >> 2] += 1
                i += 1
            y += 1
            self._ty = y
        return y >= oh

    def picture_show(self):
        """Show the finished thumbnail: contrast stretched between the 2nd
        and 98th percentiles, dithered. Redraws the picture: call with the
        stream paused."""
        if self._fit is None:
            return
        hist = self._hist
        count = sum(hist)
        lo, hi, total = 0, 255, 0
        for k in range(64):
            total += hist[k]
            if total > count // 50:
                lo = k * 4
                break
        total = 0
        for k in range(63, -1, -1):
            total += hist[k]
            if total > count // 50:
                hi = k * 4 + 3
                break
        span = max(hi - lo, 16)
        # Grey RGB565 for each luma value (the letterbox, luma 0, stays black).
        lut = [0] * 256
        for v in range(1, 256):
            g = min(255, max(0, (v - lo) * 255 // span))
            lut[v] = (g & 0xF8) << 8 | (g & 0xFC) << 3 | g >> 3
        out = memoryview(self.image)  # 16-bit pixels, rows unpadded at this width
        luma = self.luma
        for i in range(len(luma)):
            out[i] = lut[luma[i]]
        self._fit = None
        self._top = THUMB_H
        self._want.pop("thumb", None)
        self._draw_rows((0, THUMB_H))
        if self.view == 0:
            self.display.refresh(minimum_frames_per_second=0)

    # The picture viewer (the stream is paused: changes are shown at once).

    def viewer_begin(self):
        self.image.fill(0)
        self.thumb.fill(0)
        self._fit = None
        self._top = THUMB_H
        self._want.pop("thumb", None)
        self.meter(0, False)
        if self.view == 0:
            self.display.refresh(minimum_frames_per_second=0)

    def viewer_text(self, index, count, name, mode, lines, sd):
        """Picture index (from 0) of count, its file name (no extension),
        mode and lines (0 if not known); mode 'loading' while it loads."""
        if count:
            pos = "%d/%d" % (index + 1, count)
            if mode == "loading":
                short, long = "load..", "loading..."
            else:
                short = SHORT.get(mode, mode) if mode else ""
                long = "%s %d lines" % (mode, lines) if lines else (mode or "")
            rows = (
                "VIEW",
                pos,
                "#" + name[-4:],
                short,
                "%d ln" % lines if lines else "",
                "VIEWING %s" % pos,
                name + ".bmp",
                long,
                "B1 prev  B2 next",
            )
        else:
            rows = (
                "VIEW",
                "none" if sd else "NO SD",
                "",
                "",
                "",
                "VIEWER: no pictures" if sd else "VIEWER: no SD card",
                "",
                "",
                "",
            )
        for k in range(9):
            self.text(k, rows[k])
        self.text(9, "hold B3: receive")

    def viewer_picture(self, bgr, width, height):
        """Show a saved picture (bgr as the decoder leaves it), or none."""
        if bgr is None:
            self.thumb.fill(0)
            if self.view == 0:
                self.display.refresh(minimum_frames_per_second=0)
            return
        self.picture_begin(width, height)
        while not self.picture_row(bgr):
            pass
        self.picture_show()

    def viewer_end(self):
        """Back to receiving: a blank picture; show() rewrites the text."""
        self.viewer_begin()
        self._top = 0
        self._key = None
