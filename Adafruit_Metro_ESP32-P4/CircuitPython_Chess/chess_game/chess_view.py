# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=attribute-defined-outside-init, too-many-branches, too-many-locals
# pylint: disable=too-many-statements
"""Chess screen for the 1280x720 DSI display: board on the left, panel on the right.

The displayio tree is built once. render() only changes what differs from the
screen, so a refresh redraws just those areas.

  root
    board (0, 0), 720 x 720 (the Board class, shared with chess_view_s)
      squares   64 one-pixel TileGrids scaled 90x: each square's colour
      coords    file letters along the bottom, rank digits down the left
      marks     64 TileGrids: legal-move dots and capture corners
      pieces    64 TileGrids of 90 px piece tiles (index 0 is transparent)
    panel (720, 0), 560 x 720
      header, status lines, info rows, eval bar, progress bar, buttons
      promotion picker (replaces the info rows)
      menu, new-game dialog and online dialog (cover the panel below the header)
"""

import displayio

import chess_ctrl as cc
from chess_gfx import (
    CENTER,
    LEFT,
    RIGHT,
    Font,
    Text,
    fill_ramp,
    load_bitmap,
    rect,
    split_line,
)

SQ = 90
BOARD_PX = 8 * SQ
PANEL_X = BOARD_PX
PANEL_W = 1280 - BOARD_PX
M = 28  # panel margin
CW = PANEL_W - 2 * M  # panel content width
HEADER_H = 80

LIGHT = 0xC0C0C0
DARK = 0x3C64C8
WHITE_PIECE = 0xFFFFFF
WHITE_OUTLINE = 0x000000
BLACK_PIECE = 0x000000
BLACK_OUTLINE = 0x969696
SELECTED = 0xFFA500
CHECK = 0xDC3C3C
HINT_LIGHT = 0x82D778
HINT_DARK = 0x46AA5A
LAST_LIGHT = 0xE6DC78
LAST_DARK = 0x96A078
TARGET_DOT = 0x282828

PANEL_BG = 0x181C28
PANEL_HEADER = 0x2D468C
TEXT = 0xEBEBEB
MUTED = 0x8C91A0
ACCENT = 0xFFA500
LINE = 0x3C4255
BUTTON = 0x374B7D
BUTTON_OFF = 0x2D303A
BUTTON_TEXT = 0xFFFFFF
GOOD = 0x5AD26E
BAD = 0xF05A5A
COLOURS = {"good": GOOD, "bad": BAD, "accent": ACCENT, "text": TEXT, "muted": MUTED}

# square palette indices
SQ_LIGHT, SQ_DARK, SQ_SELECTED, SQ_CHECK, SQ_HINT, SQ_LAST = 0, 1, 2, 3, 4, 6

# panel layout (panel coordinates)
STATUS1_Y = 96
STATUS2_Y = 160
SEP_Y = 214
ROW_Y = (232, 282, 360, 410)  # material, eval, hint, search info
EVALBAR_Y = 324
EVALBAR_H = 16
PROGRESS_Y = 458
PROGRESS_H = 10
BTN_Y = (484, 600)
BTN_H = 100
BTN_W = (CW - 16) // 2
BUTTONS = (
    ("hint", "HINT"),
    ("undo", "UNDO"),
    ("new", "NEW GAME"),
    ("stop", "MOVE NOW"),
)

PROMO_PIECES = "qrbn"
PROMO_BOX = 112
PROMO_Y = 300


def piece_tile(code):
    """Board code (1-6 white, 9-14 black) -> tile in pieces.bmp (1-6 white, 7-12 black)."""
    if code == 0:
        return 0
    return code if code < 8 else code - 2


def square_grids(bitmap, palette, size):
    """Returns (Group, list) of 64 one-tile TileGrids, indexed row * 8 + col.

    displayio tracks one dirty rectangle per TileGrid, so separate grids let a
    refresh redraw only the changed squares instead of the whole board."""
    group = displayio.Group()
    cells = []
    for row in range(8):
        for col in range(8):
            t = displayio.TileGrid(
                bitmap,
                pixel_shader=palette,
                tile_width=size,
                tile_height=size,
                x=col * size,
                y=row * size,
            )
            group.append(t)
            cells.append(t)
    return group, cells


class Board:
    """The 8x8 board (squares, coordinates, move marks, pieces) as a Group at (0, 0).

    sq is the square size in pixels; the assets in folder a must match it.
    Used by both views (90 px squares on the DSI display, 30 px on the shield)."""

    def __init__(self, a, sq):
        self.sq = sq
        px = 8 * sq
        board = displayio.Group()
        self.group = board
        self.flipped = None

        pal = displayio.Palette(8)
        for i, c in enumerate(
            (LIGHT, DARK, SELECTED, CHECK, HINT_LIGHT, HINT_DARK, LAST_LIGHT, LAST_DARK)
        ):
            pal[i] = c
        # one pixel of each colour, scaled up to a square
        swatches = displayio.Bitmap(8, 1, 8)
        for i in range(8):
            swatches[i, 0] = i
        # colour index currently shown in each screen cell
        self.sq_cache = bytearray(b"\xff" * 64)
        g = displayio.Group(scale=sq)
        cells, self.squares = square_grids(swatches, pal, 1)
        g.append(cells)
        board.append(g)

        # Coordinates: one set of TileGrids per square colour, so the
        # anti-aliasing blends into the right background.
        files, _ = load_bitmap(a + "files.bmp")
        ranks, _ = load_bitmap(a + "ranks.bmp")
        self.coord_grids = []
        for on_light in (True, False):
            p = displayio.Palette(16)
            if on_light:
                fill_ramp(p, LIGHT, DARK)
            else:
                fill_ramp(p, DARK, LIGHT)
            p.make_transparent(0)
            fg = displayio.TileGrid(
                files,
                pixel_shader=p,
                width=8,
                height=1,
                tile_width=sq,
                tile_height=files.height,
                x=0,
                y=px - files.height,
            )
            rg = displayio.TileGrid(
                ranks,
                pixel_shader=p,
                width=1,
                height=8,
                tile_width=ranks.width // 9,
                tile_height=sq,
                x=0,
                y=0,
            )
            board.append(fg)
            board.append(rg)
            self.coord_grids.append((fg, rg))

        marks, _ = load_bitmap(a + "marks.bmp")
        p = displayio.Palette(2)
        p[1] = TARGET_DOT
        p.make_transparent(0)
        cells, self.marks = square_grids(marks, p, sq)
        board.append(cells)
        self.mark_cache = bytearray(64)

        pieces, _ = load_bitmap(a + "pieces.bmp")
        p = displayio.Palette(5)
        p[1], p[2], p[3], p[4] = WHITE_PIECE, WHITE_OUTLINE, BLACK_PIECE, BLACK_OUTLINE
        p.make_transparent(0)
        self.piece_sheet, self.piece_palette = pieces, p
        cells, self.pieces = square_grids(pieces, p, sq)
        board.append(cells)
        self.piece_cache = bytearray(64)

    def cell(self, s, flipped):
        """Square -> (col, row) on screen."""
        f, r = s & 7, s >> 3
        return (7 - f, r) if flipped else (f, 7 - r)

    def center(self, s, flipped):
        """Square -> screen (x, y) of its center."""
        col, row = self.cell(s, flipped)
        return col * self.sq + self.sq // 2, row * self.sq + self.sq // 2

    def square_at(self, x, y, flipped):
        """Screen (x, y) -> square, or None off the board."""
        n = 8 * self.sq
        if not (0 <= x < n and 0 <= y < n):
            return None
        col, row = x // self.sq, y // self.sq
        if flipped:
            return (7 - col) + 8 * row
        return col + 8 * (7 - row)

    def _set_coords(self, flipped):
        # pylint: disable=unbalanced-tuple-unpacking
        (light_files, light_ranks), (dark_files, dark_ranks) = self.coord_grids
        for c in range(8):
            f = 7 - c if flipped else c
            light = (c + 7) % 2 == 0
            light_files[c] = 1 + f if light else 0
            dark_files[c] = 0 if light else 1 + f
        for row in range(8):
            r = row if flipped else 7 - row
            light = row % 2 == 0
            light_ranks[row] = 1 + r if light else 0
            dark_ranks[row] = 0 if light else 1 + r

    def render(self, c):
        flipped = c.flipped
        if flipped != self.flipped:
            self.flipped = flipped
            self._set_coords(flipped)
            self.sq_cache[:] = b"\xff" * 64
            self.piece_cache[:] = b"\xff" * 64
            self.mark_cache[:] = b"\xff" * 64
        board = c.board
        targets = c.targets
        for s in range(64):
            col, row = self.cell(s, flipped)
            i = row * 8 + col
            light = (col + row) % 2 == 0
            if s == c.selected:
                bg = SQ_SELECTED
            elif s == c.check_sq:
                bg = SQ_CHECK
            elif s in (c.hint_from, c.hint_to):
                bg = SQ_HINT + (0 if light else 1)
            elif s in (c.last_from, c.last_to):
                bg = SQ_LAST + (0 if light else 1)
            else:
                bg = SQ_LIGHT if light else SQ_DARK
            if self.sq_cache[i] != bg:
                self.sq_cache[i] = bg
                self.squares[i][0] = bg
            t = piece_tile(board[s])
            if self.piece_cache[i] != t:
                self.piece_cache[i] = t
                self.pieces[i][0] = t
            m = (2 if board[s] else 1) if s in targets else 0
            if self.mark_cache[i] != m:
                self.mark_cache[i] = m
                self.marks[i][0] = m


class View:
    def __init__(self, asset_dir):
        a = asset_dir + "/"
        self.font_small = Font(a + "font_small.bin")
        self.font_med = Font(a + "font_med.bin")
        self.font_big = Font(a + "font_big.bin")
        self.root = displayio.Group()
        self._build_board(a)
        self._build_panel()
        self.version = -1
        self.flash_id = None

    # ------------------------------------------------------------ board

    def _build_board(self, a):
        self.board = Board(a, SQ)
        self.root.append(self.board.group)
        self.piece_sheet, self.piece_palette = (
            self.board.piece_sheet,
            self.board.piece_palette,
        )

    def cell(self, s, flipped):
        """Square -> (col, row) on screen."""
        return self.board.cell(s, flipped)

    # ------------------------------------------------------------ panel

    def _build_panel(self):
        panel = displayio.Group(x=PANEL_X)
        self.root.append(panel)
        self.panel = panel
        panel.append(rect(PANEL_BG, 0, 0, PANEL_W, 720)[0])
        panel.append(rect(PANEL_HEADER, 0, 0, PANEL_W, HEADER_H)[0])
        fs, fm, fb = self.font_small, self.font_med, self.font_big
        hy = (HEADER_H - fm.height) // 2
        self.title_text = Text(
            fm, 300, M, hy, BUTTON_TEXT, PANEL_HEADER, cc.ENGINE_NAME
        )
        panel.append(self.title_text.tile)
        self.level_text = Text(
            fs,
            200,
            PANEL_W - M - 200,
            (HEADER_H - fs.height) // 2,
            TEXT,
            PANEL_HEADER,
            "",
            align=RIGHT,
        )
        panel.append(self.level_text.tile)

        self.status1 = Text(fb, CW, M, STATUS1_Y, GOOD, PANEL_BG)
        self.status2 = Text(fm, CW, M, STATUS2_Y, TEXT, PANEL_BG)
        panel.append(self.status1.tile)
        panel.append(self.status2.tile)
        panel.append(rect(LINE, M, SEP_Y, CW, 2)[0])

        # info rows, hidden while the promotion picker is open
        self.info = displayio.Group()
        panel.append(self.info)
        self.values = []
        for y, label in zip(ROW_Y[:3], ("Material", "Eval", "Hint")):
            ly = y + (fm.height - fs.height) // 2 + 2
            self.info.append(Text(fs, 200, M, ly, MUTED, PANEL_BG, label).tile)
            v = Text(fm, CW - 200, M + 200, y, TEXT, PANEL_BG, "", align=RIGHT)
            self.values.append(v)
            self.info.append(v.tile)
        self.search_text = Text(fs, CW, M, ROW_Y[3], MUTED, PANEL_BG)
        self.info.append(self.search_text.tile)
        self.info.append(rect(MUTED, M - 2, EVALBAR_Y - 2, CW + 4, EVALBAR_H + 4)[0])
        self.eval_white, _ = rect(WHITE_PIECE, M, EVALBAR_Y, CW // 2, EVALBAR_H)
        self.eval_black, _ = rect(
            BLACK_PIECE, M + CW // 2, EVALBAR_Y, CW - CW // 2, EVALBAR_H
        )
        self.info.append(self.eval_white)
        self.info.append(self.eval_black)
        self.eval_px = CW // 2

        # engine thinking-time bar
        self.progress = displayio.Group()
        self.progress.append(rect(LINE, M, PROGRESS_Y, CW, PROGRESS_H)[0])
        self.progress_bar, _ = rect(ACCENT, M, PROGRESS_Y, 1, PROGRESS_H)
        self.progress.append(self.progress_bar)
        self.progress.hidden = True
        self.progress_px = 1
        panel.append(self.progress)

        self.buttons = {}
        for i, (bid, label) in enumerate(BUTTONS):
            x = M + (i % 2) * (BTN_W + 16)
            t = Text(
                fm,
                BTN_W,
                x,
                BTN_Y[i // 2],
                BUTTON_TEXT,
                BUTTON,
                label,
                align=CENTER,
                height=BTN_H,
            )
            self.buttons[bid] = t
            panel.append(t.tile)

        self._build_promotion(fm)
        self._build_dialog(fs, fm, fb)
        self._build_menu(fs, fm, fb)
        self._build_online(fs, fm, fb)

    def _build_promotion(self, fm):
        g = displayio.Group()
        g.hidden = True
        g.append(rect(PANEL_BG, 0, SEP_Y + 2, PANEL_W, BTN_Y[0] - SEP_Y - 6)[0])
        g.append(Text(fm, CW, M, ROW_Y[0], TEXT, PANEL_BG, "Promote to:").tile)
        self.promo_boxes = []
        gap = (CW - 4 * PROMO_BOX) // 3
        for i in range(4):
            x = M + i * (PROMO_BOX + gap)
            g.append(rect(BUTTON, x, PROMO_Y, PROMO_BOX, PROMO_BOX)[0])
            tg = displayio.TileGrid(
                self.piece_sheet,
                pixel_shader=self.piece_palette,
                tile_width=SQ,
                tile_height=SQ,
                x=x + (PROMO_BOX - SQ) // 2,
                y=PROMO_Y + (PROMO_BOX - SQ) // 2,
            )
            g.append(tg)
            self.promo_boxes.append((x, tg))
        self.promo_group = g
        self.promo_colour = None
        self.panel.append(g)

    def _build_dialog(self, fs, fm, fb):
        g = displayio.Group()
        g.hidden = True
        g.append(rect(PANEL_BG, 0, HEADER_H, PANEL_W, 720 - HEADER_H)[0])
        g.append(Text(fb, CW, M, 96, TEXT, PANEL_BG, "New game").tile)
        g.append(Text(fs, CW, M, 178, MUTED, PANEL_BG, "Play as").tile)
        half = (CW - 16) // 2
        self.dlg = {}
        self.dlg["white"] = Text(
            fm, half, M, 214, BUTTON_TEXT, BUTTON, "White", align=CENTER, height=90
        )
        self.dlg["black"] = Text(
            fm,
            half,
            M + half + 16,
            214,
            BUTTON_TEXT,
            BUTTON,
            "Black",
            align=CENTER,
            height=90,
        )
        g.append(Text(fs, CW, M, 326, MUTED, PANEL_BG, "Level (0-20)").tile)
        self.dlg["level-"] = Text(
            fb, 120, M, 362, BUTTON_TEXT, BUTTON, "-", align=CENTER, height=90
        )
        self.dlg["level+"] = Text(
            fb,
            120,
            M + CW - 120,
            362,
            BUTTON_TEXT,
            BUTTON,
            "+",
            align=CENTER,
            height=90,
        )
        self.dlg_level = Text(
            fb, CW - 260, M + 130, 362, TEXT, PANEL_BG, "", align=CENTER, height=90
        )
        self.dlg_time = Text(fs, CW, M, 470, MUTED, PANEL_BG, "", align=CENTER)
        self.dlg["start"] = Text(
            fm,
            BTN_W,
            M,
            BTN_Y[1],
            BUTTON_TEXT,
            BUTTON,
            "START",
            align=CENTER,
            height=BTN_H,
        )
        self.dlg["cancel"] = Text(
            fm,
            BTN_W,
            M + BTN_W + 16,
            BTN_Y[1],
            BUTTON_TEXT,
            BUTTON,
            "CANCEL",
            align=CENTER,
            height=BTN_H,
        )
        for t in self.dlg.values():
            g.append(t.tile)
        g.append(self.dlg_level.tile)
        g.append(self.dlg_time.tile)
        self.dialog_group = g
        self.panel.append(g)

    def _build_menu(self, fs, fm, fb):
        """The game menu (1 PLAYER / 2 PLAYERS / ONLINE, plus CANCEL during a
        game), shown at start-up and by NEW GAME."""
        g = displayio.Group()
        g.hidden = True
        g.append(rect(PANEL_BG, 0, HEADER_H, PANEL_W, 720 - HEADER_H)[0])
        g.append(Text(fb, CW, M, 96, TEXT, PANEL_BG, "New game").tile)
        self.menu = {}
        for key, label, note, y in (
            ("one", "1 PLAYER", "Play against the computer", 176),
            ("two", "2 PLAYERS", "Two players, one screen", 318),
            ("online", "ONLINE", "Play another board over Adafruit IO", 460),
        ):
            self.menu[key] = Text(
                fm, CW, M, y, BUTTON_TEXT, BUTTON, label, align=CENTER, height=90
            )
            g.append(self.menu[key].tile)
            g.append(Text(fs, CW, M, y + 96, MUTED, PANEL_BG, note, align=CENTER).tile)
        self.menu["close"] = Text(
            fm,
            BTN_W,
            M + BTN_W + 16,
            BTN_Y[1],
            BUTTON_TEXT,
            BUTTON,
            "CANCEL",
            align=CENTER,
            height=BTN_H,
        )
        g.append(self.menu["close"].tile)
        self.menu_group = g
        self.panel.append(g)

    def _build_online(self, fs, fm, fb):
        """The online dialog: players, connection status, RESUME and new game."""
        g = displayio.Group()
        g.hidden = True
        g.append(rect(PANEL_BG, 0, HEADER_H, PANEL_W, 720 - HEADER_H)[0])
        g.append(Text(fb, CW, M, 96, TEXT, PANEL_BG, "Online game").tile)
        self.on_me = Text(fs, CW, M, 166, MUTED, PANEL_BG)
        self.on_opp = Text(fs, CW, M, 196, TEXT, PANEL_BG)
        self.on_status = Text(fs, CW, M, 230, MUTED, PANEL_BG)
        self.on_note = Text(fs, CW, M, 360, MUTED, PANEL_BG, "", align=CENTER)
        self.on_new = Text(fs, CW, M, 404, MUTED, PANEL_BG, "New game, play as")
        half = (CW - 16) // 2
        self.odlg = {}
        self.odlg["o_resume"] = Text(
            fm, CW, M, 272, BUTTON_TEXT, BUTTON, "RESUME", align=CENTER, height=80
        )
        self.odlg["o_white"] = Text(
            fm, half, M, 438, BUTTON_TEXT, BUTTON, "White", align=CENTER, height=80
        )
        self.odlg["o_black"] = Text(
            fm,
            half,
            M + half + 16,
            438,
            BUTTON_TEXT,
            BUTTON,
            "Black",
            align=CENTER,
            height=80,
        )
        self.odlg["o_start"] = Text(
            fm,
            BTN_W,
            M,
            BTN_Y[1],
            BUTTON_TEXT,
            BUTTON,
            "START",
            align=CENTER,
            height=BTN_H,
        )
        self.odlg["o_back"] = Text(
            fm,
            BTN_W,
            M + BTN_W + 16,
            BTN_Y[1],
            BUTTON_TEXT,
            BUTTON,
            "BACK",
            align=CENTER,
            height=BTN_H,
        )
        for t in (self.on_me, self.on_opp, self.on_status, self.on_note, self.on_new):
            g.append(t.tile)
        for t in self.odlg.values():
            g.append(t.tile)
        self.online_group = g
        self.panel.append(g)

    def _render_online(self, c):
        o = c.online
        d = self.odlg
        if o.me:
            self.on_me.set("You: " + "/".join(o.me))
        self.on_opp.set("Opponent: " + o.opp_name() if o.opp else "")
        ok = o.configured
        if not ok:
            a, b = split_line(self.font_small, o.error, CW)
            self.on_status.set(a, BAD)
            self.on_note.align = LEFT
            self.on_note.set(b, BAD)
            self.on_note.tile.y = 260  # move up under the status (RESUME is hidden)
        else:
            self.on_note.align = CENTER
            self.on_note.tile.y = 360
            self.on_status.set(
                o.status, BAD if o.status_bad else GOOD if o.connected else ACCENT
            )
            self.on_note.set(c.online_note(), MUTED)
        for k in ("o_white", "o_black", "o_start"):
            d[k].tile.hidden = not ok
        self.on_new.tile.hidden = not ok
        d["o_resume"].tile.hidden = not ok
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

    def _button(self, t, enabled, pressed=False, selected=False):
        if pressed:
            t.set_colours(BUTTON_TEXT, ACCENT)
        elif selected:
            t.set_colours(0x000000, ACCENT)
        elif enabled:
            t.set_colours(BUTTON_TEXT, BUTTON)
        else:
            t.set_colours(MUTED, BUTTON_OFF)

    def _render_panel(self, c):
        # Header: game type and opponent
        if c.players == cc.ONLINE:
            self.title_text.set("Online")
            self.level_text.set("vs " + c.online.opp[0] if c.online.opp else "")
        elif c.players == 2:
            self.title_text.set("2 Players")
            self.level_text.set("")
        else:
            self.title_text.set(cc.ENGINE_NAME)
            self.level_text.set("Level %d" % c.settings.level)
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
                for (_x, tg), p in zip(self.promo_boxes, (4, 3, 2, 1)):  # Q R B N
                    tg[0] = base + p
        else:
            self.values[0].set(
                c.material_text(), ACCENT if c.material[0] != c.material[1] else TEXT
            )
            self.values[1].set(c.eval_text(), TEXT if c.has_eval else MUTED)
            self.values[2].set(c.hint_san or "-", GOOD if c.hint_san else MUTED)
            self.search_text.set(c.search_info)
            share = cc.eval_share(c.eval_white) if c.has_eval else 0.5
            px = min(CW - 1, max(1, int(CW * share + 0.5)))
            if px != self.eval_px:
                self.eval_px = px
                self.eval_white.width = px
                self.eval_black.x = M + px
                self.eval_black.width = CW - px

        searching = c.searching()
        self.progress.hidden = not searching
        if not searching:
            self.progress_px = 1
            self.progress_bar.width = 1
        enabled = {
            "hint": c.can_hint(),
            "undo": c.can_undo(),
            "new": not searching,
            "stop": searching and not c.stop_requested,
        }
        for bid, t in self.buttons.items():
            self._button(t, enabled[bid], pressed=bid == self.flash_id)

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
            d["cancel"].set("BACK" if c.dialog_back else "CANCEL")
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
            self.dlg_level.set(str(c.dialog_level))
            ms = cc.engine_time_ms(c.dialog_level)
            self.dlg_time.set(
                "%d.%d s per move%s"
                % (
                    ms // 1000,
                    ms // 100 % 10,
                    (
                        ""
                        if c.dialog_level >= cc.MAX_LEVEL
                        else ", depth <= %d" % (c.dialog_level + 1)
                    ),
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
        if x < BOARD_PX:
            s = self.board.square_at(x, y, c.flipped)
            return None if s is None else ("square", s)
        px = x - PANEL_X
        if c.dialog:
            for k, t in self._dialog_buttons(c).items():
                if not t.tile.hidden and t.contains(px, y):
                    return ("dialog", k)
            return None
        if c.promo is not None:
            for (bx, _tg), p in zip(self.promo_boxes, PROMO_PIECES):
                if bx <= px < bx + PROMO_BOX and PROMO_Y <= y < PROMO_Y + PROMO_BOX:
                    return ("promo", p)
        for bid, t in self.buttons.items():
            if t.contains(px, y):
                return ("button", bid)
        return None

    def _dialog_buttons(self, c):
        return {"menu": self.menu, "new": self.dlg, "online": self.odlg}[c.dialog]

    # ------------------------------------------------------------ tap positions, for tests

    def square_center(self, s, flipped):
        return self.board.center(s, flipped)

    def button_center(self, bid):
        t = self.buttons[bid]
        return PANEL_X + t.tile.x + t.bitmap.width // 2, t.tile.y + t.bitmap.height // 2

    def dialog_center(self, key):
        """Center of a menu or dialog button."""
        t = self.dlg.get(key) or self.odlg.get(key) or self.menu[key]
        return PANEL_X + t.tile.x + t.bitmap.width // 2, t.tile.y + t.bitmap.height // 2

    def promo_center(self, piece):
        bx = self.promo_boxes[PROMO_PIECES.index(piece)][0]
        return PANEL_X + bx + PROMO_BOX // 2, PROMO_Y + PROMO_BOX // 2
