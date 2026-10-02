# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Radio tuner UI."""

import board
import displayio
import framebufferio
import picodvi
import terminalio
import bitmaptools


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
        self.draw("STARTING", 0, "initializing receiver", "")
        self.typing = None

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

    def _frequency(self):
        return (
            "%.1f MHz" % (self.frequency / 1000000) if self.frequency else "RADIO LAB"
        )

    def draw(self, status, frequency, line1, line2, level=0):
        self.status = status
        self.frequency = frequency
        self.typing = False
        self.term[0].write(
            "\x1b[HFRUIT JAM / DIRECT USB FM\r\n" + ("%-49s" % status)[:49]
        )
        self.term[1].write("\x1b[H" + ("%-24s" % self._frequency())[:24])
        bitmaptools.fill_region(self.bg, 8, 98, 312, 105, 4)
        n = min(304, max(0, int(level * 304)))
        if n:
            bitmaptools.fill_region(self.bg, 8, 98, 8 + n, 105, 3)
        lines = (
            line1,
            line2,
            "",
            "B1 lower     B2 higher",
            "B3 mute / hold: next preset",
            "RTL-SDR RECEIVER",
            "MONO / 3.5MM HEADPHONE JACK",
        )
        self.term[2].write("\x1b[H" + "\r\n".join(("%-49s" % s)[:49] for s in lines))
        self.display.refresh(minimum_frames_per_second=0)

    def entry(self, text):
        # Show a frequency being typed on serial in place of the dial (None puts
        # the dial back). The stream keeps running, so only rewrite the rows that
        # change: a full draw takes longer than the USB ring lasts.
        if text is None:
            if not self.typing:
                return
            self.typing = False
            self.term[0].write("\x1b[2;1H" + ("%-49s" % self.status)[:49])
            self.term[1].write("\x1b[H" + ("%-24s" % self._frequency())[:24])
        else:
            if not self.typing:
                self.typing = True
                self.term[0].write(
                    "\x1b[2;1H" + ("%-49s" % "TYPE A FREQUENCY, ENTER TO TUNE")[:49]
                )
            self.term[1].write("\x1b[H" + ("%-24s" % (text[-23:] + "_"))[:24])
        self.display.refresh(minimum_frames_per_second=0)
