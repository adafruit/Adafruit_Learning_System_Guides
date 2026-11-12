#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Run the flasher UI on the desktop with Blinka displayio.

  .venv/bin/python tools/ui_sim.py --root sd_out/full/firmware            # window; click and drag
  .venv/bin/python tools/ui_sim.py --root ... --do "shot list.png" --do "tap 60,100" --do "shot detail.png"

Needs a venv with adafruit-blinka-displayio, adafruit-circuitpython-display-text,
adafruit-circuitpython-bitmap-font, Pillow and (for the window) pygame.
The FM-1 is faked (--identity) and installs only animate the progress screen.

Script steps (--do, in order): "drag DX[,STEPS]" (drag and let go; Metro list), "hold DX",
"vdrag DY[,STEPS]", "vhold DY" (up and down: Metro details), "tap X,Y", "press X,Y" (touch down, held), "swipe DX", "shot FILE.png",
"identity ID" (or "identity none": unplugged), "connect", "phase NAME PCT", "wait", "found",
"finish ok [MSG]", "finish fail MSG", "steps N" (run the loop N times), "until MODE" (run the
loop until the Update screen reaches plan, run, done or error; "until Pictures" also works,
for the run's phase).

--hub turns on Update firmwares with the real hub over this computer's network
(--hub-only ID,ID,... shows the device a catalog of just those firmwares).
It writes to --root: use a copy.

Window keys:
  f  plug or unplug the FM-1 (as --identity; then tap Connect FM-1)
  x  fail the install that's running
  s  stall: the FM-1 doesn't come back after its restart, so the install
     waits there (the power-cycle hint shows after 20 s); s again resumes
  h  list these keys
The window's title shows the FM-1's state.
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "FM-1_Flasher_Code", "lib"))

import busdisplay  # noqa: E402
from displayio._area import Area  # noqa: E402
from PIL import Image  # noqa: E402

from fm1ui import app as A  # noqa: E402
from fm1ui import catalog as C  # noqa: E402
from fm1ui import screens as S  # noqa: E402
from fm1ui import ui  # noqa: E402

ui.FONT_DIR = os.path.join(ROOT, "FM-1_Flasher_Code", "fonts")


class SimDisplay(busdisplay.BusDisplay):
    """A displayio display that draws into a Pillow image."""

    def __init__(self, width=320, height=240):
        self.image = Image.new("RGB", (width, height))
        self.on_refresh = None
        super().__init__(None, (), width=width, height=height, auto_refresh=False)

    def _background(self):
        pass

    def _write(self, command, data):
        pass

    def _get_refresh_areas(self):
        return [self._core.area]

    def _refresh_area(self, area):
        c = Area()
        if not self._core.clip_area(area, c):
            return True
        n = c.size()
        buf = memoryview(bytearray(n * 2 + 4))
        mask = memoryview(bytearray(((n // 32) + 1) * 4)).cast("I")
        self._core.fill_area(c, mask, buf)
        raw = bytes(buf)[:n * 2]
        img = Image.frombuffer("RGB", (c.width(), c.height()), bytes(_rgb565_to_rgb(raw)), "raw", "RGB", 0, 1)
        self.image.paste(img, (c.x1, c.y1))
        return True

    def refresh(self, *args, **kwargs):
        super().refresh(*args, **kwargs)
        if self.on_refresh:
            self.on_refresh(self.image)


def _rgb565_to_rgb(raw):
    out = bytearray(len(raw) // 2 * 3)
    o = 0
    for i in range(0, len(raw), 2):
        v = (raw[i] << 8) | raw[i + 1]
        out[o] = ((v >> 11) & 31) * 255 // 31
        out[o + 1] = ((v >> 5) & 63) * 255 // 63
        out[o + 2] = (v & 31) * 255 // 31
        o += 3
    return out


class FakeProbe:
    """An FM-1 that answers as `ident` (None: nothing attached)."""

    def __init__(self, ident):
        self.ident = ident

    def connect(self):
        return self.ident

    def present(self):
        return self.ident is not None

    def close(self):
        pass


class ScriptTouch:
    def __init__(self):
        self.queue = []

    def event(self):
        return self.queue.pop(0) if self.queue else None


class FakeInstaller:
    """Shows the progress screen. In the window it animates a whole install,
    which the window's keys can stall or fail."""

    PHASES = (("Staging loader", 4), ("Restarting", 3), ("Writing firmware", 8), ("Verifying", 1))

    def __init__(self, animate):
        self.animate = animate
        self.stall = False  # the FM-1 doesn't come back after its restart
        self.screen = None

    def running(self):
        return self.screen is not None and self.screen.done is None

    def fail(self, message):
        if self.running():
            self.screen.finish(False, message)

    def start(self, app, entry):
        screen = self.screen = S.ProgressScreen(app, entry)
        app.push(screen)
        if not self.animate:
            return
        steps = []
        t = 0
        for name, secs in self.PHASES:
            steps.append((t, name, secs))
            t += secs
        clock = [time.monotonic(), 0.0]  # the last tick, and install time, which a stall stops
        orig_tick = screen.tick

        def tick(now):
            if screen.done is None:
                at, held = clock[1], False
                for start, name, secs in steps:
                    if start <= at < start + secs:
                        if name == "Restarting":
                            if screen.waiting_since is None:
                                screen.wait("app")
                            held = self.stall
                        else:
                            screen.phase(name, min(99, int((at - start) * 100 / secs)))
                if not held:
                    clock[1] += now - clock[0]
                clock[0] = now
                if clock[1] >= t:
                    app.state.record_install(entry.slug, entry.product)
                    app.identity = app.probe.ident = entry.product
                    screen.finish(True, "The FM-1 restarted with %s." % entry.name)
            orig_tick(now)
        screen.tick = tick


class HubNet:
    """fm1ui.update's network, with urllib."""

    # Settings > WiFi's networks, simulated: these are "in range", any
    # password joins except "wrongpass", and the saved list is a JSON file.
    IN_RANGE = [("Home Studio", -48, False), ("Cafe Guest", -71, True), ("Rehearsal Room 5G", -62, False),
                ("Neighbors", -84, False), ("Venue Backstage", -58, False), ("Printer-1234", -77, True),
                ("Studio B", -66, False)]

    def __init__(self, only=None, wifi_path=None):
        from fm1ui import networks
        self.only = only
        self.joined = "Home Studio"
        self.wifi_path = wifi_path

        def load():
            try:
                with open(wifi_path) as f:
                    return f.read()
            except (OSError, TypeError):
                return None

        def store(s):
            if wifi_path:
                with open(wifi_path, "w") as f:
                    f.write(s)
            return True
        self.saved = networks.Saved(load, store)

    def toml(self):
        return ("Home Studio", "hunter22")

    def connect(self):
        return None

    def status(self):
        return (self.joined, "192.168.1.42") if self.joined else (None, None)

    def scan(self):
        from fm1ui import networks
        return networks.strongest(self.IN_RANGE)

    def join(self, ssid, password):
        if password == "wrongpass":
            return "Authentication failure"
        self.joined = ssid
        return None

    def _open(self, url):
        import urllib.request
        return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FM-1_Flasher ui_sim"}),
                                      timeout=60)

    def get(self, url):
        try:
            with self._open(url) as r:
                return r.read()
        except Exception as e:
            raise OSError(str(e))

    def get_json(self, url):
        import json
        cat = json.loads(self.get(url))
        if self.only:
            cat["firmwares"] = [e for e in cat["firmwares"] if e["id"] in self.only]
            if "stock-v15" not in self.only:
                cat.pop("stock", None)
        return cat

    def stream(self, url, chunk=8192):
        with self._open(url) as r:
            while True:
                data = r.read(chunk)
                if not data:
                    break
                yield data


def home_screen(app):
    """The list as the device has it: with Update (--hub), the one that
    scrolls when Settings > Scroll pages is on."""
    if app.updater is not None:
        from fm1ui import flat
        return flat.list_screen(app)
    return S.ListScreen(app)


def run_script(app, touch, steps):
    app.push(home_screen(app))
    for step in steps:
        cmd, _, arg = step.partition(" ")
        screen = app.stack[-1]
        if cmd == "tap":
            x, y = (int(v) for v in arg.split(","))
            touch.queue.append(("tap", x, y))
            app.step()
        elif cmd == "press":
            x, y = (int(v) for v in arg.split(","))
            touch.queue.append(("down", x, y))
            app.step()
        elif cmd == "swipe":
            touch.queue.append(("swipe", int(arg)))
            app.step()
        elif cmd == "drag":  # "drag DX" or "drag DX,STEPS": a finger dragged DX px, then let go
            dx, _, n = arg.partition(",")
            dx, n = int(dx), int(n or 8)
            touch.queue.append(("down", 160, 120))
            app.step()
            for i in range(1, n + 1):
                touch.queue.append(("drag", dx * i // n, 160, 120))
                app.step()
                time.sleep(0.03)
            touch.queue.append(("up",))
            app.step()
        elif cmd == "vdrag":  # "vdrag DY" or "vdrag DY,STEPS": a finger dragged up (DY < 0) or down, then let go
            dy, _, n = arg.partition(",")
            dy, n = int(dy), int(n or 8)
            touch.queue.append(("down", 160, 120))
            app.step()
            for i in range(1, n + 1):
                touch.queue.append(("vdrag", dy * i // n, 160, 120))
                app.step()
                time.sleep(0.03)
            touch.queue.append(("up",))
            app.step()
        elif cmd == "vhold":  # "vhold DY": drag DY px up or down and keep the finger down
            touch.queue.append(("down", 160, 120))
            app.step()
            touch.queue.append(("vdrag", int(arg), 160, 120))
            app.step()
        elif cmd == "release":  # let go after "hold"
            touch.queue.append(("up",))
            app.step()
        elif cmd == "hold":  # "hold DX": drag DX px and keep the finger down (for a shot mid-drag)
            touch.queue.append(("down", 160, 120))
            app.step()
            touch.queue.append(("drag", int(arg), 160, 120))
            app.step()
        elif cmd == "shot":
            app.display.image.save(arg)
            print("wrote", arg)
        elif cmd == "identity":
            app.probe.ident = None if arg == "none" else arg
            app.next_probe = 0
            app.step()
        elif cmd == "connect":
            app.connect()
        elif cmd == "phase":
            name, _, pct = arg.rpartition(" ")
            screen.phase(name, int(pct))
            screen.redraw(force=True)  # phase() redraws at most once a second
        elif cmd == "wait":
            screen.wait("app")
        elif cmd == "found":
            screen.found()
        elif cmd == "finish":
            ok, _, msg = arg.partition(" ")
            screen.finish(ok == "ok", msg)
        elif cmd == "steps":
            for _ in range(int(arg)):
                app.step()
        elif cmd == "until":
            t = time.monotonic()
            while time.monotonic() - t < 600:
                s = app.stack[-1]
                mode = getattr(s, "mode", None)
                if mode == arg or (mode == "run" and s.phase.text == arg):
                    break
                app.step()
            else:
                sys.exit("timed out waiting for " + arg)
            app.stack[-1].last_draw = 0
            app.step()  # draw it
            app.refresh()
        else:
            sys.exit("unknown step: " + step)


KEYS = """keys: f plug/unplug the FM-1, x fail the install, s stall the FM-1's restart, h this list"""


def run_window(app, scale, identity):
    import pygame
    pygame.init()
    w, h = app.display.width, app.display.height
    win = pygame.display.set_mode((w * scale, h * scale))
    installer = app.installer
    last = [app.probe.ident or identity]  # what the FM-1 answers as when plugged back in

    def caption():
        fm1 = ("FM-1 %s plugged in" % app.probe.ident) if app.probe.ident else "no FM-1"
        stall = ", restart stalls" if installer.stall else ""
        pygame.display.set_caption("FM-1 Flasher (simulator): %s%s. Keys: f x s h" % (fm1, stall))

    def key(k):
        if k == "f":
            if app.probe.ident:
                last[0], app.probe.ident = app.probe.ident, None
            else:
                app.probe.ident = last[0]
            print("FM-1", "plugged in, as " + app.probe.ident if app.probe.ident else "unplugged")
            app.next_probe = 0  # notice an unplug at once
        elif k == "x":
            if installer.running():
                installer.fail("No reply from the FM-1 (simulated failure)")
                print("install failed")
            else:
                print("no install running")
        elif k == "s":
            installer.stall = not installer.stall
            print("the FM-1's restart", "stalls" if installer.stall else "goes ahead")
        elif k == "h":
            print(KEYS)
        caption()

    print(KEYS)
    caption()
    gestures = A.Gestures()
    app.touch = gestures

    def blit(image):
        surf = pygame.image.frombuffer(image.tobytes(), image.size, "RGB")
        if scale != 1:
            surf = pygame.transform.scale(surf, (w * scale, h * scale))
        win.blit(surf, (0, 0))
        pygame.display.flip()

    app.display.on_refresh = blit
    app.push(home_screen(app))
    down = False
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.MOUSEBUTTONDOWN:
                down = True
            elif ev.type == pygame.MOUSEBUTTONUP:
                down = False
                gestures.sample(None)
            elif ev.type == pygame.KEYDOWN and ev.unicode:
                key(ev.unicode.lower())
        if down:
            mx, my = pygame.mouse.get_pos()
            gestures.sample((mx // scale, my // scale))
        app.step()
        time.sleep(0.01)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.join(ROOT, "sd_out", "full", "firmware"))
    ap.add_argument("--state", help="state JSON (default: flasher-sim.json next to --root)")
    ap.add_argument("--identity", default="FM-1_015", help="what the fake FM-1 answers to Connect, or 'none'")
    ap.add_argument("--do", action="append", default=[], help="script step (headless)")
    ap.add_argument("--scale", type=int, default=2, help="window zoom")
    ap.add_argument("--hub", action="store_true", help="Update firmwares from the real hub (writes to --root)")
    ap.add_argument("--hub-only", help="with --hub: a catalog of only these ids (comma-separated)")
    args = ap.parse_args()

    state = C.State(args.state or os.path.join(os.path.dirname(args.root.rstrip("/")), "flasher-sim.json"))
    touch = ScriptTouch()
    probe = FakeProbe(None if args.identity == "none" else args.identity)
    net = (HubNet(args.hub_only.split(",") if args.hub_only else None, state.path + ".wifi")
           if args.hub or args.hub_only else None)
    app = A.App(SimDisplay(), touch, args.root, state, probe, FakeInstaller(animate=not args.do),
                updater=net)
    if args.do:
        run_script(app, touch, args.do)
    else:
        run_window(app, args.scale, args.identity if args.identity != "none" else "FM-1_015")


if __name__ == "__main__":
    main()
