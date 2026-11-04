# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Settings, from the gear on the list.

Settings > WiFi lists the saved networks (join one with a tap, or forget it)
and adds new ones: scan, pick a network, type its password on the on-screen
keyboard. app.updater is the board's network (fm1ui.metro_p4.Network): status,
scan, join, connect and saved (fm1ui.networks.Saved).
"""
# Disabled for the Learn Guides lint check: screens make their widgets in build(), each time
# they're shown; modules are imported where they're needed, to keep RAM free and start-up quick;
# methods kept on their class: the screen interface, or overridden; some drawing and protocol
# functions are long by nature.
# pylint: disable=attribute-defined-outside-init,import-outside-toplevel,no-self-use,too-many-locals
import displayio

from fm1ui import catalog as C
from fm1ui import networks as N
from fm1ui import ui
from fm1ui.layout import L
from fm1ui.screens import Screen, _hit, wrapped

ROW_H, ROW_PITCH = 28, 32
ARROW_W = 40


def _fit(name, s, w):
    return C.ellipsize(s, lambda t: ui.width(name, t), w)


def _header(g, title, back="Back"):
    """Background, the Back button and the title; returns the Back button."""
    W, H = L.W, L.H
    g.append(ui.rect(0, 0, W, H, ui.BG))
    btn = ui.Button(back, *L.BACK_BTN)
    g.append(btn.group)
    bx, _, bw, _ = L.BACK_BTN
    room = W - 2 * (bx + bw) - 8
    g.append(ui.text(ui.NAME if ui.width(ui.TITLE, title) > room else ui.TITLE,
                     _fit(ui.NAME, title, room), ui.FG, W // 2, L.SETTINGS_TITLE_Y, (0.5, 0.5)))
    return btn


def _bars(g, x, y, n, h=14):
    """Signal bars, n of 4 lit, bottom-left at (x, y + h)."""
    for i in range(4):
        bh = 4 + i * (h - 4) // 3
        g.append(ui.rect(x + i * 5, y + h - bh, 3, bh, ui.CYAN if i < n else ui.LINE))


def _switch(x, y, on):
    """An on/off switch, 46x22: a knob at the right on cyan, or at the left."""
    g = ui.outlined(x, y, 46, 22, ui.CYAN if on else ui.BG, ui.CYAN if on else ui.LINE, cut=6)
    kx = x + 26 if on else x + 4
    g.append(ui.panel(kx, y + 4, 16, 14, ui.BG if on else ui.DIM, 4))
    g.append(
        ui.text(ui.SMALL, "On" if on else "Off", ui.BG if on else ui.DIM, x - 8, y + 11, (1, 0.5))
    )
    return g


class _Paged(Screen):  # pylint: disable=abstract-method
    """A screen with a page of rows and arrows in the footer."""

    KEEP = Screen.KEEP + ("page",)

    def __init__(self, app):
        super().__init__(app)
        self.page = 0

    def rows_top(self):
        return 40

    def per_page(self):
        return max(1, (L.H - 36 - self.rows_top()) // ROW_PITCH)

    def arrows(self, g, count):
        """The footer's page arrows; sets self.pages and the arrows' rects."""
        W, H = L.W, L.H
        self.pages = C.page_count(count, self.per_page())
        self.page = min(self.page, self.pages - 1)
        y = H - 32
        self.prev_rect, self.next_rect = (6, y, ARROW_W, 28), (W - 6 - ARROW_W, y, ARROW_W, 28)
        self.prev_g = self.next_g = None
        for rect, left in ((self.prev_rect, True), (self.next_rect, False)):
            active = (self.page > 0) if left else (self.page < self.pages - 1)
            if self.pages < 2:
                continue
            bx, by, bw, bh = rect
            box = ui.outlined(bx, by, bw, bh, ui.PANEL if active else ui.BG, ui.LINE)
            g.append(box)
            g.append(
                ui.triangle(
                    bx + bw // 2 - 5, by + bh // 2 - 8, 10, 16, ui.CYAN if active else ui.LINE, left
                )
            )
            if active:
                if left:
                    self.prev_g = box
                else:
                    self.next_g = box

    def arrow_at(self, x, y):
        """-1, 1 or 0: which page arrow a tap is on."""
        if self.pages < 2:
            return 0
        if _hit(self.prev_rect, x, y, 10):
            return -1 if self.prev_g else 0
        if _hit(self.next_rect, x, y, 10):
            return 1 if self.next_g else 0
        return 0

    def turn(self, d):
        if 0 <= self.page + d < self.pages:
            self.page += d
            self.app.show()

    def swipe(self, dx):
        if self.pages > 1 and (dx < 0 and self.page < self.pages - 1):
            self.turn(1)
        elif dx > 0 and self.page > 0:
            self.turn(-1)
        elif dx > 0:
            self.app.pop()


class TextScreen(Screen):
    """A title, Back, and lines of text that drag up and down when they're
    longer than the screen. items are (font, text, colour), each wrapped to
    the width, with a gap after each; or a subclass's lines()."""

    TOP = 40  # under Back
    KEEP = Screen.KEEP + ("scroll", "_title", "_items")

    def __init__(self, app, title="", items=()):
        super().__init__(app)
        self._title = title
        self._items = items
        self.dragging = False
        self.scroll = 0

    def title(self):
        return self._title

    def lines(self):
        return self._items

    def build(self):
        W, H = L.W, L.H
        self.dragging = False
        g = displayio.Group()
        g.append(ui.rect(0, 0, W, H, ui.BG))
        body = displayio.Group()
        y = self.TOP + 4
        for name, text, color in self.lines():
            for part in C.wrap(text, lambda s, n=name: ui.width(n, s), W - 24):
                body.append(ui.text(name, part, color, 12, y, (0, 0)))
                y += 18 if name != ui.SMALL else 16
            y += 6
        g.append(body)
        self.body = body
        band = H - self.TOP - 4
        self.most = max(0, y - self.TOP - band)
        self.scroll = max(0, min(self.scroll, self.most))
        body.y = -self.scroll
        cover = displayio.Group()  # the header covers the text that scrolls under it
        self.back = _header(cover, self.title())
        cover[0].height = self.TOP  # _header's background: just the header's band
        g.append(cover)
        self.thumb = None
        if self.most:
            g.append(ui.rect(W - 4, self.TOP + 2, 2, band - 4, ui.LINE))
            self.thumb = ui.rect(
                W - 4, self.TOP + 2, 2, max(12, (band - 4) * band // (band + self.most)), ui.DIM
            )
            g.append(self.thumb)
            self._place_thumb()
        self.group = g
        return g

    def _place_thumb(self):
        if self.thumb is not None:
            room = L.H - self.TOP - 4 - 4 - self.thumb.height
            self.thumb.y = self.TOP + 2 + room * max(0, min(self.most, self.scroll)) // self.most

    def vdrag(self, dy, _x0, _y0):
        if not self.most:
            return
        if not self.dragging:
            self.dragging = True
            self.scroll0 = self.scroll
        self.scroll = max(0, min(self.most, self.scroll0 - dy))
        self.body.y = -self.scroll
        self._place_thumb()
        self.app.refresh()

    def drop(self):
        self.dragging = False

    def target(self, x, y):
        return self.back.group if self.back.hit(x, y) else None

    def tap(self, x, y):
        if self.back.hit(x, y):
            self.app.pop()

    def swipe(self, dx):
        if dx > 0:
            self.app.pop()


class CreditsScreen(TextScreen):
    """Who made what the flasher stands on."""

    def title(self):
        return "Credits"

    def lines(self):
        H, T, D = ui.NAME, ui.BODY, ui.TEXT
        return (
            (H, "FM-1 Firmware Flasher", ui.CYAN),
            (T, "By John Park for Adafruit, 2026. Open source under the GPL-3.0 license.", D),
            (H, "The FM-1 Firmware Hub", ui.CYAN),
            (
                T,
                "thefirmwarehub.com, by zvenson: the FM-1 community firmware hub. Its catalog, "
                "packages and pictures are what Catalog downloads and this flasher installs.",
                D,
            ),
            (H, "The firmware authors", ui.CYAN),
            (
                T,
                "Every firmware belongs to its authors, each under its own license, "
                "shown on its page.",
                D,
            ),
            (H, "M-VAVE", ui.CYAN),
            (T, "The FM-1, its V15 firmware and factory voices, and fm1_open (Apache-2.0).", D),
            (H, "CircuitPython and Adafruit", ui.CYAN),
            (T, "CircuitPython, displayio and its libraries, and the Metro ESP32-P4.", D),
            (H, "TinyUSB", ui.CYAN),
            (T, "The USB host that talks to the FM-1.", D),
            (H, "Fonts", ui.CYAN),
            (T, "Inter and JetBrains Mono, under the SIL Open Font License.", D),
        )


class SettingsScreen(Screen):

    def build(self):
        W = L.W
        g = displayio.Group()
        self.back = _header(g, "Settings")
        ssid, _ = self.app.updater.status()
        self.wifi_rect = (6, 44, W - 12, 40)
        x, y, w, h = self.wifi_rect
        self.wifi_g = ui.outlined(x, y, w, h, ui.PANEL, ui.LINE)
        self.wifi_g.append(ui.text(ui.NAME, "WiFi", ui.FG, x + 12, y + h // 2, (0, 0.5)))
        state = _fit(ui.BODY, ssid, w - 110) if ssid else "Not connected"
        self.wifi_g.append(
            ui.text(ui.BODY, state, ui.OK if ssid else ui.WARN, x + w - 26, y + h // 2, (1, 0.5))
        )
        self.wifi_g.append(ui.triangle(x + w - 16, y + h // 2 - 6, 7, 12, ui.DIM, False))
        g.append(self.wifi_g)
        self.scroll_rect = (x, y + h + 8, w, h)
        sx, sy = x, y + h + 8
        on = self.app.state.scroll
        self.scroll_g = ui.outlined(*self.scroll_rect, ui.PANEL, ui.LINE)
        self.scroll_g.append(
            ui.text(ui.NAME, "Scroll pages", ui.FG, sx + 12, sy + h // 2, (0, 0.5))
        )
        self.scroll_g.append(_switch(sx + w - 58, sy + (h - 22) // 2, on))
        g.append(self.scroll_g)
        self.credits_rect = (x, sy + h + 8, w, h)
        cx, cy = x, sy + h + 8
        self.credits_g = ui.outlined(*self.credits_rect, ui.PANEL, ui.LINE)
        self.credits_g.append(ui.text(ui.NAME, "Credits", ui.FG, cx + 12, cy + h // 2, (0, 0.5)))
        self.credits_g.append(ui.triangle(cx + w - 16, cy + h // 2 - 6, 7, 12, ui.DIM, False))
        g.append(self.credits_g)
        self.group = g
        return g

    def target(self, x, y):
        if self.back.hit(x, y):
            return self.back.group
        if _hit(self.wifi_rect, x, y, 3):
            return self.wifi_g
        if _hit(self.scroll_rect, x, y, 3):
            return self.scroll_g
        if _hit(self.credits_rect, x, y, 3):
            return self.credits_g
        return None

    def tap(self, x, y):
        if self.back.hit(x, y):
            self.app.pop()
        elif _hit(self.wifi_rect, x, y, 3):
            self.app.push(WifiScreen(self.app))
        elif _hit(self.scroll_rect, x, y, 3):
            self.toggle_scroll()
        elif _hit(self.credits_rect, x, y, 3):
            self.app.push(CreditsScreen(self.app))

    def toggle_scroll(self):
        """Scroll pages on or off: the list under Settings becomes the other kind."""
        from fm1ui import flat
        app = self.app
        app.state.scroll = not app.state.scroll
        app.state.save()
        old = app.stack[0]
        new = flat.list_screen(app)
        for k in ("page", "favorites_only", "tag"):
            setattr(new, k, getattr(old, k))
        old.release()
        app.stack[0] = new
        app.show()

    def swipe(self, dx):
        if dx > 0:
            self.app.pop()


class WifiScreen(_Paged):
    """The network joined, the saved networks (tap one to join it; Forget,
    then Sure? to drop it) and Add network."""

    KEEP = _Paged.KEEP + ("note", "work", "sure")

    def __init__(self, app):
        super().__init__(app)
        self.note = None  # (text, colour) in place of the status line
        self.work = None  # ssid to join on the next tick
        self.sure = None  # ssid whose Forget was tapped once

    def rows_top(self):
        return 84

    def networks(self):
        """(ssid, password, saved?) for each row: the saved ones, then settings.toml's."""
        net = self.app.updater
        saved = net.saved
        rows = [(s, p, True) for s, p in saved.items]
        toml = net.toml()
        if toml and toml[0] not in saved.ssids():
            rows.append((toml[0], toml[1], False))
        return rows

    def build(self):
        W = L.W
        g = displayio.Group()
        self.back = _header(g, "WiFi")
        ssid, ip = self.app.updater.status()
        x = 12
        if self.note:
            g.append(
                ui.text(
                    ui.BODY, _fit(ui.BODY, self.note[0], W - 2 * x), self.note[1], x, 44, (0, 0)
                )
            )
        elif ssid:
            g.append(ui.text(ui.BODY, _fit(ui.BODY, "On " + ssid, W - 2 * x), ui.OK, x, 44, (0, 0)))
            g.append(ui.text(ui.SMALL, ip, ui.DIM, x, 64, (0, 0)))
        else:
            g.append(ui.text(ui.BODY, "Not connected", ui.WARN, x, 44, (0, 0)))
        rows = self.networks()
        self.arrows(g, len(rows))
        self.rows = []
        per = self.per_page()
        top = self.rows_top()
        if not rows:
            g.append(
                ui.text(ui.BODY, "No saved networks yet.", ui.DIM, W // 2, top + 20, (0.5, 0.5))
            )
        for i, (name, _, saved) in enumerate(C.page_slice(rows, self.page, per)):
            y = top + i * ROW_PITCH
            on = name == ssid
            fw = 64 if saved else 0
            rect = (6, y, W - 12 - (fw + 6 if saved else 0), ROW_H)
            row = ui.outlined(*rect, ui.PANEL, ui.CYAN if on else ui.LINE)
            room = rect[2] - 20 - (0 if saved else ui.width(ui.SMALL, "settings.toml") + 8)
            row.append(ui.text(ui.NAME, _fit(ui.NAME, name, room), ui.CYAN if on else ui.FG,
                               16, y + ROW_H // 2, (0, 0.5)))
            g.append(row)
            forget = None
            if saved:
                frect = (W - 6 - fw, y, fw, ROW_H)
                sure = self.sure == name
                forget = ui.Button(
                    "Sure?" if sure else "Forget",
                    *frect,
                    name=ui.SMALL,
                    edge=ui.WARN if sure else ui.LINE,
                    color=ui.WARN if sure else ui.DIM
                )
                g.append(forget.group)
            else:
                g.append(
                    ui.text(ui.SMALL, "settings.toml", ui.DIM, W - 16, y + ROW_H // 2, (1, 0.5))
                )
            self.rows.append((name, rect, row, forget))
        bw = 120
        self.add = ui.Button("Add network", (W - bw) // 2, L.H - 32, bw, 28, name=ui.SMALL)
        g.append(self.add.group)
        self.group = g
        return g

    def _row_at(self, x, y):
        for name, rect, _row, forget in self.rows:
            if forget and forget.hit(x, y, 2):
                return name, forget
            if _hit(rect, x, y):
                return name, None
        return None, None

    def target(self, x, y):
        if self.back.hit(x, y):
            return self.back.group
        if self.add.hit(x, y, 4):
            return self.add.group
        a = self.arrow_at(x, y)
        if a:
            return self.prev_g if a < 0 else self.next_g
        name, forget = self._row_at(x, y)
        if forget:
            return forget.group
        if name:
            for n, _rect, row, _f in self.rows:
                if n == name:
                    return row
        return None

    def tap(self, x, y):
        if self.back.hit(x, y):
            self.app.pop()
            return
        if self.add.hit(x, y, 4):
            self.app.push(ScanScreen(self.app))
            return
        a = self.arrow_at(x, y)
        if a:
            self.turn(a)
            return
        name, forget = self._row_at(x, y)
        if forget:
            if self.sure == name:
                self.app.updater.saved.forget(name)
                self.sure = None
            else:
                self.sure = name
            self.app.show()
        elif name:
            self.sure = None
            self.note = ("Joining %s..." % name, ui.DIM)
            self.work = name
            self.app.show()

    def tick(self, now):
        if self.work is None:
            return
        name, self.work = self.work, None
        password = None
        for n, p, _saved in self.networks():
            if n == name:
                password = p
        err = self.app.updater.join(name, password or "")
        if err:
            self.note = ("Couldn't join %s (%s)" % (name, err), ui.BAD)
        else:
            self.app.updater.saved.used(name)
            self.note = None
        self.app.show()


class ScanScreen(_Paged):
    """The networks in range, strongest first; tap one to join it."""

    KEEP = _Paged.KEEP + ("found", "error")

    def __init__(self, app):
        super().__init__(app)
        self.found = None  # None: scan on the next tick
        self.error = None

    def build(self):
        W = L.W
        g = displayio.Group()
        self.back = _header(g, "Networks")
        bx, by, _, bh = L.BACK_BTN
        self.rescan = ui.Button("Rescan", W - bx - 76, by, 76, bh, name=ui.SMALL)
        g.append(self.rescan.group)
        self.rows = []
        found = self.found or []
        self.arrows(g, len(found))
        if self.found is None:
            g.append(
                ui.text(ui.BODY, "Looking for networks...", ui.DIM, W // 2, L.H // 2, (0.5, 0.5))
            )
        elif self.error:
            g.append(wrapped(ui.BODY, self.error, ui.BAD, W // 2, L.H // 2, W - 24, (0.5, 0.5)))
        elif not found:
            g.append(ui.text(ui.BODY, "No networks found.", ui.DIM, W // 2, L.H // 2, (0.5, 0.5)))
        joined, _ = self.app.updater.status()
        saved = self.app.updater.saved.ssids()
        top = self.rows_top()
        for i, (ssid, rssi, is_open) in enumerate(C.page_slice(found, self.page, self.per_page())):
            y = top + i * ROW_PITCH
            rect = (6, y, W - 12, ROW_H)
            on = ssid == joined
            row = ui.outlined(*rect, ui.PANEL, ui.CYAN if on else ui.LINE)
            note = "open" if is_open else "saved" if ssid in saved else ""
            nw = ui.width(ui.SMALL, note) + 8 if note else 0
            row.append(ui.text(ui.NAME, _fit(ui.NAME, ssid, W - 60 - nw), ui.CYAN if on else ui.FG,
                               16, y + ROW_H // 2, (0, 0.5)))
            if note:
                row.append(ui.text(ui.SMALL, note, ui.DIM, W - 40, y + ROW_H // 2, (1, 0.5)))
            _bars(row, W - 34, y + 7, N.bars(rssi))
            g.append(row)
            self.rows.append((ssid, is_open, rect, row))
        if self.found and self.pages > 1:
            g.append(
                ui.text(
                    ui.SMALL,
                    "%d/%d" % (self.page + 1, self.pages),
                    ui.FG,
                    W // 2,
                    L.H - 18,
                    (0.5, 0.5),
                )
            )
        self.group = g
        return g

    def tick(self, now):
        if self.found is not None:
            return
        try:
            self.found = self.app.updater.scan()
            self.error = None
        except (OSError, RuntimeError) as e:
            self.found, self.error = [], "Couldn't scan for networks (%s)." % (str(e) or repr(e))
        self.page = 0
        self.app.show()

    def _row_at(self, x, y):
        for ssid, is_open, rect, row in self.rows:
            if _hit(rect, x, y):
                return ssid, is_open, row
        return None, None, None

    def target(self, x, y):
        if self.back.hit(x, y):
            return self.back.group
        if self.rescan.hit(x, y):
            return self.rescan.group
        a = self.arrow_at(x, y)
        if a:
            return self.prev_g if a < 0 else self.next_g
        return self._row_at(x, y)[2]

    def tap(self, x, y):
        if self.back.hit(x, y):
            self.app.pop()
        elif self.rescan.hit(x, y):
            self.found = None
            self.app.show()
        elif self.arrow_at(x, y):
            self.turn(self.arrow_at(x, y))
        else:
            ssid, is_open, _ = self._row_at(x, y)
            if ssid:
                self.app.push(PasswordScreen(self.app, ssid, is_open))


# The keyboard's pages: rows of keys as (label, value, width in key units).
# A one-character value types itself; the others are shift, del, space and
# "to:<page>".
def _keys(chars):
    return [(c, c, 1) for c in chars]


_SPACE = ("space", "space", 7)
_PAGES = {
    "abc": ([_keys("qwertyuiop"), _keys("asdfghjkl"),
             [("shift", "shift", 1.5)] + _keys("zxcvbnm") + [("del", "del", 1.5)],
             [("123", "to:123", 3), _SPACE]]),
    "123": ([_keys("1234567890"), _keys("-/:;()$&@\""),
             [("#+=", "to:sym", 1.5)] + _keys(".,?!'") + [("del", "del", 1.5)],
             [("abc", "to:abc", 3), _SPACE]]),
    "sym": ([_keys("[]{}#%^*+="), _keys("_\\|~<>`"),
             [("123", "to:123", 1.5)] + _keys(".,?!'") + [("del", "del", 1.5)],
             [("abc", "to:abc", 3), _SPACE]]),
}


class Keyboard:
    """An on-screen keyboard in the rect (x, y, w, h): four rows of keys."""

    GAP = 3

    def __init__(self, rect):
        self.rect = rect
        self.page = "abc"
        self.shift = False
        self.group = displayio.Group()
        self.keys = []  # (cell rect, value, outlined group)
        self.draw()

    def draw(self):
        x0, y0, w, h = self.rect
        while len(self.group):
            self.group.pop()
        self.keys = []
        rows = _PAGES[self.page]
        unit = w / 10
        pitch = h // len(rows)
        for r, row in enumerate(rows):
            total = sum(k[2] for k in row)
            x = x0 + (w - total * unit) / 2
            y = y0 + r * pitch
            for label, value, units in row:
                kx, kw = int(x), int(x + units * unit) - int(x)
                if self.shift and len(value) == 1:
                    label = value = value.upper()
                lit = value == "shift" and self.shift
                g = ui.outlined(
                    kx + 1,
                    y + 1,
                    kw - self.GAP,
                    pitch - self.GAP,
                    ui.CYAN if lit else ui.PANEL,
                    ui.LINE,
                )
                font = ui.NAME if len(label) == 1 else ui.SMALL
                g.append(
                    ui.text(
                        font,
                        label,
                        ui.BG if lit else ui.FG,
                        kx + kw // 2,
                        y + pitch // 2,
                        (0.5, 0.5),
                    )
                )
                self.group.append(g)
                self.keys.append(((kx, y, kw, pitch), value, g))
                x += units * unit

    def key_at(self, x, y):
        """The key under (x, y): the cells tile the keyboard, so a touch
        between two keys goes to the nearer; one off a row's end, to its end key."""
        best, far = None, 16
        for (kx, ky, kw, kh), value, g in self.keys:
            if ky <= y < ky + kh:
                d = kx - x if x < kx else x - (kx + kw) + 1 if x >= kx + kw else 0
                if d < far:
                    best, far = (value, g), d
        return best

    def press(self, value, text):
        """Apply a key to text; returns the new text. Redraws on shift and
        page changes."""
        if value == "shift":
            self.shift = not self.shift
            self.draw()
        elif value.startswith("to:"):
            self.page, self.shift = value[3:], False
            self.draw()
        elif value == "del":
            text = text[:-1]
        else:
            text += " " if value == "space" else value
            if self.shift:
                self.shift = False
                self.draw()
        return text


class PasswordScreen(Screen):
    """Type a network's password and join it. An open network joins at
    once; a saved one starts with its password filled in."""

    KEEP = Screen.KEEP + ("ssid", "is_open", "text", "note", "work", "kb_state")
    MAX_LEN = 63  # WPA passphrases

    def __init__(self, app, ssid, is_open):
        super().__init__(app)
        self.ssid = ssid
        self.is_open = is_open
        self.text = app.updater.saved.password(ssid) or ""
        self.note = None
        self.kb_state = ("abc", False)
        self.work = is_open  # an open network: join at once

    def build(self):
        W, H = L.W, L.H
        g = displayio.Group()
        self.back = _header(g, self.ssid, back="Cancel")
        bx, by, bw, bh = L.BACK_BTN
        self.join = ui.Button(
            "Join", W - bx - bw, by, bw, bh, fill=ui.CYAN, edge=ui.CYAN, color=ui.BG
        )
        g.append(self.join.group)
        self.field_rect = (6, 38, W - 12, 30)
        g.append(ui.outlined(*self.field_rect, ui.PANEL, ui.LINE))
        self.field_at = len(g)
        g.append(self.field())
        self.kb = Keyboard((6, 74, W - 12, H - 76))
        self.kb.page, self.kb.shift = self.kb_state
        self.kb.draw()
        g.append(self.kb.group)
        self.group = g
        return g

    def field(self):
        """The password as typed (shown: it's hard enough on a small
        keyboard), or a note, with a caret."""
        x, y, w, h = self.field_rect
        fg = displayio.Group()
        if self.note:
            fg.append(
                ui.text(
                    ui.BODY,
                    _fit(ui.BODY, self.note[0], w - 16),
                    self.note[1],
                    x + 8,
                    y + h // 2,
                    (0, 0.5),
                )
            )
            return fg
        s = self.text
        room = w - 22
        while s and ui.width(ui.BODY, s) > room:  # the end of a long one
            s = s[1:]
        if s:
            fg.append(ui.text(ui.BODY, s, ui.FG, x + 8, y + h // 2, (0, 0.5)))
        cx = x + 8 + (ui.width(ui.BODY, s) if s else 0) + 2
        fg.append(ui.rect(cx, y + 7, 2, h - 14, ui.CYAN))
        return fg

    def redraw_field(self):
        self.group[self.field_at] = self.field()
        self.app.refresh()

    def target(self, x, y):
        if self.work:
            return None
        if self.back.hit(x, y):
            return self.back.group
        if self.join.hit(x, y):
            return self.join.group
        k = self.kb.key_at(x, y)
        return k[1] if k else None

    def tap(self, x, y):
        if self.work:
            return
        if self.back.hit(x, y):
            self.app.pop()
        elif self.join.hit(x, y):
            self.start()
        else:
            k = self.kb.key_at(x, y)
            if k:
                text = self.kb.press(k[0], self.text)
                self.kb_state = (self.kb.page, self.kb.shift)
                self.text = text[:self.MAX_LEN]
                self.note = None
                self.redraw_field()

    def start(self):
        if not self.is_open and len(self.text) < 8:
            self.note = ("A WiFi password has at least 8 characters.", ui.WARN)
        else:
            self.note = ("Joining...", ui.DIM)
            self.work = True
        self.redraw_field()

    def tick(self, now):
        if not self.work:
            return
        self.work = False
        password = "" if self.is_open else self.text
        err = self.app.updater.join(self.ssid, password)
        if err:
            self.note = ("Couldn't join: " + err, ui.BAD)
            self.redraw_field()
            return
        self.app.updater.saved.add(self.ssid, password)
        # Back to Settings > WiFi, past the scan.
        while len(self.app.stack) > 1 and not isinstance(self.app.stack[-1], WifiScreen):
            self.app.stack.pop()
        if isinstance(self.app.stack[-1], WifiScreen):
            self.app.stack[-1].note = None
        self.app.show()
