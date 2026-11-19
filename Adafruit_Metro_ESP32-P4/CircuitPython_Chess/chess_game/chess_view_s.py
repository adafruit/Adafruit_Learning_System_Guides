# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=attribute-defined-outside-init, too-many-branches, too-many-locals
# pylint: disable=too-many-return-statements, too-many-statements
"""Chess screen for the 2.8" shield (320x240): board on the left, panel on the right.

The board is 240x240 (30 px squares). The 80 px panel holds the header (game
type, level), two status lines, points, eval and its bar, the hint, and the
HINT / UNDO / NEW buttons. While the engine thinks, NEW becomes MOVE NOW and a
thin bar shows the thinking time. The 2x2 promotion picker covers the points
and hint; the menu, new-game dialog and online dialog cover the whole screen.

Has the same interface as chess_view.View.
"""

import displayio

import chess_ctrl as cc
from chess_gfx import CENTER, RIGHT, Font, Text, rect, split_line
from chess_view import (
    ACCENT,
    BAD,
    BLACK_PIECE,
    BUTTON,
    BUTTON_OFF,
    BUTTON_TEXT,
    DARK,
    GOOD,
    LIGHT,
    LINE,
    MUTED,
    PANEL_BG,
    PANEL_HEADER,
    TEXT,
    WHITE_PIECE,
    Board,
)

W, H = 320, 240
SQ = 30
BOARD_PX = 8 * SQ
PANEL_X = BOARD_PX
PANEL_W = W - BOARD_PX
M = 4  # panel margin
CW = PANEL_W - 2 * M  # panel content width (72)
COLOURS = {"good": GOOD, "bad": BAD, "accent": ACCENT, "text": TEXT, "muted": MUTED}

# panel layout (panel coordinates)
HEADER_H = 20
STATUS1_Y = 22
STATUS2_Y = 37
PROGRESS_Y = 51  # thinking bar, drawn over the first separator line
SEP1_Y = 52
POINTS_Y = 55
SEP2_Y = 130
HINT_Y = 133
BTN_Y0 = 164
BTN_H = 22
BTN_GAP = 3
BUTTONS = (("hint", "HINT"), ("undo", "UNDO"), ("new", "NEW"))

PROMO_PIECES = "qrbn"
PROMO_Y0 = POINTS_Y + 23
PROMO_CELL = 35

LEVEL_WORDS = (
    (5, "beginner"),
    (10, "casual"),
    (15, "club player"),
    (20, "strong"),
    (99, "full strength"),
)


def level_words(level):
    for limit, words in LEVEL_WORDS:
        if level < limit:
            return words
    return ""


class ShieldView:
    def __init__(self, asset_dir):
        a = asset_dir + "/"
        self.font_small = Font(a + "font_small.bin")
        self.font_bold = Font(a + "font_bold.bin")
        self.font_med = Font(a + "font_med.bin")
        self.font_big = Font(a + "font_big.bin")
        self.root = displayio.Group()
        self.board = Board(a, SQ)
        self.root.append(self.board.group)
        self._build_panel()
        self._build_promotion()
        self._build_dialog()
        self._build_menu()
        self._build_online()
        self.version = -1
        self.flash_id = None
        self.stop_shown = None

    # ------------------------------------------------------------ panel

    def _build_panel(self):
        panel = displayio.Group(x=PANEL_X)
        self.root.append(panel)
        self.panel = panel
        fs, fb, fm = self.font_small, self.font_bold, self.font_med
        panel.append(rect(PANEL_BG, 0, 0, PANEL_W, H)[0])
        panel.append(rect(PANEL_HEADER, 0, 0, PANEL_W, HEADER_H)[0])
        hy = (HEADER_H - fs.height) // 2
        self.title_text = Text(fs, 56, 3, hy, TEXT, PANEL_HEADER, cc.ENGINE_NAME)
        panel.append(self.title_text.tile)
        self.level_text = Text(
            fb,
            20,
            PANEL_W - 3 - 20,
            (HEADER_H - fb.height) // 2,
            ACCENT,
            PANEL_HEADER,
            "",
            align=RIGHT,
        )
        panel.append(self.level_text.tile)

        self.status1 = Text(fb, CW, M, STATUS1_Y, GOOD, PANEL_BG)
        self.status2 = Text(fs, CW, M, STATUS2_Y, TEXT, PANEL_BG)
        panel.append(self.status1.tile)
        panel.append(self.status2.tile)
        panel.append(rect(LINE, M, SEP1_Y, CW, 1)[0])
        panel.append(rect(LINE, M, SEP2_Y, CW, 1)[0])

        # points, material balance and eval (hidden while promoting)
        info = displayio.Group()
        self.info = info
        panel.append(info)
        y = POINTS_Y
        info.append(Text(fs, CW, M, y, MUTED, PANEL_BG, "Points").tile)
        y += 13
        info.append(rect(WHITE_PIECE, M, y + 4, 8, 8)[0])
        self.white_pts = Text(fs, 26, M + 11, y, TEXT, PANEL_BG)
        info.append(self.white_pts.tile)
        info.append(rect(MUTED, M + 38, y + 4, 8, 8)[0])
        info.append(rect(BLACK_PIECE, M + 39, y + 5, 6, 6)[0])
        self.black_pts = Text(fs, CW - 49, M + 49, y, TEXT, PANEL_BG)
        info.append(self.black_pts.tile)
        y += 15
        self.balance = Text(fb, CW, M, y, TEXT, PANEL_BG)
        info.append(self.balance.tile)
        y += 17
        info.append(Text(fs, 30, M, y, MUTED, PANEL_BG, "Eval").tile)
        self.eval_text = Text(fs, CW - 30, M + 30, y, TEXT, PANEL_BG, "", align=RIGHT)
        info.append(self.eval_text.tile)
        y += 16
        info.append(rect(MUTED, M, y, CW, 9)[0])
        self.eval_w = CW - 2
        self.eval_white, _ = rect(WHITE_PIECE, M + 1, y + 1, self.eval_w // 2, 7)
        self.eval_black, _ = rect(
            BLACK_PIECE,
            M + 1 + self.eval_w // 2,
            y + 1,
            self.eval_w - self.eval_w // 2,
            7,
        )
        info.append(self.eval_white)
        info.append(self.eval_black)
        self.eval_px = self.eval_w // 2

        info.append(Text(fs, CW, M, HINT_Y, MUTED, PANEL_BG, "Hint").tile)
        self.hint_text = Text(fm, CW, M, HINT_Y + 12, GOOD, PANEL_BG)
        info.append(self.hint_text.tile)

        # engine thinking-time bar
        self.progress = displayio.Group()
        self.progress.append(rect(LINE, M, PROGRESS_Y, CW, 3)[0])
        self.progress_bar, _ = rect(ACCENT, M, PROGRESS_Y, 1, 3)
        self.progress.append(self.progress_bar)
        self.progress.hidden = True
        self.progress_px = 1
        panel.append(self.progress)

        self.buttons = {}
        for i, (bid, label) in enumerate(BUTTONS):
            t = Text(
                fb,
                CW,
                M,
                BTN_Y0 + i * (BTN_H + BTN_GAP),
                BUTTON_TEXT,
                BUTTON,
                label,
                align=CENTER,
                height=BTN_H,
            )
            self.buttons[bid] = t
            panel.append(t.tile)

    def _build_promotion(self):
        g = displayio.Group(x=PANEL_X)
        g.hidden = True
        g.append(rect(PANEL_BG, 0, SEP1_Y + 1, PANEL_W, BTN_Y0 - 2 - SEP1_Y - 1)[0])
        g.append(
            Text(
                self.font_bold, CW, M, POINTS_Y + 2, ACCENT, PANEL_BG, "Promote to:"
            ).tile
        )
        b = self.board
        self.promo_cells = []
        for i in range(4):
            x = M + 1 + (i % 2) * PROMO_CELL
            y = PROMO_Y0 + (i // 2) * PROMO_CELL
            g.append(
                rect(DARK if i & 1 else LIGHT, x, y, PROMO_CELL - 2, PROMO_CELL - 2)[0]
            )
            off = (PROMO_CELL - 2 - SQ) // 2
            tg = displayio.TileGrid(
                b.piece_sheet,
                pixel_shader=b.piece_palette,
                tile_width=SQ,
                tile_height=SQ,
                x=x + off,
                y=y + off,
            )
            g.append(tg)
            self.promo_cells.append((x, y, tg))
        self.promo_group = g
        self.promo_colour = None
        self.root.append(g)

    def _build_dialog(self):
        """The full-screen one-player new-game dialog (colour and level)."""
        fs, fm, fbig = self.font_small, self.font_med, self.font_big
        g = displayio.Group()
        g.hidden = True
        g.append(rect(PANEL_BG, 0, 0, W, H)[0])
        g.append(Text(fbig, W, 0, 6, ACCENT, PANEL_BG, "New Game", align=CENTER).tile)
        g.append(Text(fs, 220, 50, 44, MUTED, PANEL_BG, "Play as").tile)
        g.append(
            Text(fs, 220, 50, 118, MUTED, PANEL_BG, cc.ENGINE_NAME + " level").tile
        )
        self.dlg = {}
        for key, label, x, y, w in (
            ("white", "White", 50, 62, 105),
            ("black", "Black", 165, 62, 105),
            ("level-", "-", 50, 136, 44),
            ("level+", "+", 226, 136, 44),
            ("start", "Start", 50, 196, 105),
            ("cancel", "Cancel", 165, 196, 105),
        ):
            font = fbig if label in "+-" else fm
            self.dlg[key] = Text(
                font, w, x, y, BUTTON_TEXT, BUTTON, label, align=CENTER, height=34
            )
            g.append(self.dlg[key].tile)
        self.dlg_level = Text(fbig, 128, 96, 134, TEXT, PANEL_BG, "", align=CENTER)
        self.dlg_words = Text(fs, 220, 50, 164, MUTED, PANEL_BG, "", align=CENTER)
        self.dlg_time = Text(fs, 220, 50, 178, MUTED, PANEL_BG, "", align=CENTER)
        g.append(self.dlg_level.tile)
        g.append(self.dlg_words.tile)
        g.append(self.dlg_time.tile)
        self.dialog_group = g
        self.root.append(g)

    def _build_menu(self):
        """The full-screen game menu (1 Player / 2 Players / Online, plus Cancel
        during a game), shown at start-up and by NEW."""
        fs, fm, fbig = self.font_small, self.font_med, self.font_big
        g = displayio.Group()
        g.hidden = True
        g.append(rect(PANEL_BG, 0, 0, W, H)[0])
        g.append(Text(fbig, W, 0, 6, ACCENT, PANEL_BG, "New Game", align=CENTER).tile)
        self.menu = {}
        for key, label, note, y in (
            ("one", "1 Player", "against the computer", 38),
            ("two", "2 Players", "two players, one screen", 90),
            ("online", "Online", "another board, over Adafruit IO", 142),
        ):
            self.menu[key] = Text(
                fm, 220, 50, y, BUTTON_TEXT, BUTTON, label, align=CENTER, height=32
            )
            g.append(self.menu[key].tile)
            g.append(
                Text(fs, 220, 50, y + 34, MUTED, PANEL_BG, note, align=CENTER).tile
            )
        self.menu["close"] = Text(
            fm, 105, 165, 196, BUTTON_TEXT, BUTTON, "Cancel", align=CENTER, height=34
        )
        g.append(self.menu["close"].tile)
        self.menu_group = g
        self.root.append(g)

    def _build_online(self):
        """The full-screen online dialog: opponent, connection, Resume, new game."""
        fs, fm, fbig = self.font_small, self.font_med, self.font_big
        g = displayio.Group()
        g.hidden = True
        g.append(rect(PANEL_BG, 0, 0, W, H)[0])
        g.append(
            Text(fbig, W, 0, 6, ACCENT, PANEL_BG, "Online Game", align=CENTER).tile
        )
        self.on_opp = Text(fs, 300, 10, 34, TEXT, PANEL_BG, "", align=CENTER)
        self.on_status = Text(fs, 300, 10, 48, MUTED, PANEL_BG, "", align=CENTER)
        self.on_note = Text(fs, 300, 10, 98, MUTED, PANEL_BG, "", align=CENTER)
        self.on_new = Text(fs, 220, 50, 114, MUTED, PANEL_BG, "New game, play as")
        self.on_me = Text(fs, 300, 10, 168, MUTED, PANEL_BG, "", align=CENTER)
        self.odlg = {}
        for key, label, x, y, w, h in (
            ("o_resume", "Resume", 50, 65, 220, 31),
            ("o_white", "White", 50, 130, 105, 32),
            ("o_black", "Black", 165, 130, 105, 32),
            ("o_start", "Start", 50, 196, 105, 34),
            ("o_back", "Back", 165, 196, 105, 34),
        ):
            self.odlg[key] = Text(
                fm, w, x, y, BUTTON_TEXT, BUTTON, label, align=CENTER, height=h
            )
        for t in (self.on_opp, self.on_status, self.on_note, self.on_new, self.on_me):
            g.append(t.tile)
        for t in self.odlg.values():
            g.append(t.tile)
        self.online_group = g
        self.root.append(g)

    def _render_online(self, c):
        o = c.online
        d = self.odlg
        self.on_opp.set("vs " + o.opp_name() if o.opp else "")
        self.on_me.set("you: " + "/".join(o.me) if o.me else "")
        ok = o.configured
        if not ok:
            a, b = split_line(self.font_small, o.error, 300)
            self.on_status.set(a, BAD)
            self.on_note.set(b, BAD)
            self.on_note.tile.y = 62  # move up under the status (Resume is hidden)
        else:
            self.on_note.tile.y = 98
            self.on_status.set(
                o.status, BAD if o.status_bad else GOOD if o.connected else ACCENT
            )
            self.on_note.set(c.online_note(), MUTED)
        for k in ("o_resume", "o_white", "o_black", "o_start"):
            d[k].tile.hidden = not ok
        self.on_new.tile.hidden = not ok
        self._button(d["o_resume"], c.can_resume(), pressed=self.flash_id == "o_resume")
        self._button(
            d["o_start"], c.can_start_online(), pressed=self.flash_id == "o_start"
        )
        self._button(
            d["o_white"],
            True,
            selected=c.online_white,
            pressed=self.flash_id == "o_white",
        )
        self._button(
            d["o_black"],
            True,
            selected=not c.online_white,
            pressed=self.flash_id == "o_black",
        )
        self._button(d["o_back"], True, pressed=self.flash_id == "o_back")

    # ------------------------------------------------------------ drawing

    @staticmethod
    def _button(t, enabled, pressed=False, selected=False):
        if pressed or selected:
            t.set_colours(PANEL_BG, ACCENT)
        elif enabled:
            t.set_colours(BUTTON_TEXT, BUTTON)
        else:
            t.set_colours(MUTED, BUTTON_OFF)

    def _render_panel(self, c):
        # Header: game type, plus the level when playing the computer
        self.title_text.set(
            "Online"
            if c.players == cc.ONLINE
            else "2 Players" if c.players == 2 else cc.ENGINE_NAME
        )
        self.level_text.set(str(c.settings.level) if c.players == 1 else "")
        l1, c1, l2, c2 = c.status()
        self.status1.set(l1, COLOURS[c1])
        self.status2.set(l2, COLOURS[c2])

        promo = c.promo is not None
        self.info.hidden = promo
        self.promo_group.hidden = not promo
        if promo:
            colour = c.human
            if colour != self.promo_colour:
                self.promo_colour = colour
                base = 1 if colour == cc.WHITE else 7
                for (_x, _y, tg), p in zip(self.promo_cells, (4, 3, 2, 1)):  # Q R B N
                    tg[0] = base + p
        else:
            w, b = c.material
            self.white_pts.set(str(w))
            self.black_pts.set(str(b))
            self.balance.set(c.material_text(), ACCENT if w != b else TEXT)
            self.eval_text.set(c.eval_text(), TEXT if c.has_eval else MUTED)
            self.hint_text.set(c.hint_san)
            share = cc.eval_share(c.eval_white) if c.has_eval else 0.5
            ew = self.eval_w
            px = min(ew - 1, max(1, int(ew * share)))
            if px != self.eval_px:
                self.eval_px = px
                self.eval_white.width = px
                self.eval_black.x = M + 1 + px
                self.eval_black.width = ew - px

        searching = c.searching()
        self.progress.hidden = not searching
        if not searching:
            self.progress_px = 1
            self.progress_bar.width = 1
        # the third button is NEW, or MOVE NOW while the engine thinks
        stop = searching
        if stop != self.stop_shown:
            self.stop_shown = stop
            self.buttons["new"].set("MOVE NOW" if stop else "NEW")
        enabled = {
            "hint": c.can_hint(),
            "undo": c.can_undo(),
            "new": not c.stop_requested if searching else True,
        }
        pressed = {"stop": "new"}.get(self.flash_id, self.flash_id)
        for bid, t in self.buttons.items():
            self._button(t, enabled[bid], pressed=bid == pressed)

        self.menu_group.hidden = c.dialog != "menu"
        if c.dialog == "menu":
            for k, t in self.menu.items():
                self._button(t, True, pressed=self.flash_id == k)
            self.menu["close"].tile.hidden = not c.menu_cancel

        self.online_group.hidden = c.dialog != "online"
        if c.dialog == "online":
            self._render_online(c)

        self.dialog_group.hidden = c.dialog != "new"
        if c.dialog == "new":
            d = self.dlg
            d["cancel"].set("Back" if c.dialog_back else "Cancel")
            self._button(
                d["white"],
                True,
                selected=c.dialog_white,
                pressed=self.flash_id == "white",
            )
            self._button(
                d["black"],
                True,
                selected=not c.dialog_white,
                pressed=self.flash_id == "black",
            )
            for k in ("level-", "level+", "start", "cancel"):
                self._button(d[k], True, pressed=self.flash_id == k)
            lvl = c.dialog_level
            self.dlg_level.set(str(lvl))
            self.dlg_words.set(level_words(lvl))
            ms = cc.engine_time_ms(lvl)
            self.dlg_time.set(
                "%d.%d s per move%s"
                % (
                    ms // 1000,
                    ms // 100 % 10,
                    "" if lvl >= cc.MAX_LEVEL else ", depth <= %d" % (lvl + 1),
                )
            )

    # ------------------------------------------------------------ public

    def render(self, c):
        """Updates the screen from the controller. Returns True if anything changed."""
        if c.version == self.version:
            return False
        self.version = c.version
        self.board.render(c)
        self._render_panel(c)
        return True

    def render_progress(self, c):
        """Moves the thinking-time bar. Returns True if it changed."""
        if not c.searching():
            return False
        px = max(1, int(CW * c.progress()))
        if px == self.progress_px:
            return False
        self.progress_px = px
        self.progress_bar.width = px
        return True

    def flash(self, c, what):
        """Shows a button pressed until the next render."""
        self.flash_id = what
        self.version = -1
        self._render_panel(c)
        self.flash_id = None
        self.version = -1

    def hit(self, c, x, y):
        """Maps a tap at (x, y) to ('square', s), ('button', id), ('promo', piece),
        ('dialog', action) or None."""
        if c.dialog:
            for k, t in {"menu": self.menu, "new": self.dlg, "online": self.odlg}[
                c.dialog
            ].items():
                if not t.tile.hidden and t.contains(x, y):
                    return ("dialog", k)
            return None
        if x < BOARD_PX:
            s = self.board.square_at(x, y, c.flipped)
            return None if s is None else ("square", s)
        px = x - PANEL_X
        if c.promo is not None:
            for (bx, by, _tg), p in zip(self.promo_cells, PROMO_PIECES):
                if bx <= px < bx + PROMO_CELL and by <= y < by + PROMO_CELL:
                    return ("promo", p)
        if M <= px < M + CW:
            for i, (bid, _label) in enumerate(BUTTONS):
                by = BTN_Y0 + i * (BTN_H + BTN_GAP)
                if by - 1 <= y < by + BTN_H + 2:  # include the gaps between buttons
                    if bid == "new" and c.searching():
                        return ("button", "stop")
                    return ("button", bid)
        return None

    # ------------------------------------------------------------ tap positions, for tests

    def square_center(self, s, flipped):
        return self.board.center(s, flipped)

    def button_center(self, bid):
        t = self.buttons["new" if bid == "stop" else bid]
        return PANEL_X + t.tile.x + t.bitmap.width // 2, t.tile.y + t.bitmap.height // 2

    def dialog_center(self, key):
        """Center of a menu or dialog button."""
        t = self.dlg.get(key) or self.odlg.get(key) or self.menu[key]
        return t.tile.x + t.bitmap.width // 2, t.tile.y + t.bitmap.height // 2

    def promo_center(self, piece):
        x, y, _tg = self.promo_cells[PROMO_PIECES.index(piece)]
        return PANEL_X + x + PROMO_CELL // 2, y + PROMO_CELL // 2
