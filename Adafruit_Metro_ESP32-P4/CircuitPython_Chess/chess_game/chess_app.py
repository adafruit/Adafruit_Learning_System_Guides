# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=import-outside-toplevel, too-many-locals, too-many-return-statements
# pylint: disable=too-many-statements
"""CircuitPython Chess app: sets up the display, touch and engine, and runs the loop.

Supported displays:

  "dsi"     Raspberry Pi Touch Display 2 (5", 1280x720, GT911 touch)
  "shield"  Adafruit 2.8" TFT Touch Shield (ILI9341, 320x240) with either
            resistive (TSC2007) or capacitive (FT6206) touch

The display is chosen by detect(), or by App(hardware="dsi" / "shield").
The game modes are 1 player, 2 players and online (see chess_ctrl). The engine
searches in short slices so the main loop can poll touch and update the thinking
bar in between, which keeps MOVE NOW responsive.

    import chess_app; chess_app.App().run()

For tests: App.tap(x, y) simulates a tap, and App(start_screen=False) skips the
splash, calibration prompt and start-up menu (menu=True keeps the menu).
"""

import gc
import os
import time

import displayio
import microcontroller
import supervisor

import _chess_engine as tf
import chess_ctrl as cc
from chess_settings import Settings

# Folder holding assets/ and assets_s/ (this file's folder; "" is the CIRCUITPY root)
APP_DIR = __file__.rsplit("/", 1)[0] if "/" in __file__ else ""

TT_BYTES = 6144 * 32  # engine transposition table (192 KB)
STACK_BYTES = 256 * 1024  # search stack (peak use ~96 KB)
IDLE_POLL_S = 0.015  # touch poll period while waiting for the player
PROGRESS_EVERY_MS = 250  # thinking bar refresh period

# Per display: asset folder, and engine time between touch polls while thinking.
# The GT911 holds a touch until it is read, so longer slices are fine; the shield's
# controllers only report a finger while it is down, so they are polled more often.
HARDWARE = {
    "dsi": {"assets": APP_DIR + "/assets", "slice_ms": 100},
    "shield": {"assets": APP_DIR + "/assets_s", "slice_ms": 50},
}
SHIELD_ROTATION = 0  # 180 turns the screen upside down
SHIELD_SPI_HZ = 40_000_000
TSC2007_ADDRESS = 0x48  # resistive shield
FT6206_ADDRESS = 0x38  # capacitive shield
DSI_I2C_ADDRESSES = (0x45, 0x5D, 0x14)  # DSI panel's MCU, GT911 (either address)


def now_ms():
    return time.monotonic_ns() // 1000000


def detect():
    """Returns 'dsi' or 'shield'. Uses CPCHESS_DISPLAY from settings.toml if set,
    otherwise checks for an existing DSI display, then scans I2C for the DSI
    panel's chips. Anything else is assumed to be the shield."""
    choice = os.getenv("CPCHESS_DISPLAY")
    if choice in HARDWARE:
        return choice
    d = supervisor.runtime.display
    if d is not None and hasattr(d, "framebuffer"):
        return "dsi"
    try:
        import board

        i2c = board.I2C()
        while not i2c.try_lock():
            pass
        try:
            found = i2c.scan()
        finally:
            i2c.unlock()
    except (RuntimeError, ValueError, OSError):
        found = []  # no pull-ups, so nothing is on the bus
    if any(a in found for a in DSI_I2C_ADDRESSES):
        return "dsi"
    return "shield"


def start_display():
    """Sets up the DSI panel at 1280x720, RGB565, or reuses it if already set up."""
    d = supervisor.runtime.display
    if (
        d is not None
        and d.rotation == 90
        and getattr(d.framebuffer, "color_depth", 0) == 16
    ):
        d.auto_refresh = False
        return d
    import adafruit_ili9881
    import board
    import framebufferio
    import mipidsi

    displayio.release_displays()
    bus = mipidsi.Bus(
        minimum_frequency=adafruit_ili9881.RaspberryPiTouchDisplay2.MINIMUM_BUS_FREQUENCY,
        num_lanes=2,
    )
    panel = adafruit_ili9881.RaspberryPiTouchDisplay2(bus, board.I2C(), color_depth=16)
    d = framebufferio.FramebufferDisplay(panel, rotation=90, auto_refresh=False)
    supervisor.runtime.display = d
    return d


def start_display_shield():
    """Sets up the shield's ILI9341 at 320x240 (CS D10, DC D9, board SPI), or
    reuses it if already set up."""
    d = supervisor.runtime.display
    if (
        d is not None
        and not hasattr(d, "framebuffer")
        and d.width == 320
        and d.height == 240
        and d.rotation == SHIELD_ROTATION
    ):
        d.auto_refresh = False
        return d
    import adafruit_ili9341
    import board
    import fourwire

    displayio.release_displays()
    bus = fourwire.FourWire(
        board.SPI(), command=board.D9, chip_select=board.D10, baudrate=SHIELD_SPI_HZ
    )
    d = adafruit_ili9341.ILI9341(
        bus, width=320, height=240, rotation=SHIELD_ROTATION, auto_refresh=False
    )
    try:
        supervisor.runtime.display = d
    except TypeError:
        pass  # some CircuitPython versions reject the driver's display subclass
    return d


def start_touch_shield(display):
    """Returns the shield's touch driver on a 400 kHz I2C bus: FT6206 (capacitive)
    if found, else TSC2007 (resistive), which raises OSError if missing."""
    import board
    import busio

    try:
        board.I2C().deinit()
    except (RuntimeError, ValueError):
        pass
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    try:
        while not i2c.try_lock():
            pass
        try:
            found = i2c.scan()
        finally:
            i2c.unlock()
        if FT6206_ADDRESS in found:
            from chess_touch_ft import Touch

            return Touch(display.width, display.height, display.rotation, i2c=i2c)
        from chess_touch_tsc import Touch

        return Touch(display.width, display.height, i2c=i2c)
    except Exception:
        i2c.deinit()
        raise


class App:
    def __init__(self, log=True, hardware=None, start_screen=True, menu=None):
        t0 = now_ms()
        self.hardware = hardware or detect()
        hw = HARDWARE[self.hardware]
        self.slice_ms = hw["slice_ms"]
        shield = self.hardware == "shield"
        self.display = start_display_shield() if shield else start_display()
        if shield:
            from chess_view_s import ShieldView

            self.view = ShieldView(hw["assets"])
        else:
            from chess_view import View

            self.view = View(hw["assets"])
        screens = None
        if shield and start_screen:
            from chess_calib import Screens

            screens = Screens(self.display, self.view, None)
            screens.splash("Starting...")
        try:
            if shield:
                self.touch = start_touch_shield(self.display)
            else:
                from chess_touch import Touch

                self.touch = Touch(self.display.rotation)
        except (OSError, RuntimeError, ValueError) as e:
            print("No touch screen:", e)
            self.touch = None
        gc.collect()
        self.mem = bytearray(tf.tables_size() + TT_BYTES + 64)
        tf.init(self.mem, microcontroller.cpu.frequency, TT_BYTES)
        self.stack = bytearray(STACK_BYTES)
        self.settings = Settings(cc.DEFAULT_LEVEL)
        import chess_net

        online, net_cfg = chess_net.load_online()
        if menu is None:
            menu = start_screen
            if menu and self.settings.mode == cc.ONLINE and online.configured:
                menu = "online"
        self.ctrl = cc.Controller(
            tf, self.stack, self.settings, now_ms, menu=menu, online=online
        )
        self.net = None
        if online.configured:
            self.net = chess_net.Net(
                self.ctrl,
                net_cfg["key"],
                mqtt=net_cfg["mqtt"],
                poll_s=net_cfg["poll_s"],
                log=print if log else None,
            )
        self.net_active = False  # networking starts when online play is first chosen
        self.last_dialog = self.ctrl.dialog
        if log:
            self.ctrl.log = print
        print(
            "CircuitPython Chess (%s) ready in %d ms, %d KB free"
            % (self.hardware, now_ms() - t0, gc.mem_free() // 1024)
        )
        if (
            screens is not None
            and self.touch is not None
            and self.touch.needs_calibration
        ):
            screens.touch = self.touch
            screens.start()
            self.touch.wait_release()
        self.display.root_group = self.view.root
        self.view.render(self.ctrl)
        self.refresh()
        self.last_progress = 0
        self.slices = 0

    def refresh(self):
        self.display.refresh(target_frames_per_second=None)

    def tap(self, x, y):
        c, v = self.ctrl, self.view
        hit = v.hit(c, x, y)
        if hit is None:
            return None
        kind, what = hit
        if kind == "square":
            return c.tap_square(what)
        if kind == "promo":
            c.choose_promotion(what)
            return "ok"
        if kind == "button":
            ok = {
                "hint": c.can_hint,
                "undo": c.can_undo,
                "new": lambda: not c.searching(),
                "stop": lambda: c.searching() and not c.stop_requested,
            }[what]()
            if not ok:
                return "warn"
            v.flash(c, what)
            self.refresh()
            if what == "hint":
                c.hint()
            elif what == "undo":
                c.undo()
            elif what == "new":
                c.open_menu()
            else:
                c.stop()
            return "ok"
        if kind == "dialog":
            if (what == "o_resume" and not c.can_resume()) or (
                what == "o_start" and not c.can_start_online()
            ):
                return "warn"
            v.flash(c, what)
            self.refresh()
            c.dialog_action(what)
            return "ok"
        return None

    def poll(self):
        """One pass of the main loop: an engine slice (or idle wait), touch, network
        and screen update."""
        c = self.ctrl
        if c.searching():
            self.slices += 1
            if c.step(self.slice_ms):
                gc.collect()
        else:
            time.sleep(IDLE_POLL_S)
        if self.touch is not None and self.touch.tapped():
            self.tap(self.touch.x, self.touch.y)
        if self.net is not None:
            self.net_poll()
        changed = self.view.render(c)
        t = now_ms()
        if c.searching() and t - self.last_progress >= PROGRESS_EVERY_MS:
            self.last_progress = t
            changed = self.view.render_progress(c) or changed
        if changed:
            self.refresh()

    def net_poll(self):
        """Runs network work, but never during an engine search (requests block)."""
        c = self.ctrl
        if c.dialog != self.last_dialog:
            self.last_dialog = c.dialog
            if c.dialog == "online":
                self.net.poll_now()  # refresh the opponent's state for RESUME
        if not self.net_active:
            if c.dialog != "online" and c.players != cc.ONLINE:
                return
            self.net_active = True
        if c.searching():
            return
        if c.version != self.view.version:
            # draw pending changes (e.g. "Sending...") before the network blocks
            self.view.render(c)
            self.refresh()
        self.net.step(waiting=c.mode == cc.REMOTE)

    def run(self, seconds=None):
        end = None if seconds is None else now_ms() + int(seconds * 1000)
        while end is None or now_ms() < end:
            self.poll()

    def wait_engine(self, limit_s=30):
        """Runs the loop until the engine is done (for tests)."""
        end = now_ms() + int(limit_s * 1000)
        while self.ctrl.searching() and now_ms() < end:
            self.poll()
        self.poll()
