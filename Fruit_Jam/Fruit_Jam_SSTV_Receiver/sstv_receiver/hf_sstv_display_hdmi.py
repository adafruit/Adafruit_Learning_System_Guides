# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""HDMI display for hf_sstv_iss.py: one fixed 320x240 screen.

hf_sstv_iss.py imports this module when no OLED answers on I2C;
hf_sstv_display_oled.py has the same methods for the OLED.

The picture (live, then decoded) fills the top IMAGE_H rows; two text rows
below show the frequency, signal and receiver state, then the last saved
file and the pictures saved since the start. Nothing ever redraws
the whole screen while the USB stream runs (a full redraw takes longer
than the USB ring holds): only changed text rows and the image rows just
drawn are refreshed. The refreshes are quick enough to send at once, so
the methods the OLED needs for queueing (set_live, service) do nothing.
"""
# pylint: disable=unused-argument, unnecessary-pass
import board
import displayio
import framebufferio
import picodvi
import terminalio

IMAGE_H = 212  # picture area height; the decoder fits each mode into 320 x IMAGE_H


def format_frequency(hz):
    """14230000 -> '14.230.00 MHz' (10 Hz resolution)."""
    hz = int(hz)
    return "%d.%03d.%02d MHz" % (hz // 1000000, hz // 1000 % 1000, hz // 10 % 100)


class HdmiDisplay:
    NAME = "hdmi"
    W, H = 320, IMAGE_H  # the live preview draws into W x H
    DECODE_SIZE = (320, IMAGE_H)  # and the decoder too (decode_image)
    VIEWS = 1
    view = 0

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
        # The decoder and the live preview write RGB565 pixels straight into
        # this bitmap's buffer; it is dithered to the 8-bit framebuffer.
        self.image = displayio.Bitmap(320, IMAGE_H, 65536)
        self.decode_image = self.image
        converter = displayio.ColorConverter(
            input_colorspace=displayio.Colorspace.RGB565, dither=True
        )
        self.group.append(displayio.TileGrid(self.image, pixel_shader=converter))
        pal = displayio.Palette(2)
        pal[0] = 0x07111D
        pal[1] = 0xEAF1FA
        fw, fh = terminalio.FONT.get_bounding_box()[:2]
        self.columns = 320 // fw
        rows = max(1, (240 - IMAGE_H) // fh)
        grid = displayio.TileGrid(
            terminalio.FONT.bitmap,
            pixel_shader=pal,
            width=self.columns,
            height=rows,
            tile_width=fw,
            tile_height=fh,
        )
        g = displayio.Group(x=0, y=IMAGE_H + (240 - IMAGE_H - rows * fh) // 2)
        g.append(grid)
        self.group.append(g)
        self.term = terminalio.Terminal(grid, terminalio.FONT)
        self.rows_shown = rows
        self._shown = {}
        self.display.root_group = self.group
        self.display.refresh(minimum_frames_per_second=0)

    def text(self, row, text):
        """Rewrite one text row if it changed (about 7 ms); returns whether
        it did."""
        if row >= self.rows_shown:
            return False
        # One column short of the width: filling the last row wraps the
        # cursor, which scrolls the terminal and blanks that row.
        text = ("%-*s" % (self.columns - 1, text))[: self.columns - 1]
        if self._shown.get(row) == text:
            return False
        self._shown[row] = text
        self.term.write("\x1b[%d;1H%s" % (row + 1, text))
        self.display.refresh(minimum_frames_per_second=0)
        return True

    def set_live(self, live):
        pass

    def service(self):
        return False

    def set_view(self, view):
        return 0

    def show(self, st):
        """The receiver's status (a hf_sstv_iss.Status)."""
        mode = st.mode
        if st.state == "rx":
            state = "RX %s line %d/%d%s" % (
                mode[0],
                st.line,
                mode[4],
                "" if st.offset is None else " %+d Hz" % st.offset,
            )
        elif st.state == "decode":
            state = "DECODING %s %d%%" % (mode[0], st.progress)
        elif st.state == "save":
            state = "SAVING %s" % mode[0]
        else:
            state = "listening"
        self.text(
            0,
            "%s %s %4d dB %s%s"
            % (
                format_frequency(st.dial),
                st.demod,
                st.level,
                state,
                " MUTED" if st.muted else "",
            ),
        )
        # Pictures saved since this run started, at the right end of row 1.
        pics = "%d pic%s" % (st.pictures, "" if st.pictures == 1 else "s")
        if st.last:
            name, mode_name, lines = st.last
            last = (
                "%s %s %d lines" % (name, mode_name, lines)
                if mode_name
                else "%s.wav (no picture)" % name
            )
        elif st.sd:
            last = st.label
        else:
            last, pics = "NO SD CARD", ""
        last += ("  " + st.note[0] if st.note else "") + (
            "  [d: keep all]" if st.record_all else ""
        )
        width = self.columns - 2 - len(pics)
        self.text(1, "%-*s %s" % (width, last[:width], pics))

    def connecting(self):
        self.text(0, "CONNECTING: looking for the USB receiver")

    def file_begin(self, path):
        """decode_wav() is decoding the file at path."""
        self.text(0, "DECODING %s" % path)

    def file_done(self, info):
        """decode_wav() is done: info is the decoder's result, or None if
        there was no picture."""
        if info:
            self.text(
                0,
                "%s  %d lines%s"
                % (info["mode"], info["lines"], ", VIS" if info["vis"] else ""),
            )
        else:
            self.text(0, "NO IMAGE: no SSTV header or line syncs found")

    def rows(self, width, height, row0, row1):
        """Display rows (y0, y1) where rows row0..row1-1 of a width x height
        picture land (the preview fits it into W x H, centred)."""
        if 320 * height <= IMAGE_H * width:
            oh = 320 * height // width
        else:
            oh = IMAGE_H
        oy = (IMAGE_H - oh) // 2
        return oy + row0 * oh // height - 1, oy + (row1 * oh + height - 1) // height + 1

    def new_picture(self):
        """A new live picture: drawn over the last one, line by line."""
        pass

    def image_rows(self, y0, y1):
        """Show image rows y0..y1-1 after the decoder or preview wrote them."""
        y0 = max(0, y0)
        y1 = min(IMAGE_H, y1)
        if y1 > y0:
            self.image.dirty(0, y0, 320, y1)
            self.display.refresh(minimum_frames_per_second=0)

    # The decoder draws the picture into decode_image itself: showing it
    # is one refresh.
    def picture_begin(self, width, height):
        pass

    def picture_row(self, bgr):
        return True

    def picture_show(self):
        self.image_rows(0, IMAGE_H)

    def clear_image(self):
        """Black picture area. A full refresh: call with the stream paused."""
        self.image.fill(0)
        self.display.refresh(minimum_frames_per_second=0)

    # The picture viewer (the stream is paused).

    def viewer_begin(self):
        self.clear_image()

    def viewer_text(self, index, count, name, mode, lines, sd):
        """Picture index (from 0) of count, its file name (no extension),
        mode and lines (0 if not known); mode 'loading' while it loads."""
        if count:
            what = (
                "loading..."
                if mode == "loading"
                else ("%s %d lines" % (mode, lines) if lines else (mode or ""))
            )
            self.text(0, "PICTURE %d/%d  %s  %s" % (index + 1, count, name, what))
        else:
            self.text(0, "PICTURES: none saved" if sd else "PICTURES: no SD card")
        self.text(1, "B1 previous  B2 next  hold B3: back to receiving")

    def viewer_picture(self, bgr, width, height):
        """Show a saved picture (bgr as the decoder leaves it: BGR, rows
        bottom-up), fitted into the picture area, or none. About 1-2 s:
        one sample per screen pixel, converted to RGB565 here."""
        self.image.fill(0)
        if bgr is not None:
            if 320 * height <= IMAGE_H * width:
                ow, oh = 320, 320 * height // width
            else:
                ow, oh = IMAGE_H * width // height, IMAGE_H
            ox, oy = (320 - ow) // 2, (IMAGE_H - oh) // 2
            cols = [(2 * x + 1) * width // (2 * ow) * 3 for x in range(ow)]
            out = memoryview(self.image)  # 16-bit pixels, rows unpadded at this width
            for y in range(oh):
                r = (height - 1 - (2 * y + 1) * height // (2 * oh)) * width * 3
                i = (oy + y) * 320 + ox
                for c in cols:
                    a = r + c
                    out[i] = (
                        (bgr[a + 2] & 0xF8) << 8
                        | (bgr[a + 1] & 0xFC) << 3
                        | bgr[a] >> 3
                    )
                    i += 1
            self.image.dirty()
        self.display.refresh(minimum_frames_per_second=0)

    def viewer_end(self):
        self.clear_image()
