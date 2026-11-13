# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""The list with scrolling pages, for the Metro ESP32-P4 (Settings > Scroll).

Each page of cards (or names) is drawn once into one bitmap, which displayio
can slide across the screen at 20-30 frames a second; the list's own cards,
built of shapes and text, manage 10 (tools/device/metro_spike_scroll.py). The
pages follow the finger and glide to the next one when let go.

ScrollList is ListScreen with the cards replaced by those pages; everything
else (header, footer, filters, taps) is ListScreen's. It keeps the current
page and its neighbors across rebuilds, and draws a missing neighbor a card
at a time between touches.
"""
# Disabled for the Learn Guides lint check: screens make their widgets in build(), each time
# they're shown; modules are imported where they're needed, to keep RAM free and start-up quick;
# methods kept on their class: the screen interface, or overridden; fm1ui's modules share a few
# internal helpers; some drawing and protocol functions are long by nature.
# pylint: disable=attribute-defined-outside-init,import-outside-toplevel,no-self-use
# pylint: disable=protected-access,too-many-locals
# pylint: disable=cyclic-import  # the cycles go through imports inside functions
import time

import bitmaptools
import displayio

from fm1ui import catalog as C
from fm1ui import screens as S
from fm1ui import ui
from fm1ui.layout import L

# Palette indices: the UI's colors at fixed places (0 stays unused, so ink
# is never 0, the "no ink" index of the 1-bit font sheets), then 16 for each
# card's picture.
_COLORS = [0x000000, ui.BG, ui.PANEL, ui.LINE, ui.FG, ui.TEXT, ui.DIM, ui.CYAN, ui.OK, ui.WARN,
           ui.BAD, ui.HEART, ui.BEIGE, ui.THUMB_BG]
for _c in ui.KIND_COLORS.values():
    if _c not in _COLORS:
        _COLORS.append(_c)
_INDEX = {c: i for i, c in enumerate(_COLORS)}
PIC0 = 64  # card i's picture colors: PIC0 + 16 * i
GLIDE_FRAMES = 8
FLICK_PX_S = 400  # a let-go this fast turns the page whatever the distance
BAND_GAP = 4  # between the page band and the footer
TAP_PX = 30  # fm1ui.app.Gestures.TAP_PX


def ci(color):
    return _INDEX.get(color, _INDEX[ui.BEIGE])


_sheets = {}


def _sheet(name, index):
    """The font's glyph sheet with its ink as palette index `index`:
    filled with the index, then the sheet's blank pixels copied over it."""
    key = (name, index)
    s = _sheets.get(key)
    if s is None:
        src = ui.font(name).sheet
        s = displayio.Bitmap(src.width, src.height, 256)
        # fill_region, not fill: Blinka's Bitmap.fill (the simulator) fills
        # only part of a 256-color bitmap.
        bitmaptools.fill_region(s, 0, 0, src.width, src.height, index)
        bitmaptools.blit(s, src, 0, 0, skip_source_index=1)
        _sheets[key] = s
    return s


class Canvas:
    """A page: one 256-color bitmap for the band of the screen from y = top,
    drawn in screen coordinates."""

    def __init__(self, w, top, h):
        self.top = top
        self.bmp = displayio.Bitmap(w, h, 256)
        self.pal = displayio.Palette(256)
        for i, c in enumerate(_COLORS):
            self.pal[i] = c
        bitmaptools.fill_region(self.bmp, 0, 0, w, h, ci(ui.BG))

    def fill(self, x, y, w, h, color):
        y -= self.top
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(self.bmp.width, x + w), min(self.bmp.height, y + h)
        if x1 < x2 and y1 < y2:
            bitmaptools.fill_region(self.bmp, x1, y1, x2, y2, ci(color))

    def panel(self, x, y, w, h, color, cut, under):
        """ui.panel: a rectangle with its corners cut at 45 degrees."""
        self.fill(x, y, w, h, color)
        for i in range(cut):
            n = cut - i
            for row in (y + i, y + h - 1 - i):
                self.fill(x, row, n, 1, under)
                self.fill(x + w - n, row, n, 1, under)

    def outlined(self, x, y, w, h, fill, edge, cut=4, under=ui.BG):
        self.panel(x, y, w, h, edge, cut, under)
        self.panel(x + 1, y + 1, w - 2, h - 2, fill, cut - 1 if cut > 1 else 0, edge)

    def text(self, name, s, color, x, y, anchor=(0, 0)):
        """As ui.text(name, s, color, x, y, anchor), drawn into the page."""
        f = ui.font(name)
        sheet = _sheet(name, ci(color))
        t = f.table
        rows = [f._find(ord(ch)) for ch in s]
        pad = 0
        if rows:
            left = t[rows[0] + 5]
            pad = (256 - left) if left > 127 else 0
        ax, ay = anchor
        x0 = int(x - ax * f.width(s)) - pad
        y0 = int(y - ay * f.cap) - (f.ascent - f.cap) - self.top
        sy1, sy2 = max(0, -y0), min(f.height, self.bmp.height - y0)  # the rows in the band
        if sy1 >= sy2:
            return
        pen = pad
        for o in rows:
            gw = t[o + 4]
            if gw:
                left = t[o + 5]
                left = left - 256 if left > 127 else left
                gx = x0 + pen + left
                sx = t[o + 2] | (t[o + 3] << 8)
                if gx >= 0 and gx + gw <= self.bmp.width:
                    bitmaptools.blit(
                        self.bmp,
                        sheet,
                        gx,
                        y0 + sy1,
                        x1=sx,
                        y1=sy1,
                        x2=sx + gw,
                        y2=sy2,
                        skip_source_index=0,
                    )
            pen += t[o + 6]

    def heart(self, filled, x, y, under=ui.PANEL):
        """ui.heart_tile(filled, x, y), drawn into the page."""
        self.fill(x, y, 13, len(ui._HEART), under)
        y -= self.top
        ink, dim = ci(ui.HEART), ci(ui.DIM)
        for yy, row in enumerate(ui._HEART):
            for xx, c in enumerate(row):
                if c == "#":
                    self.bmp[x + xx, y + yy] = ink if filled else dim
                elif filled and c == "+":
                    self.bmp[x + xx, y + yy] = ink

    def picture(self, path, x, y, size, placeholder, slot):
        """ui.thumbnail(path, x, y, size, placeholder): the picture shrunk
        from a pool tile, its colors at PIC0 + 16 * slot."""
        tile = ui.slots()[0]
        try:
            pal = ui.load_tiles(path, [tile])
        except (OSError, ValueError) as e:
            if getattr(e, "errno", None) != 2:
                print("no picture:", path, repr(e))
            self.fill(x, y, size, size, ui.THUMB_BG)
            self.text(ui.NAME, placeholder, ui.BEIGE, x + size // 2, y + size // 2, (0.5, 0.5))
            return
        base = PIC0 + 16 * slot
        for i in range(len(pal)):
            self.pal[base + i] = pal[i]
        step = ui.TILE // size
        bmp, top = self.bmp, y - self.top
        for yy in range(size):
            sy, dy = yy * step, top + yy
            for xx in range(size):
                bmp[x + xx, dy] = base + tile[xx * step, sy]


class Page:
    """One page of the list as a Canvas, drawn a card at a time by steps().
    cards: (entry, card rect, heart rect, heart position) in screen
    coordinates, for the page in place (strip at x = 0)."""

    def __init__(self, screen, n, entries, installed):
        self.n = n
        self.entries = entries
        self.installed = installed
        self.cards = []
        self.canvas = Canvas(L.W, L.GRID_Y, band_height())
        self.app = screen.app
        self.as_list = screen.app.state.view == "list"
        self.work = self.steps()
        self.tile = None

    def done(self):
        return self.work is None

    def step(self):
        """Draw one more card; True when the page is finished."""
        if self.work is not None:
            try:
                next(self.work)
            except StopIteration:
                self.work = None
        return self.work is None

    def finish(self):
        while not self.step():
            pass
        return self

    def grid(self):
        """The page's TileGrid (one per page, made when first needed)."""
        if self.tile is None:
            self.tile = displayio.TileGrid(
                self.canvas.bmp, pixel_shader=self.canvas.pal, y=L.GRID_Y
            )
        return self.tile

    def steps(self):
        for i, e in enumerate(self.entries):
            if self.as_list:
                x = L.GRID_X + (i // L.LIST_ROWS) * (L.ROW_W + L.GAP)
                self.row(e, x, L.GRID_Y + (i % L.LIST_ROWS) * L.ROW_PITCH, e.slug == self.installed)
            else:
                x = L.GRID_X + (i % L.COLS) * (L.CARD_W + L.GAP)
                y = L.GRID_Y + (i // L.COLS) * (L.CARD_H + L.GAP)
                self.card(e, x, y, e.slug == self.installed, i)
            yield

    def card(self, e, x, y, installed, slot):
        """ListScreen.card, drawn into the page."""
        cv = self.canvas
        cw, ch, thumb = L.CARD_W, L.CARD_H, L.THUMB
        cv.outlined(x, y, cw, ch, ui.PANEL, ui.CYAN if installed else ui.LINE)
        if installed:
            cv.panel(x + 1, y + 1, cw - 2, ch - 2, ui.CYAN, 3, ui.CYAN)
            cv.panel(x + 2, y + 2, cw - 4, ch - 4, ui.PANEL, 2, ui.CYAN)
        cv.fill(x + 4, y + 2, cw - 8, 3, ui.kind_color(e.kind))
        tx, ty = x + (cw - thumb) // 2, y + L.CARD_THUMB_Y
        cv.picture(self.app.path(e.slug, "thumb.bmp"), tx, ty, thumb, e.version, slot)
        if installed:
            bx, bw = x + 4, cw - 8  # across the card, not just the picture
            cv.fill(bx, ty + thumb - 12, bw, 12, ui.CYAN)
            cv.text(ui.SMALL, "INSTALLED", ui.BG, bx + bw // 2, ty + thumb - 6, (0.5, 0.5))
        heart = (x + cw - 15, y + 10)
        cv.heart(e.slug in self.app.state.favorites, *heart)
        name = C.ellipsize(e.name, lambda s: ui.width(ui.NAME, s), cw - 8)
        cv.text(ui.NAME, name, ui.FG, x + cw // 2, y + L.CARD_NAME_Y, (0.5, 0))
        vy = y + L.CARD_VERSION_Y
        version = C.ellipsize(
            e.version, lambda s: ui.width(ui.SMALL, s), cw - (50 if e.beta else 8)
        )
        if e.beta:
            vw, bw = ui.width(ui.SMALL, version + " "), ui.width(ui.SMALL, "beta")
            left = x + (cw - vw - bw) // 2
            cv.text(ui.SMALL, version, ui.DIM, left, vy, (0, 0))
            cv.text(ui.SMALL, "beta", ui.WARN, left + vw, vy, (0, 0))
        else:
            cv.text(ui.SMALL, version, ui.DIM, x + cw // 2, vy, (0.5, 0))
        self.cards.append((e, (x, y, cw, ch), (x + cw - 28, y - L.GAP, 28 + L.GAP, 50), heart))

    def row(self, e, x, y, installed):
        """ListScreen.row, drawn into the page."""
        cv = self.canvas
        rw, rh = L.ROW_W, L.ROW_H
        cv.outlined(x, y, rw, rh, ui.PANEL, ui.CYAN if installed else ui.LINE)
        cv.fill(x + 5, y + 6, 3, rh - 12, ui.kind_color(e.kind))
        name = C.ellipsize(e.name, lambda s: ui.width(ui.NAME, s), rw - 50)
        cv.text(ui.NAME, name, ui.CYAN if installed else ui.FG, x + 16, y + rh // 2, (0, 0.5))
        heart = (x + rw - 22, y + L.ROW_HEART_DY)
        cv.heart(e.slug in self.app.state.favorites, *heart)
        self.cards.append((e, (x, y, rw, rh), (x + rw - 40, y - 1, 46, rh + 2), heart))


def band_height():
    return L.PREV[1] - BAND_GAP - L.GRID_Y


class Highlight(displayio.Group):
    """The pressed card: a cyan frame over it. ui.press() and ui.release()
    call press() and release() on it, as for a button's shapes."""

    def __init__(self):
        super().__init__()
        self.hidden = True
        self.size = None

    def place(self, rect):
        x, y, w, h = rect
        if self.size != (w, h):
            while len(self):
                self.pop()
            for rx, ry, rw, rh in ((0, 0, w, 2), (0, h - 2, w, 2), (0, 0, 2, h), (w - 2, 0, 2, h)):
                self.append(ui.rect(rx, ry, rw, rh, ui.CYAN))
            self.size = (w, h)
        self.x, self.y = x, y
        return self

    def press(self):
        self.hidden = False

    def release(self, _old):
        self.hidden = True


class Scroller:
    """Dragging a strip of pages: self.page of self.pages is in place at
    strip.x = 0. The screen provides _ready(n) (page n drawn and in the
    strip), _turned(d) (now on page + d) and _scrolling() (anything to move)."""

    def _offset(self, dx):
        """The strip's x for a drag of dx, with a rubber band past the ends."""
        if (dx > 0 and self.page == 0) or (dx < 0 and self.page >= self.pages - 1):
            return dx // 3
        return max(-L.W, min(L.W, dx))

    def _neighbors(self):
        return [n for n in (self.page + 1, self.page - 1) if 0 <= n < self.pages]

    def drag(self, dx, x0, y0):
        if not self._scrolling():
            return
        if not self.dragging:
            self.dragging = True
            self.drag_start = (x0, y0)
            self.hist = []
            for n in self._neighbors():
                self._ready(n)
        self.hist.append((time.monotonic(), dx))
        x = self._offset(dx)
        if x != self.strip.x:
            self.strip.x = x
            self.app.refresh()

    def drop(self):
        """The finger let go after a drag: glide to the next page after a
        flick or a drag past a quarter of the screen, else back. A drag too
        short to be one is a tap where it started."""
        self.dragging = False
        hist = self.hist
        dx = hist[-1][1] if hist else 0
        now = hist[-1][0] if hist else 0
        recent = [h for h in hist if now - h[0] <= 0.12] or hist[-2:]
        v = 0
        if len(recent) > 1:
            v = (recent[-1][1] - recent[0][1]) / max(0.001, recent[-1][0] - recent[0][0])
        d = 0
        if (dx < -L.W // 4 or v < -FLICK_PX_S) and self.page < self.pages - 1:
            d = 1
        elif (dx > L.W // 4 or v > FLICK_PX_S) and self.page > 0:
            d = -1
        self._glide(-d * L.W)
        if d:
            self._turned(d)
        elif abs(dx) <= TAP_PX:  # a tap that rolled: as a tap
            self.tap(*self.drag_start)

    def _glide(self, target):
        start = self.strip.x
        for f in range(1, GLIDE_FRAMES + 1):
            e = 1 - (1 - f / GLIDE_FRAMES) ** 3
            self.strip.x = int(start + (target - start) * e)
            self.app.refresh()

    def turn(self, delta):
        page = self.page + delta
        if not self._scrolling() or not 0 <= page < self.pages:
            return
        self._ready(page)
        self._glide(-delta * L.W)
        self._turned(delta)

    def swipe(self, dx):
        pass  # drags do it

    def _attach_tile(self, t, n):
        """Put page n's TileGrid in the strip, beside the current page."""
        t.x = (n - self.page) * L.W
        for i in range(len(self.strip)):
            if self.strip[i] is t:
                return
        self.strip.append(t)

    def _empty_strip(self):
        # The cached pages' TileGrids go into the next build's strip, and a
        # TileGrid can be in one group at a time.
        strip = getattr(self, "strip", None)
        while strip is not None and len(strip):
            strip.pop()


class ScrollList(Scroller, S.ListScreen):
    """ListScreen whose pages scroll with the finger."""

    KEEP = S.ListScreen.KEEP + ("flat",)

    def __init__(self, app):
        super().__init__(app)
        self.flat = {"key": None, "pages": {}}
        self.dragging = False

    def release(self):
        self._empty_strip()
        super().release()

    def _scrolling(self):
        return bool(getattr(self, "_items", None))

    # -- pages ------------------------------------------------------------------

    def _key(self):
        st = self.app.state
        return (self.tag, self.favorites_only, st.view, st.sort, self.app.installed_slug(),
                tuple(sorted(st.favorites)), id(self.app.index), st.new_chip)

    def _page(self, n, finish=True):
        """Page n, from the cache or started; finished unless finish=False."""
        pages = self.flat["pages"]
        p = pages.get(n)
        if p is None:
            per = self.per_page()
            entries = [self.app.index.entry(i) for i in C.page_slice(self._items, n, per)]
            p = pages[n] = Page(self, n, entries, self.flat["installed"])
        return p.finish() if finish else p

    def card(self, e, x, y, installed, slot):
        return displayio.Group()  # the page's bitmap has the cards

    def row(self, e, x, y, installed):
        return displayio.Group()

    def build(self):
        self.dragging = False
        key = self._key()
        if key != self.flat["key"]:
            self.flat = {"key": key, "pages": {}, "installed": key[4]}
        g = super().build()
        self._items = self.items()
        self.cards = []
        if not self._items:
            return g
        keep = (self.page - 1, self.page, self.page + 1)
        pages = self.flat["pages"]
        for n in list(pages):
            if n not in keep:
                del pages[n]
        cur = self._page(self.page)
        self.strip = displayio.Group()
        self.strip.append(cur.grid())
        cur.tile.x = 0
        for n in self._neighbors():
            p = pages.get(n)
            if p is not None and p.done():
                self._attach(p)
        g.append(self.strip)
        self.highlight = Highlight()
        g.append(self.highlight)
        return g

    def _attach(self, p):
        self._attach_tile(p.grid(), p.n)

    def _ready(self, n):
        """Page n drawn and in the strip (drawn now if it wasn't)."""
        self._attach(self._page(n))

    def tick(self, now):
        """Draw the neighbors a card at a time between touches."""
        if self.dragging or not getattr(self, "_items", None):
            return
        for n in self._neighbors():
            p = self._page(n, finish=False)
            if not p.done():
                if p.step():
                    self._attach(p)
                return

    # -- moving -----------------------------------------------------------------

    def _turned(self, d):
        self.page += d
        self.app.show()  # the header and footer for the new page; pages from the cache

    # -- taps on the cards ---------------------------------------------------------

    def _hit_card(self, x, y):
        """(entry, heart position or None, card rect) under a touch on the
        current page, or (None, None, None)."""
        p = self.flat["pages"].get(self.page)
        if p is None or self.strip.x != 0:
            return None, None, None
        for i, (e, card, heart, heart_at) in enumerate(p.cards):
            if S._hit(heart, x, y):
                return e, heart_at, card
            if S._hit(card, x, y):
                self._tapped = self.page * self.per_page() + i
                return e, None, card
        return None, None, None

    def target(self, x, y):
        if self._zone(x, y) is not None or not getattr(self, "_items", None):
            return super().target(x, y)
        e, heart, card = self._hit_card(x, y)
        if e is None or heart is not None:
            return None
        return self.highlight.place(card)

    def tap(self, x, y):
        if self._zone(x, y) is not None or not getattr(self, "_items", None):
            super().tap(x, y)
            return
        e, heart, _ = self._hit_card(x, y)
        if heart is not None:
            on = self.app.state.toggle_favorite(e.slug)
            if self.favorites_only:
                self.app.show()
                return
            self.flat["key"] = self._key()  # the page has it already, once redrawn
            p = self.flat["pages"][self.page]
            p.canvas.heart(on, *heart)
            self.app.refresh()
        elif e is not None:
            self.app.push(ScrollDetail(self.app, e, list(self._items), self._tapped))


# -- the details --------------------------------------------------------------

def detail_band():
    """(top, height) of the part of the details screen that scrolls: from
    under Back to above the Install bar."""
    top = L.BACK_BTN[1] + L.BACK_BTN[3]
    return top, L.INSTALL_BTN[1] - 4 - top


MAX_DETAIL_H = 1200  # a page's tallest bitmap (a 551-character description is ~400)
VGLIDE_FRAMES = 10
VFLICK_S = 0.3  # a let-go glides on as far as it would go in this time


class DetailPage:
    """One firmware's details (DetailScreen.build's middle) as a Canvas, as
    tall as its whole description: a long one scrolls up and down in the
    band (ScrollDetail.vdrag)."""

    def __init__(self, app, n, entry):
        self.app = app
        self.n = n
        self.entry = entry
        self.canvas = None  # made by the first step, once the height is known
        self.tile = None
        self.work = self.steps()

    done, step, finish = Page.done, Page.step, Page.finish

    def grid(self):
        if self.tile is None:
            self.tile = displayio.TileGrid(
                self.canvas.bmp, pixel_shader=self.canvas.pal, y=self.canvas.top
            )
        return self.tile

    def max_scroll(self):
        """How far the page scrolls: its height past the band's."""
        return max(0, self.canvas.bmp.height - detail_band()[1]) if self.canvas else 0

    def _lines(self, desc, y):
        """The description as (left, y, text): beside the picture, then
        the full width under it. Returns (lines, the y after the last)."""
        W, x0 = L.W, L.DETAIL_X
        width_of = lambda s: ui.width(ui.BODY, s)  # noqa: E731
        out = []
        rest = desc
        while rest:
            left = x0 if y < L.PIC_BOTTOM else L.DESC_LEFT
            line = C.wrap(rest, width_of, W - left - 12)[0]
            if not line:  # a word wider than the line
                line = rest.split(" ")[0]
            rest = rest[len(line):].lstrip(" ")
            out.append((left, y, line))
            y += 18
        return out, y

    def steps(self):
        import json
        e, app = self.entry, self.app
        try:
            with open(app.path(e.slug, "meta.json")) as f:
                m = json.load(f)
        except (OSError, ValueError):
            m = {}
        pic, size = L.PIC
        px, py = L.PIC_AT
        author = m.get("author") or ""
        desc = C.plain(m.get("description") or "")
        # The description starts under the name, author, info and tags.
        lines, end = self._lines(desc, py + 28 + (22 if author else 0) + 20 + 30)
        top, h = detail_band()
        h = min(MAX_DETAIL_H, max(h, end - top + 6))
        self.canvas = cv = Canvas(L.W, top, h)
        cv.outlined(px - 1, py - 1, size + 2, size + 2, ui.THUMB_BG, ui.LINE, 1)
        cv.picture(app.path(e.slug, pic), px, py, size, e.version, 0)
        yield
        nbytes = m.get("bytes")
        info = "  ".join(s for s in (C.version_label(e.version), e.product,
                                     "%d KB" % (nbytes // 1024) if nbytes else "") if s)
        tags = [(g, ui.kind_color(g)) for g in e.genre.split(",") if g]
        if e.beta:
            tags.append(("beta", ui.WARN))
        if m.get("license"):
            tags.append((m["license"], ui.DIM))
        W = L.W
        x0 = L.DETAIL_X
        top = py
        tf = ui.title_font(e.name)
        name = C.ellipsize(e.name, lambda s: ui.width(tf, s), W - x0 - L.NAME_W_PAD)
        cv.text(tf, name, ui.FG, x0, top, (0, 0))
        y = top + 28
        if author:
            cv.text(
                ui.BODY,
                C.ellipsize("by " + author, lambda s: ui.width(ui.BODY, s), W - x0 - 12),
                ui.DIM,
                x0,
                y,
                (0, 0),
            )
            y += 22
        cv.text(ui.SMALL, info, ui.DIM, x0, y, (0, 0))
        y += 20
        tx = x0
        for label, color in tags:
            w = ui.width(ui.SMALL, label) + 14
            if tx + w > W - 8:
                break
            cv.outlined(tx, y, w, 20, ui.PANEL, ui.LINE, 3)
            cv.text(ui.SMALL, label, color, tx + w // 2, y + 10, (0.5, 0.5))
            tx += w + 6
        for left, ly, line in lines:
            cv.text(ui.BODY, line, ui.TEXT, left, ly, (0, 0))


class ScrollDetail(Scroller, S.DetailScreen):
    """DetailScreen that drags sideways to the previous or next firmware of
    the list it was opened from (its filters, its order), and up and down
    through a long description. Only Back goes back."""

    KEEP = S.DetailScreen.KEEP + ("order", "page", "flat", "scroll")

    def __init__(self, app, entry, order, pos):
        super().__init__(app, entry)
        self.order = order  # the list's index positions
        self.page = pos
        self.flat = {}
        self.dragging = False
        self.axis = "x"  # the drag under way: "x" (firmwares) or "y" (this one's text)
        self.scroll = 0  # how far this firmware's page is scrolled up

    @property
    def pages(self):
        return len(self.order)

    def release(self):
        self._empty_strip()
        super().release()

    def _scrolling(self):
        return True

    def _page(self, n, finish=True):
        p = self.flat.get(n)
        if p is None:
            p = self.flat[n] = DetailPage(self.app, n, self.app.index.entry(self.order[n]))
        return p.finish() if finish else p

    def _ready(self, n):
        self._attach_tile(self._page(n).grid(), n)

    def build(self):
        self.dragging = False
        e, app = self.entry, self.app
        for n in list(self.flat):
            if abs(n - self.page) > 1:
                del self.flat[n]
        W, H = L.W, L.H
        top, band = detail_band()
        g = displayio.Group()
        g.append(ui.rect(0, 0, W, H, ui.BG))
        self.strip = displayio.Group()
        cur = self._page(self.page)
        self.scroll = max(0, min(self.scroll, cur.max_scroll()))
        self._attach_tile(cur.grid(), self.page)
        cur.tile.y = top - self.scroll
        for n in self._neighbors():
            p = self.flat.get(n)
            if p is not None and p.done():
                self._attach_tile(p.grid(), n)
                p.tile.y = top
        g.append(self.strip)
        # A scrolled page passes under the header and the bar: they cover it.
        g.append(ui.rect(0, 0, W, top, ui.BG))
        g.append(ui.rect(0, top + band, W, H - top - band, ui.BG))
        self.thumb = self.bar_g = None  # the scroll bar, for a page that scrolls
        if cur.max_scroll():
            self.bar_g = displayio.Group()
            self.bar_g.append(ui.rect(W - 4, top + 2, 2, band - 4, ui.LINE))
            self.thumb = ui.rect(
                W - 4, top + 2, 2, max(12, (band - 4) * band // (band + cur.max_scroll())), ui.DIM
            )
            self.bar_g.append(self.thumb)
            g.append(self.bar_g)
            self._place_thumb()
        g.append(ui.rect(0, 0, W, 3, ui.kind_color(e.kind)))
        self.back_at = len(g)
        g.append(self.back_button().group)
        self.heart_rect = L.HEART_BTN
        g.append(ui.outlined(*L.HEART_BTN, ui.PANEL, ui.LINE))
        self.heart = ui.heart_tile(e.slug in app.state.favorites, *L.HEART_AT)
        g.append(self.heart)
        self.remove_button(g)
        self.bar_at = len(g)
        g.append(self.bottom_bar())
        self.group = g
        return g

    def tick(self, now):
        if self.dragging:
            return
        for n in self._neighbors():
            p = self._page(n, finish=False)
            if not p.done():
                if p.step():
                    self._attach_tile(p.grid(), n)
                    p.tile.y = detail_band()[0]
                return

    # -- sideways: the firmwares; up and down: this one's description ------------

    def drag(self, dx, x0, y0):
        if not self.dragging:
            self.axis = "x"
            if self.bar_g is not None:  # it's this firmware's, not the next one's
                self.bar_g.hidden = True
        Scroller.drag(self, dx, x0, y0)

    def vdrag(self, dy, _x0, _y0):
        p = self._page(self.page)
        most = p.max_scroll()
        if not most:
            return
        if not self.dragging:
            self.dragging = True
            self.axis = "y"
            self.hist = []
            self.scroll0 = self.scroll
        self.hist.append((time.monotonic(), dy))
        s = self.scroll0 - dy
        if s < 0:  # a rubber band past the ends
            s = s // 3
        elif s > most:
            s = most + (s - most) // 3
        self._set_scroll(s)
        self.app.refresh()

    def drop(self):
        if self.axis == "x":
            Scroller.drop(self)
            if self.bar_g is not None:
                self.bar_g.hidden = False
                self.app.refresh()
            return
        self.dragging = False
        hist = self.hist
        now = hist[-1][0] if hist else 0
        recent = [h for h in hist if now - h[0] <= 0.12] or hist[-2:]
        v = 0
        if len(recent) > 1:
            v = (recent[-1][1] - recent[0][1]) / max(0.001, recent[-1][0] - recent[0][0])
        most = self._page(self.page).max_scroll()
        start = self.scroll
        target = max(0, min(most, int(start - v * VFLICK_S)))
        for f in range(1, VGLIDE_FRAMES + 1):
            e = 1 - (1 - f / VGLIDE_FRAMES) ** 3
            self._set_scroll(int(start + (target - start) * e))
            self.app.refresh()

    def _set_scroll(self, s):
        self.scroll = s
        p = self.flat.get(self.page)
        if p is not None and p.tile is not None:
            p.tile.y = detail_band()[0] - s
        self._place_thumb()

    def _place_thumb(self):
        if self.thumb is None:
            return
        top, band = detail_band()
        most = self._page(self.page).max_scroll()
        room = band - 4 - self.thumb.height
        s = max(0, min(most, self.scroll))
        self.thumb.y = top + 2 + (room * s // most if most else 0)

    def _turned(self, d):
        self.scroll = 0
        self.page += d
        self.entry = self.app.index.entry(self.order[self.page])
        self.meta = None
        under = self.app.stack[-2] if len(self.app.stack) > 1 else None
        if isinstance(under, ScrollList):  # Back lands on this one's page
            under.page = self.page // under.per_page()
        self.app.show()


def list_screen(app):
    """The list as Settings > Scroll has it: ScrollList, or ListScreen."""
    return ScrollList(app) if app.state.scroll else S.ListScreen(app)
