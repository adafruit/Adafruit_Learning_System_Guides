# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""The flasher's screens: firmware list, details, confirm and install progress.

Each screen builds its displayio group when shown and lets it go when another
screen covers it, so only one screen's objects are in RAM. Screens get
taps and swipes from the App and redraw by changing their objects in place.
"""
# Disabled for the Learn Guides lint check: screens make their widgets in build(), each time
# they're shown; modules are imported where they're needed, to keep RAM free and start-up quick;
# methods kept on their class: the screen interface, or overridden; some drawing and protocol
# functions are long by nature.
# pylint: disable=attribute-defined-outside-init,import-outside-toplevel,no-self-use
# pylint: disable=too-many-branches,too-many-locals,too-many-statements
# pylint: disable=cyclic-import  # the cycles go through imports inside functions
import json
import time

import displayio

from fm1ui import catalog as C
from fm1ui import ui
from fm1ui.layout import L  # sizes and positions for this display

STOCK_PRODUCT = "FM-1_015"
FOOTER_SLACK = 20  # px: a footer tap this far off a button still counts


def wrapped(name, s, color, x, y, width, anchor=(0, 0), pitch=18, lines=2):
    """`s` on up to `lines` lines of at most `width` px, as a Group; the last
    line is ellipsized. Short text is a single ui.text, as before."""
    width_of = lambda t: ui.width(name, t)  # noqa: E731
    if width_of(s) <= width:
        return ui.text(name, s, color, x, y, anchor)
    parts = C.wrap(s, width_of, width)
    if len(parts) > lines:
        parts = parts[:lines - 1] + [C.ellipsize(" ".join(parts[lines - 1:]), width_of, width)]
    g = displayio.Group()
    for i, part in enumerate(parts):
        g.append(ui.text(name, part, color, x, y + i * pitch, anchor))
    return g


def _hit(rect, x, y, slack=0):
    """Is (x, y) in rect, or within `slack` px of it? Small targets get
    slack: a fingertip lands 10-15 px from where it's aimed."""
    rx, ry, rw, rh = rect
    return rx - slack <= x < rx + rw + slack and ry - slack <= y < ry + rh + slack


class Screen:
    # Attributes that outlive a build; release() drops every other one, so
    # the displayio objects a screen keeps handles on are freed with its group.
    KEEP = ("app", "group")

    def __init__(self, app):
        self.app = app
        self.group = None

    def build(self):
        raise NotImplementedError

    def release(self):
        self.group = None
        for k in list(self.__dict__):
            if k not in self.KEEP:
                # None first: MicroPython's dict leaves a deleted entry's
                # value in its table, where the GC still finds it, so a bare
                # delattr kept the whole screen alive (26 KB for the text list).
                setattr(self, k, None)
                delattr(self, k)

    def tap(self, x, y):
        pass

    def swipe(self, dx):
        pass

    def tick(self, now):
        pass

    def target(self, x, y):  # pylint: disable=unused-argument
        """The outlined group a touch at (x, y) would press, or None.
        Mirrors tap(): what lights up is what the tap will act on."""
        return None

    def fm1_changed(self):
        """The attached FM-1 (app.identity) changed."""


def tag_label(tag):
    """The filter button's text: "All", or the tag as the catalogue names it."""
    return tag[0].upper() + tag[1:] if tag else "All"


def fm1_status(app):
    """"FM-1: <what it runs>" for the connected FM-1."""
    slug = app.installed_slug()
    e = app.entry(slug) if slug else None
    return "FM-1: " + (C.display_name(e) if e else app.identity)


class ListScreen(Screen):
    """Six cards or 16 names a page, a tag filter, a favourites filter, a sort, and
    the FM-1 in the header."""

    KEEP = Screen.KEEP + ("page", "favorites_only", "tag")

    def __init__(self, app):
        super().__init__(app)
        self.page = 0
        self.favorites_only = False
        self.tag = None  # one of app.tags, or None for all
        self.cards = []  # (entry, card rect, heart rect, heart tile, card group)

    def items(self):
        """Index positions of the entries the filters show."""
        st = self.app.state
        return self.app.index.select(
            st.favorites if self.favorites_only else None, self.tag, st.sort
        )

    def per_page(self):
        return 2 * L.LIST_ROWS if self.app.state.view == "list" else L.COLS * L.ROWS

    def next_tag(self):
        """All -> each tag, most used first -> All."""
        tags = self.app.tags
        i = tags.index(self.tag) + 1 if self.tag in tags else 0
        return tags[i] if i < len(tags) else None

    def build(self):
        app = self.app
        items = self.items()
        per = self.per_page()
        pages = C.page_count(len(items), per)
        self.page = min(self.page, pages - 1)
        shown = [app.index.entry(i) for i in C.page_slice(items, self.page, per)]
        del items
        installed = app.installed_slug()

        W, H = L.W, L.H
        g = displayio.Group()
        g.append(ui.rect(0, 0, W, H, ui.BG))
        # header
        tag_color = ui.kind_color(self.tag) if self.tag else ui.CYAN
        self.tab_tag = ui.Button(tag_label(self.tag), *L.TAG_BTN, edge=tag_color,
                                 color=tag_color if self.tag else ui.FG)
        g.append(self.tab_tag.group)
        fx, fy = L.FAV_TAB[0], L.FAV_TAB[1]
        on = self.favorites_only
        self.tab_fav_g = ui.outlined(
            *L.FAV_TAB, ui.PANEL if on else ui.BG, ui.CYAN if on else ui.LINE
        )
        g.append(self.tab_fav_g)
        g.append(ui.heart_tile(True, fx + (L.FAV_TAB[2] - 13) // 2, fy + 7))
        self.tab_sort = ui.Button(C.SORT_LABELS.get(app.state.sort, "A-Z"), *L.SORT_BTN)
        g.append(self.tab_sort.group)
        self.fm1_at = len(g)
        g.append(self.fm1_header())

        # cards
        self.cards = []
        if not shown:
            if self.favorites_only and self.tag:
                empty = "No %s favourites." % tag_label(self.tag)
            elif self.favorites_only:
                empty = "No favourites yet. Tap the heart on a card to add one."
            elif self.tag:
                empty = "No %s firmware on the card." % tag_label(self.tag)
            else:
                empty = "No firmware found on the card."
            g.append(wrapped(ui.BODY, empty, ui.DIM, W // 2, L.EMPTY_Y, W - 24, (0.5, 0.5)))
        as_list = self.app.state.view == "list"
        for i, e in enumerate(shown):
            if as_list:
                x = L.GRID_X + (i // L.LIST_ROWS) * (L.ROW_W + L.GAP)
                g.append(
                    self.row(e, x, L.GRID_Y + (i % L.LIST_ROWS) * L.ROW_PITCH, e.slug == installed)
                )
            else:
                x = L.GRID_X + (i % L.COLS) * (L.CARD_W + L.GAP)
                y = L.GRID_Y + (i // L.COLS) * (L.CARD_H + L.GAP)
                g.append(self.card(e, x, y, e.slug == installed, i))

        # footer
        self.prev = L.PREV
        self.next = L.NEXT
        self.arrows = []  # outlined groups, or None when there's no page that way
        for (bx, by, bw, bh), left in ((self.prev, True), (self.next, False)):
            active = (self.page > 0) if left else (self.page < pages - 1)
            box = ui.outlined(bx, by, bw, bh, ui.PANEL if active else ui.BG, ui.LINE)
            self.arrows.append(box if active else None)
            g.append(box)
            g.append(
                ui.triangle(
                    bx + bw // 2 - 5, by + bh // 2 - 8, 10, 16, ui.CYAN if active else ui.LINE, left
                )
            )
        self.view_g = self.view_toggle(as_list)
        g.append(self.view_g)
        # The footer's buttons, left to right, as (rect, name, group or None).
        self.footer = [(self.prev, "prev", self.arrows[0]), (L.VIEW, "view", self.view_g)]
        if app.updater is not None:
            sx, sy, sw, sh = L.SETTINGS_BTN
            gear = ui.outlined(sx, sy, sw, sh, ui.PANEL, ui.LINE)
            gear.append(ui.gear(sx + sw // 2, sy + sh // 2, min(sw, sh) // 2 - 5, ui.FG, ui.PANEL))
            g.append(gear)
            self.footer.append((L.SETTINGS_BTN, "settings", gear))
        update = app.updater is not None
        if update:
            btn = ui.Button("Catalog", *L.UPDATE_BTN, name=ui.SMALL)
            g.append(btn.group)
            self.footer.append((L.UPDATE_BTN, "update", btn.group))
        lx, _, lw, _ = self.footer[-1][0]  # between the last left button and the next arrow
        px = (lx + lw + L.NEXT[0]) // 2
        page = ("%d/%d" if update else "Page %d of %d") % (self.page + 1, pages)
        g.append(ui.text(ui.SMALL, page, ui.FG, px, L.PAGE_Y, (0.5, 0.5)))
        self.footer.append((self.next, "next", self.arrows[1]))
        self.pages = pages
        self.group = g
        return g

    def fm1_header(self):
        """The header's right end: the connected FM-1, "Connecting...", or
        the Connect FM-1 button (outlined in amber after a failed try)."""
        app = self.app
        g = displayio.Group()
        self.connect_btn = None
        right, y = L.FM1_RIGHT, L.HEADER_Y
        if app.identity:
            room = right - (L.SORT_BTN[0] + L.SORT_BTN[2]) - 20  # the dot and a gap after the tabs
            status = C.ellipsize(fm1_status(app), lambda s: ui.width(ui.SMALL, s), room)
            g.append(ui.text(ui.SMALL, status, ui.FG, right, y, (1, 0.5)))
            g.append(ui.rect(right - ui.width(ui.SMALL, status) - 14, y - 4, 8, 8, ui.OK))
        elif app.connecting:
            g.append(ui.text(ui.SMALL, "Connecting...", ui.DIM, right, y, (1, 0.5)))
        else:
            self.connect_btn = ui.Button(
                "Connect FM-1", *L.CONNECT_BTN, edge=ui.WARN if app.connect_failed else ui.CYAN
            )
            g.append(self.connect_btn.group)
        return g

    def card(self, e, x, y, installed, slot):
        cw, ch, thumb = L.CARD_W, L.CARD_H, L.THUMB
        g = ui.outlined(x, y, cw, ch, ui.PANEL, ui.CYAN if installed else ui.LINE)
        if installed:  # a second line makes the outline read at a glance
            g.append(ui.panel(x + 1, y + 1, cw - 2, ch - 2, ui.CYAN, 3))
            g.append(ui.panel(x + 2, y + 2, cw - 4, ch - 4, ui.PANEL, 2))
        g.append(ui.rect(x + 4, y + 2, cw - 8, 3, ui.kind_color(e.kind)))
        tx, ty = x + (cw - thumb) // 2, y + L.CARD_THUMB_Y
        g.append(ui.thumbnail(self.app.path(e.slug, "thumb.bmp"), tx, ty, thumb, e.version, slot))
        if installed:
            bx, bw = x + 4, cw - 8  # across the card, not just the picture
            g.append(ui.rect(bx, ty + thumb - 12, bw, 12, ui.CYAN))
            g.append(
                ui.text(ui.SMALL, "INSTALLED", ui.BG, bx + bw // 2, ty + thumb - 6, (0.5, 0.5))
            )
        fav = e.slug in self.app.state.favorites
        tile = ui.heart_tile(fav, x + cw - 15, y + 10)
        g.append(tile)
        name = C.ellipsize(e.name, lambda s: ui.width(ui.NAME, s), cw - 8)
        g.append(ui.text(ui.NAME, name, ui.FG, x + cw // 2, y + L.CARD_NAME_Y, (0.5, 0)))
        vy = y + L.CARD_VERSION_Y
        version = C.ellipsize(
            e.version, lambda s: ui.width(ui.SMALL, s), cw - (50 if e.beta else 8)
        )
        if e.beta:
            vw, bw = ui.width(ui.SMALL, version + " "), ui.width(ui.SMALL, "beta")
            left = x + (cw - vw - bw) // 2
            g.append(ui.text(ui.SMALL, version, ui.DIM, left, vy, (0, 0)))
            g.append(ui.text(ui.SMALL, "beta", ui.WARN, left + vw, vy, (0, 0)))
        else:
            g.append(ui.text(ui.SMALL, version, ui.DIM, x + cw // 2, vy, (0.5, 0)))
        self.cards.append((e, (x, y, cw, ch), (x + cw - 28, y - L.GAP, 28 + L.GAP, 50), tile, g))
        return g

    def row(self, e, x, y, installed):
        """One firmware as its name and heart, with the tag's colour stripe."""
        rw, rh = L.ROW_W, L.ROW_H
        g = ui.outlined(x, y, rw, rh, ui.PANEL, ui.CYAN if installed else ui.LINE)
        g.append(ui.rect(x + 5, y + 6, 3, rh - 12, ui.kind_color(e.kind)))
        name = C.ellipsize(e.name, lambda s: ui.width(ui.NAME, s), rw - 50)
        g.append(
            ui.text(ui.NAME, name, ui.CYAN if installed else ui.FG, x + 16, y + rh // 2, (0, 0.5))
        )
        fav = e.slug in self.app.state.favorites
        tile = ui.heart_tile(fav, x + rw - 22, y + L.ROW_HEART_DY)
        g.append(tile)
        self.cards.append((e, (x, y, rw, rh), (x + rw - 40, y - 1, 46, rh + 2), tile, g))
        return g

    def view_toggle(self, as_list):
        """One button showing the current view, pictures or text; a tap
        anywhere on it switches to the other."""
        x, y, w, h = L.VIEW
        dy = L.VIEW_ICON_DY
        g = ui.outlined(x, y, w, h, ui.PANEL, ui.LINE)
        if as_list:
            for i in range(3):  # three lines of text
                g.append(ui.rect(x + (w - 20) // 2, y + dy + i * 5, 20, 2, ui.CYAN))
        else:
            for i in range(6):  # a 3x2 grid of small squares
                g.append(
                    ui.rect(x + (w - 22) // 2 + (i % 3) * 8, y + dy + (i // 3) * 7, 6, 5, ui.CYAN)
                )
        return g

    def set_view(self, view):
        if view != self.app.state.view:
            first = self.page * self.per_page()
            self.app.state.view = view
            self.app.state.save()
            self.page = first // self.per_page()  # keep the top entry on screen
            self.app.show()

    def next_sort(self):
        """A-Z -> New -> RcntUp -> A-Z, from the first page."""
        st = self.app.state
        st.sort = C.next_sort(st.sort)
        st.save()
        self.page = 0
        self.app.show()

    def turn(self, delta):
        page = self.page + delta
        if 0 <= page < self.pages:
            self.page = page
            self.app.show()

    def _tab_at(self, x):
        """"tag", "fav" or "sort": the tabs take the header's full height
        (taps there land high) and split at the gaps between them."""
        if x < (L.TAG_BTN[0] + L.TAG_BTN[2] + L.FAV_TAB[0]) // 2:
            return "tag"
        if x < (L.FAV_TAB[0] + L.FAV_TAB[2] + L.SORT_BTN[0]) // 2:
            return "fav"
        return "sort"

    def _footer_at(self, x):
        """The footer button nearest x, within FOOTER_SLACK: a fingertip
        lands off a small button, and the buttons split the gaps between
        them. (rect, name, group), or None."""
        best, far = None, FOOTER_SLACK + 1
        for item in self.footer:
            bx, _, bw, _ = item[0]
            d = bx - x if x < bx else x - (bx + bw - 1) if x >= bx + bw else 0
            if d < far:
                best, far = item, d
        return best

    def _zone(self, x, y):
        """"connect", "tabs", a footer button's name ("prev", "view",
        "settings", "update", "next") or None."""
        if y < L.GRID_Y - 2:
            if x >= L.CONNECT_ZONE_X:
                return "connect"
            if L.TABS_ZONE[0] <= x < L.TABS_ZONE[1]:
                return "tabs"
        elif y >= self.prev[1] - 8:
            item = self._footer_at(x)
            return item[1] if item else None
        return None

    def target(self, x, y):
        zone = self._zone(x, y)
        if zone == "connect":
            return self.connect_btn.group if self.connect_btn else None
        if zone == "tabs":
            tab = self._tab_at(x)
            return (
                self.tab_tag.group
                if tab == "tag"
                else self.tab_fav_g if tab == "fav" else self.tab_sort.group
            )
        if zone is not None:  # a footer button; None for an arrow with no page that way
            return self._footer_at(x)[2]
        for _e, card, heart, _tile, g in self.cards:
            if _hit(heart, x, y):
                return None  # the heart's own toggle is the feedback
            if _hit(card, x, y):
                return g
        return None

    def tap(self, x, y):
        zone = self._zone(x, y)
        if zone == "connect":
            self.app.connect()  # connected: ask again, e.g. after a manual install
        elif zone == "tabs":
            tab = self._tab_at(x)
            if tab == "sort":
                self.next_sort()
                return
            if tab == "fav":
                self.favorites_only = not self.favorites_only
            else:
                self.tag = self.next_tag()
            self.page = 0
            self.app.show()
        elif zone == "prev":
            self.turn(-1)
        elif zone == "view":
            self.set_view("grid" if self.app.state.view == "list" else "list")
        elif zone == "next":
            self.turn(1)
        elif zone == "update":
            from fm1ui.update import UpdateScreen
            self.app.push(UpdateScreen(self.app))
        elif zone == "settings":
            from fm1ui.settings import SettingsScreen
            self.app.push(SettingsScreen(self.app))
        else:
            e, tile = self._card_at(x, y)
            if tile is not None:
                ui.set_heart(tile, self.app.state.toggle_favorite(e.slug))
                del tile
                if self.favorites_only:
                    self.app.show()
                else:
                    self.app.refresh()
            elif e is not None:
                self.app.push(DetailScreen(self.app, e))

    def _card_at(self, x, y):
        """(entry, heart tile) for a touch on a heart, (entry, None) for one
        elsewhere on a card or row, else (None, None). A helper so no loop
        over self.cards is running when the next screen is built: the loop
        keeps every card's group alive, and 16 rows' worth ran the detail
        screen out of memory."""
        for e, card, heart, tile, _ in self.cards:
            if _hit(heart, x, y):
                return e, tile
            if _hit(card, x, y):
                return e, None
        return None, None

    def swipe(self, dx):
        self.turn(1 if dx < 0 else -1)

    def fm1_changed(self):
        if self.app.connecting:  # just the header, quickly, before the wait
            self.group[self.fm1_at] = self.fm1_header()
            self.app.refresh()
        else:  # the INSTALLED card may change too
            self.app.show()


class DetailScreen(Screen):
    """The picture, name, author, version, tags and description, with Back,
    a favourite toggle and Install (Connect FM-1 until one is connected)."""

    KEEP = Screen.KEEP + ("entry", "meta")

    def __init__(self, app, entry):
        super().__init__(app)
        self.entry = entry
        self.meta = None

    def build(self):
        e, app = self.entry, self.app
        if self.meta is None:
            try:
                with open(app.path(e.slug, "meta.json")) as f:
                    self.meta = json.load(f)
            except (OSError, ValueError):
                self.meta = {}
        m = self.meta
        author = m.get("author") or ""
        desc = C.plain(m.get("description") or "")
        size = m.get("bytes")
        info = "  ".join(s for s in (C.version_label(e.version), e.product,
                                     "%d KB" % (size // 1024) if size else "") if s)
        tags = [(g, ui.kind_color(g)) for g in e.genre.split(",") if g]
        if e.beta:
            tags.append(("beta", ui.WARN))
        if m.get("license"):
            tags.append((m["license"], ui.DIM))
        W, H = L.W, L.H
        x0 = L.DETAIL_X
        top = L.PIC_AT[1]
        # The description's lines are the screen's largest text bitmaps (up
        # to 1 KB each), so they're made first, while the heap still has the
        # big gaps the list screen left.
        y = top + 28 + (22 if author else 0) + 20 + 30
        lines = []
        rest = desc
        width_of = lambda s: ui.width(ui.BODY, s)  # noqa: E731
        bottom, left_full = L.DESC_BOTTOM, L.DESC_LEFT
        while rest and y + 16 <= bottom:
            left = x0 if y < L.PIC_BOTTOM else left_full
            line = C.wrap(rest, width_of, W - left - 12)[0]
            rest = rest[len(line):].lstrip(" ")
            if rest and y + 34 > bottom:  # last line that fits
                line = C.ellipsize(
                    line + " " + rest, width_of, W - left - 12 if left == x0 else L.DESC_LAST_W
                )
                rest = ""
            lines.append(ui.text(ui.BODY, line, ui.TEXT, left, y, (0, 0)))
            y += 18
        del rest

        g = displayio.Group()
        g.append(ui.rect(0, 0, W, H, ui.BG))
        g.append(ui.rect(0, 0, W, 3, ui.kind_color(e.kind)))
        self.back_at = len(g)
        g.append(self.back_button().group)
        self.heart_rect = L.HEART_BTN
        g.append(ui.outlined(*L.HEART_BTN, ui.PANEL, ui.LINE))  # the heart's toggle is its feedback
        self.heart = ui.heart_tile(e.slug in app.state.favorites, *L.HEART_AT)
        g.append(self.heart)
        self.remove_button(g)

        pic, size = L.PIC
        px, py = L.PIC_AT
        g.append(ui.outlined(px - 1, py - 1, size + 2, size + 2, ui.THUMB_BG, ui.LINE, 1))
        g.append(ui.thumbnail(app.path(e.slug, pic), px, py, size, e.version))

        tf = ui.title_font(e.name)
        name = C.ellipsize(e.name, lambda s: ui.width(tf, s), W - x0 - L.NAME_W_PAD)
        g.append(ui.text(tf, name, ui.FG, x0, top, (0, 0)))
        y = top + 28
        if author:
            g.append(
                ui.text(
                    ui.BODY,
                    C.ellipsize("by " + author, lambda s: ui.width(ui.BODY, s), W - x0 - 12),
                    ui.DIM,
                    x0,
                    y,
                    (0, 0),
                )
            )
            y += 22
        g.append(ui.text(ui.SMALL, info, ui.DIM, x0, y, (0, 0)))
        y += 20
        tx = x0
        for label, color in tags:
            w = ui.width(ui.SMALL, label) + 14
            if tx + w > L.W - 8:
                break
            g.append(ui.outlined(tx, y, w, 20, ui.PANEL, ui.LINE, 3))
            g.append(ui.text(ui.SMALL, label, color, tx + w // 2, y + 10, (0.5, 0.5)))
            tx += w + 6
        y += 30

        for line in lines:
            g.append(line)

        self.bar_at = len(g)
        g.append(self.bottom_bar())
        self.group = g
        return g

    def remove_button(self, g):
        """Remove, on boards that can rewrite the card's list (the Metro);
        never for M-VAVE V15, the way back to the factory firmware."""
        self.remove_btn = None
        if self.app.updater is not None and self.entry.product != STOCK_PRODUCT:
            self.remove_btn = ui.Button("Remove", *L.REMOVE_BTN, edge=ui.WARN, color=ui.WARN)
            g.append(self.remove_btn.group)

    def installed_here(self):
        """Is the connected FM-1 running this firmware?"""
        return bool(self.app.identity) and self.app.installed_slug() == self.entry.slug

    def back_button(self):
        """Back, outlined in cyan when this firmware is the one on the FM-1
        (after an install it's the way on, not Install again)."""
        self.back = ui.Button(
            "Back", *L.BACK_BTN, edge=ui.CYAN if self.installed_here() else ui.LINE
        )
        return self.back

    def bottom_bar(self):
        """The bottom line: what's connected, and Install or Connect FM-1.
        Install again, for the firmware the FM-1 runs, is a plain button."""
        app = self.app
        g = displayio.Group()
        installed = self.installed_here()
        if app.identity:
            label, ready = ("Install again" if installed else "Install"), True
            note, color = (
                ("Installed on this FM-1", ui.CYAN) if installed else (fm1_status(app), ui.DIM)
            )
        elif app.connecting:
            label, ready = "Connect FM-1", False
            note, color = "Connecting...", ui.DIM
        else:
            label, ready = "Connect FM-1", True
            note, color = (
                ("No FM-1 answered. Is it on and plugged in?", ui.WARN)
                if app.connect_failed
                else ("Connect the FM-1 to install.", ui.DIM)
            )
        if installed:
            self.install = ui.Button(label, *L.INSTALL_BTN)
        else:
            self.install = ui.Button(
                label,
                *L.INSTALL_BTN,
                fill=ui.CYAN if ready else ui.BG,
                edge=ui.CYAN if ready else ui.LINE,
                color=ui.BG if ready else ui.LINE
            )
        g.append(self.install.group)
        nx, ny = L.NOTE_AT
        g.append(wrapped(ui.SMALL, note, color, nx, ny - 7, L.NOTE_W, (0, 0.5), pitch=14))
        return g

    def target(self, x, y):
        if self.back.hit(x, y):
            return self.back.group
        if self.remove_btn is not None and self.remove_btn.hit(x, y, 4):
            return self.remove_btn.group
        if _hit(self.heart_rect, x, y, 14):
            return None
        if self.install.hit(x, y) and not self.app.connecting:
            return self.install.group
        return None

    def tap(self, x, y):
        if self.back.hit(x, y):
            self.app.pop()
        elif self.remove_btn is not None and self.remove_btn.hit(x, y, 4):
            self.app.push(RemoveScreen(self.app, self.entry))
        elif _hit(self.heart_rect, x, y, 14):
            ui.set_heart(self.heart, self.app.state.toggle_favorite(self.entry.slug))
            self.app.refresh()
        elif self.install.hit(x, y):
            if self.app.identity:
                self.app.push(ConfirmScreen(self.app, self.entry))
            else:
                self.app.connect()

    def fm1_changed(self):
        self.group[self.back_at] = self.back_button().group
        self.group[self.bar_at] = self.bottom_bar()
        self.app.refresh()

    def swipe(self, dx):
        if dx > 0:
            self.app.pop()


class ConfirmScreen(Screen):
    """Install X over what the FM-1 is running? Reached with an FM-1 connected;
    goes back to the details if it's unplugged."""

    KEEP = Screen.KEEP + ("entry",)

    def __init__(self, app, entry):
        super().__init__(app)
        self.entry = entry

    def message(self):
        """(ready, text, warning or None)."""
        app, e = self.app, self.entry
        ident = app.identity
        if not ident:
            return False, "The FM-1 is no longer connected. Go back and tap Connect FM-1.", None
        current = app.installed_slug()
        cur = app.entry(current) if current else None
        running = C.display_name(cur) if cur else ident
        if current == e.slug:
            text = "%s is already on the FM-1. Install it again?" % e.name
        elif e.product == STOCK_PRODUCT:
            text = ("This puts back M-VAVE's official firmware and its factory voices, "
                    "replacing %s." % running)
        elif ident == STOCK_PRODUCT:
            text = ("The FM-1 runs M-VAVE's official V15. %s replaces it. To go back, install "
                    "M-VAVE V15 from the list at any time." % e.name)
        else:
            text = "%s replaces %s on the FM-1." % (e.name, running)
        from fm1ui import heads
        warning = None if current == e.slug else heads.advice(app, e)
        if warning:  # the room goes to the warning
            return True, text, warning
        return True, text + " Keep the FM-1 on and connected; it takes one to two minutes.", None

    def build(self):
        e = self.entry
        ready, msg, warning = self.message()
        self.ready = ready
        title = "Install %s?" % e.name
        width_of = lambda s: ui.width(ui.BODY, s)  # noqa: E731
        g = displayio.Group()
        g.append(ui.rect(0, 0, L.W, L.H, ui.BG))
        px, py, pw, ph = L.CONFIRM_PANEL
        g.append(ui.outlined(px, py, pw, ph, ui.PANEL, ui.LINE))
        g.append(ui.rect(px + 4, py + 2, pw - 8, 3, ui.kind_color(e.kind)))
        tf = ui.title_font(title)
        tx, ty = L.CONFIRM_TITLE_AT
        g.append(
            ui.text(
                tf,
                C.ellipsize(title, lambda s: ui.width(tf, s), L.CONFIRM_W),
                ui.FG,
                tx,
                ty,
                (0, 0),
            )
        )
        y = L.CONFIRM_TEXT_Y
        lines = [(line, ui.TEXT) for line in C.wrap(msg, width_of, L.CONFIRM_W)]
        if warning:
            lines += [(line, ui.WARN) for line in C.wrap(warning, width_of, L.CONFIRM_W)]
        for line, color in lines[:L.CONFIRM_LINES]:
            g.append(ui.text(ui.BODY, line, color, tx, y, (0, 0)))
            y += 19
        self.cancel = ui.Button("Cancel", *L.CANCEL_BTN)
        self.go = ui.Button("Install", *L.GO_BTN, fill=ui.CYAN if ready else ui.BG,
                            edge=ui.CYAN if ready else ui.LINE, color=ui.BG if ready else ui.LINE)
        g.append(self.cancel.group)
        g.append(self.go.group)
        self.group = g
        return g

    def target(self, x, y):
        if self.cancel.hit(x, y):
            return self.cancel.group
        if self.go.hit(x, y) and self.ready:
            return self.go.group
        return None

    def tap(self, x, y):
        if self.cancel.hit(x, y):
            self.app.pop()
        elif self.go.hit(x, y) and self.ready:
            self.app.start_install(self.entry)

    def fm1_changed(self):
        if self.app.identity:
            self.app.show()
        else:  # unplugged: back to the details, which offer Connect FM-1
            self.app.pop()


class RemoveScreen(Screen):
    """Remove X from the card? From Remove on the details (the Metro). Yes
    deletes its folder and goes back to the list; updates then leave it
    unticked, so it stays gone until it's ticked in Update > Details."""

    KEEP = Screen.KEEP + ("entry", "error")

    def __init__(self, app, entry):
        super().__init__(app)
        self.entry = entry
        self.error = None

    def build(self):
        e = self.entry
        title = "Remove %s?" % e.name
        if self.error:
            msg, color = self.error, ui.WARN
        else:
            msg, color = ("Deletes %s from the SD card: its package and pictures. Update firmwares "
                          "leaves it out, unless you tick it in Details." % e.name), ui.TEXT
        width_of = lambda s: ui.width(ui.BODY, s)  # noqa: E731
        g = displayio.Group()
        g.append(ui.rect(0, 0, L.W, L.H, ui.BG))
        px, py, pw, ph = L.CONFIRM_PANEL
        g.append(ui.outlined(px, py, pw, ph, ui.PANEL, ui.LINE))
        g.append(ui.rect(px + 4, py + 2, pw - 8, 3, ui.WARN))
        tf = ui.title_font(title)
        tx, ty = L.CONFIRM_TITLE_AT
        g.append(
            ui.text(
                tf,
                C.ellipsize(title, lambda s: ui.width(tf, s), L.CONFIRM_W),
                ui.FG,
                tx,
                ty,
                (0, 0),
            )
        )
        y = L.CONFIRM_TEXT_Y
        for line in C.wrap(msg, width_of, L.CONFIRM_W)[:L.CONFIRM_LINES]:
            g.append(ui.text(ui.BODY, line, color, tx, y, (0, 0)))
            y += 19
        self.cancel = ui.Button("Cancel" if not self.error else "Back", *L.CANCEL_BTN)
        self.go = ui.Button("Remove", *L.GO_BTN, fill=ui.WARN, edge=ui.WARN, color=ui.BG)
        self.go.group.hidden = bool(self.error)
        g.append(self.cancel.group)
        g.append(self.go.group)
        self.group = g
        return g

    def target(self, x, y):
        if self.cancel.hit(x, y):
            return self.cancel.group
        if self.go.hit(x, y) and not self.error:
            return self.go.group
        return None

    def tap(self, x, y):
        if self.cancel.hit(x, y):
            self.app.pop()
        elif self.go.hit(x, y) and not self.error:
            self.remove()

    def remove(self):
        import fm1catalog as K
        app, slug = self.app, self.entry.slug
        try:
            K.remove(app.root, slug)
        except OSError as e:
            print("remove %s: %r" % (slug, e))
            self.error = "Couldn't remove it from the card (%s)." % (str(e) or repr(e))
        st = app.state
        if self.error is None or not K.exists(app.root + "/" + slug + "/meta.json"):
            st.removed.add(slug)
            st.favorites.discard(slug)
            st.save()
        app.reload_index()
        if self.error:
            app.show()
        else:
            app.home()


class ProgressScreen(Screen):
    """Install progress: the phase, a bar, elapsed time and hints. The
    installer drives it through phase(), wait() and finish()."""

    KEEP = Screen.KEEP + ("entry", "t0", "waiting_since", "done", "last_draw")
    LONG_WAIT_S = 20

    def __init__(self, app, entry):
        super().__init__(app)
        self.entry = entry
        self.t0 = time.monotonic()
        self.waiting_since = None
        self.done = None
        self.last_draw = 0

    def build(self):
        e = self.entry
        W, H = L.W, L.H
        g = displayio.Group()
        g.append(ui.rect(0, 0, W, H, ui.BG))
        g.append(ui.rect(0, 0, W, 3, ui.kind_color(e.kind)))
        tf = ui.title_font(e.name)
        self.title = ui.text(tf, self._fit(tf, "Installing %s" % e.name, L.PROGRESS_TITLE_W),
                             ui.FG, W // 2, L.PROGRESS_TITLE_Y, (0.5, 0))
        g.append(self.title)
        self.sub = ui.text(
            ui.BODY, "Keep the FM-1 on and connected.", ui.DIM, W // 2, L.PROGRESS_SUB_Y, (0.5, 0)
        )
        g.append(self.sub)
        bx, by, bw, bh = L.BAR
        self.phase_label = ui.text(ui.NAME, "Preparing", ui.FG, bx, by - 10, (0, 1))
        g.append(self.phase_label)
        self.pct = ui.text(ui.NAME, "", ui.FG, bx + bw, by - 10, (1, 1))
        g.append(self.pct)
        g.append(ui.outlined(bx, by, bw, bh, ui.PANEL, ui.LINE))
        self.fill = ui.rect(bx + 3, by + 3, 1, bh - 6, ui.CYAN)
        self.fill_group = displayio.Group()  # shapes can't hide themselves; groups can
        self.fill_group.append(self.fill)
        self.fill_group.hidden = True
        g.append(self.fill_group)
        self.elapsed = ui.text(ui.SMALL, "Elapsed 0:00", ui.DIM, bx, by + bh + 14, (0, 0.5))
        g.append(self.elapsed)
        # The note is two lines (the second blank unless it wraps), so a long
        # hint fits a narrow screen.
        self.note = ui.text(ui.BODY, " ", ui.WARN, W // 2, L.PROGRESS_NOTE_Y, (0.5, 0.5))
        self.note2 = ui.text(ui.BODY, " ", ui.WARN, W // 2, L.PROGRESS_NOTE_Y + 18, (0.5, 0.5))
        g.append(self.note)
        g.append(self.note2)
        self.ok = ui.Button("OK", *L.OK_BTN, fill=ui.CYAN, edge=ui.CYAN, color=ui.BG)
        self.ok.group.hidden = True
        g.append(self.ok.group)
        self.group = g
        return g

    @staticmethod
    def _fit(font, s, width):
        return C.ellipsize(s, lambda t: ui.width(font, t), width)

    def _note(self, s, color=None):
        """The note, on two lines if it's wider than the screen."""
        width_of = lambda t: ui.width(ui.BODY, t)  # noqa: E731
        parts = C.wrap(s, width_of, L.W - 24) if width_of(s) > L.W - 24 else [s]
        for label, part in ((self.note, parts[0]), (self.note2, " ".join(parts[1:]) or " ")):
            if color is not None:
                label.color = color
            label.set(part)

    def _bar(self, pct, color=None):
        bw = L.BAR[2]
        w = max(1, (bw - 6) * pct // 100)
        self.fill.width = w
        if color is not None:
            self.fill.pixel_shader = ui.palette(color)
        self.fill_group.hidden = pct <= 0

    def _clock(self, now):
        s = int(now - self.t0)
        self.elapsed.set("Elapsed %d:%02d" % (s // 60, s % 60))

    def phase(self, name, pct):
        """Installer status callback."""
        if self.waiting_since is not None:
            self.waiting_since = None
            self._note(" ")
        self.phase_label.set(name)
        self.pct.set("%d%%" % pct)
        self._bar(pct)
        self.redraw()

    def wait(self, _what, note="Waiting for the FM-1 to restart..."):
        """The installer is waiting for the FM-1 to come back."""
        self.waiting_since = time.monotonic()
        self._note(note, ui.WARN)
        self.redraw(force=True)

    def found(self):
        if self.waiting_since is not None:
            self.waiting_since = None
            self._note(" ")
            self.redraw(force=True)

    def tick(self, now):
        if self.done is not None:
            return
        if self.waiting_since is not None and now - self.waiting_since > self.LONG_WAIT_S:
            self._note("If it doesn't come back, turn the FM-1 off and on again.")
        self.redraw()

    def redraw(self, force=False):
        now = time.monotonic()
        if force or now - self.last_draw >= 1:
            self._clock(now)
            self.last_draw = now
            self.app.refresh()

    def finish(self, ok, message=""):
        self.done = ok
        self._clock(time.monotonic())
        if ok:
            self.title.set("Installed %s" % self.entry.name)
            self.title.color = ui.OK
            self.phase_label.set("Done")
            self.pct.set("100%")
            self._bar(100, ui.OK)
            self.sub.set(" ")
            self._note(message or " ", ui.DIM)
        else:
            self.title.set("Install failed")
            self.title.color = ui.BAD
            self.sub.set(self._fit(ui.BODY, message[:60], L.W - 24) if message else " ")
            self._bar(max(1, self.fill.width * 100 // (L.BAR[2] - 6)), ui.BAD)
            self._note("Power-cycle the FM-1; the firmware it had still boots.", ui.WARN)
        self.ok.group.hidden = False
        self.app.refresh()

    def target(self, x, y):
        if self.done is not None and self.ok.hit(x, y):
            return self.ok.group
        return None

    def tap(self, x, y):
        if self.done is not None and self.ok.hit(x, y):
            self.app.finish_install()
