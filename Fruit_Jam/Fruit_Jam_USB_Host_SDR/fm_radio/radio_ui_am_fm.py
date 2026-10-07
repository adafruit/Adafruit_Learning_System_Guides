# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""AM/FM/weather radio tuner UI."""

import board
import displayio
import framebufferio
import picodvi
import terminalio
import bitmaptools

# pylint: disable=too-many-arguments

HELP = (
    "B1 lower  B2 higher  hold B1: next band",
    "B3 mute / hold: next preset  hold B2: save/del",
    "keys: - + tune  b/a/n/w band  p m f<freq>  s x",
)


def format_frequency(hz):
    # 101100000 -> '101.1 MHz', 162550000 -> '162.550 MHz', 610000 ->
    # '610 kHz', from integers only. Above the FM band (weather) always show
    # kHz, so 162.400 lines up with the other channels.
    if not hz:
        return "RADIO LAB"
    if hz < 2000000:
        return "%d kHz" % (hz // 1000)
    if hz % 100000 or hz > 108000000:
        return "%d.%03d MHz" % (hz // 1000000, hz // 1000 % 1000)
    return "%d.%d MHz" % (hz // 1000000, hz // 100000 % 10)


class RadioUI:
    def __init__(self):
        displayio.release_displays()
        self.fb = picodvi.Framebuffer(
            320,
            240,
            clk_dp=board.CKP,
            clk_dn=board.CKN,
            red_dp=board.D0P,
            red_dn=board.D0N,
            green_dp=board.D1P,
            green_dn=board.D1N,
            blue_dp=board.D2P,
            blue_dn=board.D2N,
            color_depth=8,
        )
        self.display = framebufferio.FramebufferDisplay(self.fb, auto_refresh=False)
        self.group = displayio.Group()
        self.palette = displayio.Palette(5)
        for i, c in enumerate((0x07111D, 0xFFC44D, 0xEAF1FA, 0x41DBAC, 0x294257)):
            self.palette[i] = c
        self.bg = displayio.Bitmap(320, 240, 5)
        self.group.append(displayio.TileGrid(self.bg, pixel_shader=self.palette))
        self.term = []
        self._text(0, 8, 50, 2, 1)
        self._text(8, 44, 25, 2, 2)
        self._text(8, 114, 50, 8, 1)
        self.display.root_group = self.group
        self._shown = {}
        self._level = -1
        self.status = ""
        self.frequency = 0
        self.draw("STARTING", 0, "initializing receiver", "")

    def _text(self, x, y, columns, rows, scale):
        pal = displayio.Palette(2)
        pal[0] = 0x07111D
        pal[1] = 0xFFC44D if scale == 2 else 0xEAF1FA
        fw, fh = terminalio.FONT.get_bounding_box()[:2]
        grid = displayio.TileGrid(
            terminalio.FONT.bitmap,
            pixel_shader=pal,
            width=columns,
            height=rows,
            tile_width=fw,
            tile_height=fh,
        )
        g = displayio.Group(x=x, y=y, scale=scale)
        g.append(grid)
        self.group.append(g)
        self.term.append(terminalio.Terminal(grid, terminalio.FONT))

    def _line(self, term, row, text, width):
        # Rewrite one text row, only if it changed. A full redraw takes longer
        # than the USB ring lasts, so updates while the stream runs (mute,
        # typing, an AM step inside the tuning window) must touch few rows.
        text = ("%-*s" % (width, text))[:width]
        key = (term, row)
        if self._shown.get(key) == text:
            return False
        self._shown[key] = text
        self.term[term].write("\x1b[%d;1H%s" % (row + 1, text))
        return True

    def draw(self, status, frequency, line1, line2, footer="RTL-SDR RECEIVER"):
        # Only the rows that changed are rewritten, so this is cheap when, for
        # example, only the status row differs from the last call.
        self.status = status
        self.frequency = frequency
        changed = self._line(0, 0, "FRUIT JAM / DIRECT USB AM/FM/WEATHER", 49)
        changed |= self._line(0, 1, status, 49)
        changed |= self._line(1, 0, format_frequency(frequency), 24)
        lines = (line1, line2, "") + HELP + (footer, "MONO / 3.5MM HEADPHONE JACK")
        for row, text in enumerate(lines):
            changed |= self._line(2, row, text, 49)
        if changed:
            self.display.refresh(minimum_frames_per_second=0)
        return changed

    def level(self, fraction):
        # Signal bar, 0..1. Like entry() this runs while the stream is live, so
        # it only redraws the bar, and only when its length changes.
        n = min(304, max(0, int(fraction * 304))) & ~3
        if n == self._level:
            return
        self._level = n
        bitmaptools.fill_region(self.bg, 8, 98, 312, 105, 4)
        if n:
            bitmaptools.fill_region(self.bg, 8, 98, 8 + n, 105, 3)
        self.display.refresh(minimum_frames_per_second=0)

    def entry(self, text):
        # Show a frequency being typed in place of the dial (None puts the
        # dial and status back).
        if text is None:
            changed = self._line(0, 1, self.status, 49)
            changed |= self._line(1, 0, format_frequency(self.frequency), 24)
        else:
            changed = self._line(0, 1, "TYPE A FREQUENCY, ENTER TO TUNE", 49)
            changed |= self._line(1, 0, text[-23:] + "_", 24)
        if changed:
            self.display.refresh(minimum_frames_per_second=0)
