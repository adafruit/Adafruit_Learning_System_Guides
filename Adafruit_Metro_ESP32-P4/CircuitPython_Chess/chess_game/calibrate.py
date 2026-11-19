# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recalibrate the resistive 2.8" shield's touch screen from the REPL.

Stop the game with Ctrl-C, then:

    import calibrate          # calibrates once on import
    calibrate.run()           # calibrate again

Uses the same screens as the app (chess_calib.Screens.calibrate): tap three
crosshairs, tap a fourth to check, then draw to test. A failed check is not
saved and the crosshairs start over; Ctrl-C quits and keeps the old calibration.
The capacitive shield needs no calibration, so run() just reports that.
"""

import gc

import displayio

import chess_app
from chess_calib import Screens
from chess_view_s import ShieldView


def run(retry=True):
    """Runs the calibration and returns what was saved, or None."""
    display = chess_app.start_display_shield()
    view = ShieldView(chess_app.HARDWARE["shield"]["assets"])
    touch = chess_app.start_touch_shield(display)
    if not touch.needs_calibration:
        print("Capacitive touch (FT6206): no calibration needed")
        touch.i2c.deinit()
        display.root_group = displayio.CIRCUITPYTHON_TERMINAL
        display.auto_refresh = True
        return None
    print("Stored calibration:", touch.cal)
    print("Tap the crosshairs on the shield (Ctrl-C to give up)")
    saved = None
    try:
        screens = Screens(display, view, touch)
        while True:
            if screens.calibrate():
                saved = touch.cal
                print("Saved:", saved)
                break
            print("Check failed, not saved")
            if not retry:
                break
    finally:
        touch.i2c.deinit()  # free the I2C pins so the bus can be opened again
        display.root_group = displayio.CIRCUITPYTHON_TERMINAL
        display.auto_refresh = True
        gc.collect()
    return saved


run()
