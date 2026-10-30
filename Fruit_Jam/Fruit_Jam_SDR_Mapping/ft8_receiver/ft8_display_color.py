# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Color DVI display for ft8_receiver.py: the screen of ft8_display_dvi
(same layout and rows) drawn with adafruit_color_terminal.

Each callsign gets a color the first time it is heard and keeps it, so
the two sides of a QSO are easy to follow down the screen. There are 15
call colors: a new call gets the one that has gone longest without
being shown, so calls on the screen share colors as little as they can.
A call whose color has since gone to another call gets a new one when it
is heard again. MY_CALL is shown inverted. The time, SNR, DT and audio
frequency are grey and the frequency row is a grey bar.

The call colors are palette entries past ColorTerminal's ANSI ones, in
256-color codes ('\x1b[38;5;12m'), which pair() maps itself. The DVI
framebuffer has 8-bit color (RGB332), so they are RGB332 values, picked
on the screen for being told apart.

Rows are made with ANSI color codes, which ColorTerminal turns into
palette entries for its TilePaletteMapper. Rows are not written with
ColorTerminal.write(): it parses the text a character at a time and sets
the colors of every cell, and with the radio running a decode took up to
126 ms to draw, long enough to lose USB packets. Here the text goes to the
terminalio.Terminal in one write and only the cells whose colors change
are set (at most 42 ms a decode, against 20 ms for ft8_display_dvi).

"""
import displayio
from terminalio import FONT
from adafruit_color_terminal import ColorTerminal
import ft8_help
from ft8_display_dvi import DviDisplay, STATUS_ROWS, message_columns, join_columns

# pylint: disable=too-many-locals

RESET = '\x1b[0m'
GREY = '\x1b[90;40m'
BAR = '\x1b[30;100m'          # background color on grey
MINE = '\x1b[30;47m'          # background color on white
DEFAULT = [0, 1]              # [background, foreground] palette entries (a
                              # list: TilePaletteMapper takes no tuples)

# ColorTerminal palette: background, text, red, green, yellow, blue,
# magenta, cyan, grey (ANSI 30-37 and 90).
ANSI_PALETTE = (0x07111d, 0xeaf1fa, 0xff6b6b, 0x5fe07a, 0xffd84d, 0x6fa8ff, 0xf07cff, 0x4fe3e3,
                0x8a96a8)
# Callsign colors (RGB332 values), in the order a fresh screen gives them out.
CALL_RGB = (
    0xffff00,   # yellow
    0x496dff,   # blue
    0xff00ff,   # magenta
    0x49ff00,   # green
    0xff9200,   # orange
    0x00ffff,   # cyan
    0xb624ff,   # purple
    0xb6ff00,   # chartreuse
    0xff2400,   # red
    0x6db6ff,   # sky
    0xff6daa,   # pink
    0x00b6aa,   # teal
    0xffb6aa,   # salmon
    0xdb92ff,   # lavender
    0x6dffaa,   # mint
)
PALETTE = ANSI_PALETTE + CALL_RGB
CALL_COLORS = tuple('\x1b[38;5;%dm' % (len(ANSI_PALETTE) + k) for k in range(len(CALL_RGB)))


def is_grid(word):
    """'FN42' (also 'RR73', which reads as one)."""
    return (len(word) == 4 and 'A' <= word[0] <= 'R' and 'A' <= word[1] <= 'R'
            and word[2].isdigit() and word[3].isdigit())


def is_call(word):
    """'K1ABC', 'VE3/K1ABC', 'K1ABC/P': letters and digits (and '/'),
    with at least one of each, and not a grid."""
    letter = digit = False
    for c in word:
        if 'A' <= c <= 'Z':
            letter = True
        elif '0' <= c <= '9':
            digit = True
        elif c != '/':
            return False
    return letter and digit and len(word) >= 3 and not is_grid(word)


class ColorDisplay(DviDisplay):
    NAME = 'color'
    ROW_STYLES = {0: BAR, STATUS_ROWS: GREY}

    def __init__(self, screen=None, views=False):
        self.call_colors = {}                       # call -> CALL_COLORS index
        self.owner = [None] * len(CALL_COLORS)      # the call each color is with
        self.shown_at = [0] * len(CALL_COLORS)      # when each color was last shown
        self.shown = 0
        self._pairs = {}
        super().__init__(screen, views)

    def help_rows(self, views):
        return ft8_help.text_rows(True, views)

    def make_terminal(self, fw, fh):
        pal = displayio.Palette(len(PALETTE))
        for k, color in enumerate(PALETTE):
            pal[k] = color
        self.term = ColorTerminal(FONT, self.columns, self.rows, custom_palette=pal)
        # colors on the screen
        self._cells = [[DEFAULT] * self.columns for _ in range(self.rows)]
        return self.term.tilegrid

    def pair(self, code):
        """The [background, foreground] of a color code ('[33m', or
        '[38;5;12m' for palette entry 12), from the default colors."""
        p = self._pairs.get(code)
        if p is None:
            if code.startswith('[38;5;'):
                p = [DEFAULT[0], int(code[6:-1])]
            else:
                self.term.cur_color_mapping = list(DEFAULT)
                p = self.term.get_color_mapping(code[1:])
            self._pairs[code] = p
        return p

    def row(self, row, text):
        """Rewrite one screen row if it changed. text may have color codes;
        spaces after it keep the last color (the bar)."""
        if row >= self.rows:
            return
        text = self.ROW_STYLES.get(row, RESET) + text      # starts with a code
        if self._shown.get(row) == text:
            return
        self._shown[row] = text
        width = self.columns - 1         # one column short: see DviDisplay
        cells = self._cells[row]
        tpm = self.term.tpm
        # The colors go by the TileGrid's own rows, which the terminal
        # offsets (it starts scrolled by one): the cursor has that row.
        self.term.terminal.write('\x1b[%d;1H' % (row + 1))
        y = self.term.cursor_y
        plain = []
        x = 0
        pieces = text.split('\x1b')
        for k in range(1, len(pieces)):
            piece = pieces[k]
            m = piece.find('m') + 1
            pair = self.pair(piece[:m])
            piece = piece[m:m + width - x]
            end = x + len(piece) if k < len(pieces) - 1 else width
            plain.append(piece)
            # Only the cells whose colors change (pairs are shared: 'is'),
            # and of a space only its background: a refresh after text and
            # color changes takes as long as one for each (about 8 ms a row).
            for c in range(x, end):
                now = cells[c]
                if now is not pair and (now[0] != pair[0]
                                        or c - x < len(piece) and piece[c - x] != ' '):
                    cells[c] = pair
                    tpm[c, y] = pair
            x += len(piece)
        self.term.terminal.write('%s%s' % (''.join(plain), ' ' * (width - x)))
        self.display.refresh(minimum_frames_per_second=0)

    def screen(self):
        width = self.columns - 1
        return [('%-*s' % (width, ColorTerminal.parse_ansi_colors(s)[0]))[:width] if s else ''
                for s in super().screen()]

    def color_for(self, call):
        """The color code of a callsign. A call without one gets the color
        that has gone longest without being shown (from the call that had it)."""
        k = self.call_colors.get(call)
        if k is None:
            k = 0
            for i in range(1, len(CALL_COLORS)):
                if self.shown_at[i] < self.shown_at[k]:
                    k = i
            self.call_colors.pop(self.owner[k], None)
            self.call_colors[call] = k
            self.owner[k] = call
        self.shown += 1
        self.shown_at[k] = self.shown
        return CALL_COLORS[k]

    def format_decode(self, d, my_call=''):
        columns = message_columns(d['text'])
        words = []
        mine = False
        for word in columns:
            call = word.strip('<>')       # '<K1ABC>': a call sent as a hash
            if call and call == my_call:
                mine = True
                word = word.replace(call, MINE + call + RESET)
            elif is_call(call):
                word = word.replace(call, self.color_for(call) + call + RESET)
            words.append(word)
        return '%s%s%s %3d %4.1f %4d%s %s' % ('>' if mine else ' ', GREY, d['t'][7:], d['snr'],
                                              d['dt'], d['freq'], RESET,
                                              join_columns(columns, words))
