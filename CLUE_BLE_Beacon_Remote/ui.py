# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''Display views for the CLUE MagicBand+ remote.

Three views share the 240x240 TFT through root-group swaps:
  - GridView: 2-col x 3-row grid of category tiles
  - ListView: scrollable command list for a category
  - ConfirmView: modal confirmation for shake-fired random commands
'''
# Target: Adafruit CLUE (nRF52840) - the BLE remote
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.label import Label

_W = 240
_H = 240
_TITLE_H = 24
_STATUS_H = 20

_BG = 0x000000
_FG = 0xFFFFFF
_DIM = 0x404040
_HIGHLIGHT = 0xFF00FF
_ACCENT = 0x00FFFF


class GridView:
    '''Four-tile category grid displayed at startup.'''

    def __init__(self, categories):
        self._categories = categories
        self._selected = 0
        self._group = displayio.Group()
        title = Label(
            terminalio.FONT, text="MagicBand+",
            color=_ACCENT, x=36, y=16,
        )
        title.scale = 2
        self._group.append(title)
        self._tile_rects = []
        self._tile_labels = []
        self._build_tiles()
        self._status = Label(
            terminalio.FONT, text="A/B: select  2xA: open",
            color=_DIM, x=20, y=_H - 10,
        )
        self._group.append(self._status)
        self._refresh()

    @property
    def group(self):
        '''The displayio.Group root for this view.'''
        return self._group

    @property
    def selected(self):
        '''Index of the currently selected tile.'''
        return self._selected

    def next_tile(self):
        '''Move highlight to the next tile (wraps).'''
        self._selected = (self._selected + 1) % len(self._categories)
        self._refresh()

    def prev_tile(self):
        '''Move highlight to the previous tile (wraps).'''
        self._selected = (self._selected - 1) % len(self._categories)
        self._refresh()

    def set_tile(self, idx):
        '''Set the highlighted tile by index.'''
        if 0 <= idx < len(self._categories):
            self._selected = idx
            self._refresh()

    def set_status(self, text, color=_DIM):
        '''Update the bottom status line.'''
        self._status.text = text
        self._status.color = color

    def _build_tiles(self):
        # 2x2 grid with larger tiles now that we have 4 categories
        cell_w = _W // 2
        cell_h = (_H - _TITLE_H - _STATUS_H - 8) // 2
        tile_inner_w = cell_w - 8
        for idx, (name, _commands) in enumerate(self._categories):
            col = idx % 2
            row = idx // 2
            x = col * cell_w + 4
            y = _TITLE_H + 4 + row * (cell_h + 4)
            rect = Rect(x, y, tile_inner_w, cell_h, outline=_DIM, stroke=2)
            label = Label(terminalio.FONT, text=name, color=_FG)
            # Pick the largest scale that fits horizontally with padding.
            # terminalio.FONT is 6px wide per char at scale 1.
            label_w_scale2 = len(name) * 12
            if label_w_scale2 + 12 <= tile_inner_w:
                label.scale = 2
                label_w = label_w_scale2
            else:
                label.scale = 1
                label_w = len(name) * 6
            label.x = x + (tile_inner_w - label_w) // 2
            label.y = y + cell_h // 2
            self._tile_rects.append(rect)
            self._tile_labels.append(label)
            self._group.append(rect)
            self._group.append(label)

    def _refresh(self):
        for idx, rect in enumerate(self._tile_rects):
            if idx == self._selected:
                rect.outline = _HIGHLIGHT
                self._tile_labels[idx].color = _HIGHLIGHT
            else:
                rect.outline = _DIM
                self._tile_labels[idx].color = _FG


class ListView:
    '''Scrollable command list for a single category.'''

    _VISIBLE_ROWS = 7
    _ROW_H = 22
    # Wide enough to fit scale=2 rendering of most names. Longer names
    # automatically fall back to scale=1 to preserve right-side padding.
    _MAX_CHARS_SCALE2 = 18

    def __init__(self):
        self._category_idx = 0
        self._category_name = ""
        self._commands = ()
        self._selected = 0
        self._scroll = 0
        self._group = displayio.Group()
        self._title = Label(
            terminalio.FONT, text="", color=_ACCENT, x=8, y=12,
        )
        self._group.append(self._title)
        self._rows = []
        for i in range(self._VISIBLE_ROWS):
            row = Label(
                terminalio.FONT, text="", color=_FG,
                x=12, y=_TITLE_H + 8 + i * self._ROW_H,
            )
            self._rows.append(row)
            self._group.append(row)
        self._status = Label(
            terminalio.FONT, text="A/B scroll  2xA fire  B-hold off",
            color=_DIM, x=8, y=_H - 10,
        )
        self._group.append(self._status)

    @property
    def group(self):
        '''The displayio.Group root for this view.'''
        return self._group

    @property
    def selected_command(self):
        '''The (name, payload, ping) tuple of the highlighted command.'''
        if not self._commands:
            return None
        return self._commands[self._selected]

    @property
    def category_idx(self):
        '''Index into CATEGORIES of the currently displayed list.'''
        return self._category_idx

    def load_category(self, idx, name, commands):
        '''Populate the list with the commands of one category.'''
        self._category_idx = idx
        self._category_name = name
        self._commands = commands
        self._selected = 0
        self._scroll = 0
        self._title.text = f"{name} ({len(commands)})"
        self._refresh()

    def scroll_up(self):
        '''Move selection up one row (wraps).'''
        if not self._commands:
            return
        self._selected = (self._selected - 1) % len(self._commands)
        self._adjust_scroll()
        self._refresh()

    def scroll_down(self):
        '''Move selection down one row (wraps).'''
        if not self._commands:
            return
        self._selected = (self._selected + 1) % len(self._commands)
        self._adjust_scroll()
        self._refresh()

    def set_status(self, text, color=_DIM):
        '''Update the bottom status line.'''
        self._status.text = text
        self._status.color = color

    def _adjust_scroll(self):
        if self._selected < self._scroll:
            self._scroll = self._selected
        elif self._selected >= self._scroll + self._VISIBLE_ROWS:
            self._scroll = self._selected - self._VISIBLE_ROWS + 1

    def _refresh(self):
        for i, row in enumerate(self._rows):
            cmd_idx = self._scroll + i
            if cmd_idx >= len(self._commands):
                row.text = ""
                continue
            name = self._commands[cmd_idx][0]
            marker = ">" if cmd_idx == self._selected else " "
            full = f"{marker}{name}"
            row.scale = 2 if len(full) <= self._MAX_CHARS_SCALE2 else 1
            row.text = full
            row.color = _HIGHLIGHT if cmd_idx == self._selected else _FG


class ConfirmView:
    '''Modal confirmation for shake-fired random commands.'''

    def __init__(self):
        self._group = displayio.Group()
        self._group.append(Label(
            terminalio.FONT, text="Shake! Fire this?",
            color=_ACCENT, x=50, y=40,
        ))
        self._command_label = Label(
            terminalio.FONT, text="", color=_HIGHLIGHT,
            x=20, y=110, scale=2,
        )
        self._group.append(self._command_label)
        self._group.append(Label(
            terminalio.FONT, text="2xA: Fire",
            color=_FG, x=8, y=200,
        ))
        self._group.append(Label(
            terminalio.FONT, text="B: Cancel",
            color=_FG, x=178, y=200,
        ))

    @property
    def group(self):
        '''The displayio.Group root for this view.'''
        return self._group

    def set_command(self, name):
        '''Set the command name shown in the confirm modal.'''
        self._command_label.text = name


class ListenView:
    '''BLE listening / capture view. Minimal to keep memory low.'''

    def __init__(self):
        self._group = displayio.Group()
        title = Label(
            terminalio.FONT, text="Listen Mode",
            color=_ACCENT, x=36, y=16,
        )
        title.scale = 2
        self._group.append(title)
        # One label for all stats - updated less often than per-field labels
        # to reduce bitmap allocation churn. Pre-allocated with worst-case
        # length string so re-rendering reuses the same bitmap.
        # 18 chars at scale 2 = 216px wide, fits on 240px display
        self._stats_label = Label(
            terminalio.FONT,
            text="                  ",  # 18 chars padding
            color=_FG, x=8, y=72,
        )
        self._stats_label.scale = 2
        self._group.append(self._stats_label)
        self._status = Label(
            terminalio.FONT,
            text="                              ",
            color=_DIM, x=8, y=_H - 10,
        )
        self._group.append(self._status)
        self._status.text = "Hold B to stop"

    @property
    def group(self):
        '''The displayio.Group root for this view.'''
        return self._group

    def update_stats(self, elapsed_s, total, unique, _last_rssi, _rate=None):
        '''Update the stats label with the current capture summary.

        last_rssi/rate are accepted for caller-API stability but not shown
        on screen at scale 2 - the 240px display only fits the compact
        "Ns U/T" format. Underscore prefix marks them as intentionally
        unused for the linter.
        '''
        # Compact format that fits at scale 2 on the 240px display.
        # 18 chars * 12px = 216px, leaves margin.
        # Format: "{seconds}s {unique}/{total}"  e.g. "47s 12/823"
        text = f"{int(elapsed_s)}s {unique}/{total}"
        # Pad to 18 chars to keep bitmap allocation stable
        self._stats_label.text = f"{text:<18s}"

    def set_status(self, text, color=_DIM):
        '''Update the bottom status line.'''
        # Status stays at scale 1 (smaller), pad to ~30 chars
        self._status.text = f"{text:<30s}"
        self._status.color = color
