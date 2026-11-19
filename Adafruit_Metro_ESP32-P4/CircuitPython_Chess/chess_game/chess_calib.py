# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=attribute-defined-outside-init
"""Splash screen and touch calibration for the 2.8" shield.

Screens.start() shows the splash. If a calibration is stored, tapping within
CAL_WINDOW_MS starts a new one; if not, calibration starts right away.
Calibration: tap three crosshairs to fit, a fourth to check, then draw to test.
It is saved only if the check tap is within CHECK_MAX_PX of its crosshair.
"""

import time

import bitmaptools
import displayio
import vectorio

from chess_gfx import CENTER, Text, rect
from chess_touch_tsc import fit
from chess_view import ACCENT, BAD, DARK, GOOD, LIGHT, LINE, MUTED, PANEL_BG, TEXT

W, H = 320, 240
CAL_WINDOW_MS = 3000
TEST_MS = 6000
# crosshairs used for the fit, and the one used to check it
TARGETS = ((32, 24), (288, 120), (160, 216))
CHECK = (40, 200)
CHECK_MAX_PX = 14


def _ms():
    return time.monotonic_ns() // 1000000


def _palette(colour):
    p = displayio.Palette(1)
    p[0] = colour
    return p


class Screens:
    def __init__(self, display, view, touch):
        self.display = display
        self.view = view
        self.touch = touch

    def refresh(self):
        self.display.refresh(target_frames_per_second=None)

    def _bar(self, g, y):
        """Adds a countdown bar at y. Returns (fill shape, full width)."""
        bw = W - 120
        g.append(rect(LINE, 60, y, bw, 4)[0])
        fill, _ = rect(ACCENT, 60, y, bw, 4)
        g.append(fill)
        return fill, bw

    # ------------------------------------------------------------ splash

    def splash(self, message):
        """Shows the splash screen and returns its group. self.message is the
        status line below the title."""
        v = self.view
        g = displayio.Group()
        g.append(rect(PANEL_BG, 0, 0, W, H)[0])
        b = v.board
        for i, (white, kind) in enumerate(
            ((True, 4), (True, 2), (True, 3), (False, 5), (False, 6), (False, 1))
        ):
            x = 70 + i * 30
            g.append(rect(DARK if i & 1 else LIGHT, x, 40, 30, 30)[0])
            tg = displayio.TileGrid(
                b.piece_sheet,
                pixel_shader=b.piece_palette,
                tile_width=30,
                tile_height=30,
                x=x,
                y=40,
            )
            tg[0] = kind if white else kind + 6
            g.append(tg)
        g.append(
            Text(
                v.font_big,
                W,
                0,
                84,
                TEXT,
                PANEL_BG,
                "CircuitPython Chess",
                align=CENTER,
            ).tile
        )
        g.append(
            Text(
                v.font_small,
                W,
                0,
                122,
                MUTED,
                PANEL_BG,
                "Chess engine based on Stockfish",
                align=CENTER,
            ).tile
        )
        self.message = Text(
            v.font_small, W, 0, 172, ACCENT, PANEL_BG, message, align=CENTER
        )
        g.append(self.message.tile)
        self.display.root_group = g
        self.refresh()
        return g

    def start(self):
        """Offers calibration on the splash (or forces it if none is stored).
        Returns True if a new calibration was made."""
        t = self.touch
        if t.cal is None:
            self.message.set("Touch needs calibrating", BAD)
            self.refresh()
            time.sleep(1.0)
            while not self.calibrate():
                pass
            return True
        self.message.set("Tap the screen to calibrate touch")
        g = self.display.root_group
        fill, bw = self._bar(g, 194)
        self.refresh()
        t0 = _ms()
        while _ms() - t0 < CAL_WINDOW_MS:
            if t.pressed():
                time.sleep(0.02)
                if t.pressed():
                    t.wait_release()
                    while not self.calibrate():
                        pass
                    return True
            left = bw - bw * (_ms() - t0) // CAL_WINDOW_MS
            if left != fill.width:
                fill.width = max(1, left)
                self.refresh()
            time.sleep(0.02)
        return False

    # ------------------------------------------------------------ calibration

    def _text_screen(self, title, line, step):
        v = self.view
        g = displayio.Group()
        g.append(rect(PANEL_BG, 0, 0, W, H)[0])
        g.append(Text(v.font_med, W, 0, 76, ACCENT, PANEL_BG, title, align=CENTER).tile)
        g.append(rect(LINE, 70, 98, W - 140, 1)[0])
        g.append(Text(v.font_small, W, 0, 106, TEXT, PANEL_BG, line, align=CENTER).tile)
        if step:
            g.append(
                Text(v.font_small, W, 0, 126, MUTED, PANEL_BG, step, align=CENTER).tile
            )
        self.display.root_group = g
        return g

    def _target(self, g, x, y):
        g.append(vectorio.Circle(pixel_shader=_palette(ACCENT), radius=10, x=x, y=y))
        g.append(vectorio.Circle(pixel_shader=_palette(PANEL_BG), radius=8, x=x, y=y))
        g.append(rect(TEXT, x - 16, y, 33, 1)[0])
        g.append(rect(TEXT, x, y - 16, 1, 33)[0])
        g.append(vectorio.Circle(pixel_shader=_palette(BAD), radius=2, x=x, y=y))
        done = vectorio.Circle(pixel_shader=_palette(GOOD), radius=10, x=x, y=y)
        done.hidden = True
        g.append(done)
        return done

    def _tap_target(self, x, y, step):
        t = self.touch
        g = self._text_screen("Touch calibration", "Tap the crosshair", step)
        done = self._target(g, x, y)
        self.refresh()
        t.wait_release()
        time.sleep(0.2)
        p = None
        while p is None:
            p = t.average_press()
        done.hidden = False
        self.refresh()
        t.wait_release()
        time.sleep(0.2)
        return p

    def calibrate(self):
        """Runs the calibration. Returns True if it passed and was saved."""
        t = self.touch
        raw = []
        n = len(TARGETS) + 1
        for i, (x, y) in enumerate(TARGETS):
            raw.append(self._tap_target(x, y, "Step %d of %d" % (i + 1, n)))
        check = self._tap_target(CHECK[0], CHECK[1], "Step %d of %d" % (n, n))
        cal = fit(raw, TARGETS)
        err = None
        if cal is not None:
            cx, cy = t.to_screen(check[0], check[1], cal)
            err = max(abs(cx - CHECK[0]), abs(cy - CHECK[1]))
        print(
            "Touch calibration: raw %r check %r -> %r, error %s px"
            % (raw, check, cal, err)
        )
        if err is None or err > CHECK_MAX_PX:
            self._text_screen("Calibration failed", "Not saved: try again", "")
            self.refresh()
            time.sleep(1.5)
            return False
        self._draw_test(cal)
        t.save_calibration(cal)
        self._text_screen("Calibration saved", "", "")
        self.refresh()
        time.sleep(1.0)
        return True

    def _draw_test(self, cal):
        """Draws dots under the finger for TEST_MS so the user can check the result."""
        t = self.touch
        g = self._text_screen("Draw to test", "Dots follow your finger", "")
        bmp = displayio.Bitmap(W, H, 2)
        p = displayio.Palette(2)
        p[1] = ACCENT
        p.make_transparent(0)
        g.append(displayio.TileGrid(bmp, pixel_shader=p))
        fill, bw = self._bar(g, 190)
        self.refresh()
        t0 = _ms()
        while _ms() - t0 < TEST_MS:
            r = t.raw()
            if r is not None:
                x, y = t.to_screen(r[0], r[1], cal)
                bitmaptools.draw_circle(bmp, x, y, 2, 1)
                bitmaptools.fill_region(
                    bmp, max(0, x - 1), max(0, y - 1), min(W, x + 2), min(H, y + 2), 1
                )
            fill.width = max(1, bw - bw * (_ms() - t0) // TEST_MS)
            self.refresh()
            time.sleep(0.01)
        t.wait_release()
