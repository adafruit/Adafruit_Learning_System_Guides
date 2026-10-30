# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The help page for ft8_receiver.py's displays: ? shows a page over the
screen below the status row (what the screen shows, then the keys and
buttons), ? again or Esc hides it. While it shows, the display's own keys
(the map's) do nothing; the receiver's still work (the status row stays
in view).

The page is drawn once, when the display opens (before the radio
starts), and shown or hidden a 12-pixel strip at a time from the
display's step(), which the receiver calls when the USB stream is idle:
a full-screen refresh takes longer than the USB ring holds.

text_rows() is the page of the text displays (ft8_display_dvi and
ft8_display_color), map_rows() the map's (ft8_display_map); views: the
display is one of several on the screen (ft8_display_views: m or l shows
the next).
"""
import bitmaptools
import displayio
import terminalio

WIDTH = 320
HEIGHT = 240
BACKGROUND = 0x07111d
FOREGROUND = 0xeaf1fa
PROMPT = 0xffe000            # headings
HELP_TOP = 12                # the page covers the screen below the status row
HELP_STRIP = 12              # px: it is shown / hidden this many rows at a time
HELP_BORDER = 0x3a4a5e
HELP_X = 6
HELP_Y = 6
BLACK = 0x000000
WHITE = 0xffffff

TITLE = [('h', 'HELP'), '%47s' % '? or Esc: close']
RADIO = [
    [('h', 'RADIO')],
    ['. ,  or n p  next / previous preset   1-9  preset'],
    ['f14.074 Enter  tune there   [ ]  500 Hz down / up'],
    ['c<n> Enter  preset n, from 0   c Enter  list them'],
    ['x  mute   t  read the clock again   #  status'],
    ['u  save each slot\'s audio on / off (SD card)'],
]
VIEWS = [('h', 'VIEWS'), '  m or l  the next view']
# (two rows: the Metro ESP32-P4 has no buttons)
BUTTONS = [
    [('h', 'BUTTONS'), '  (Fruit Jam only)'],
    ['B1 previous preset  B2 mute  B3 next'],
]


def text_rows(colour=False, views=False):
    """The text displays' page; colour: the color display's (each call
    in its own colour)."""
    if colour:
        grey, a, b = 0x8a96a8, 0xffff00, 0x496dff     # (ft8_display_color's)
    else:
        grey = a = b = FOREGROUND
    rows = [
        TITLE,
        [('h', 'DECODES'), '  after each 15 s slot, the newest above'],
        ['the blank row (new ones go over the oldest):'],
        [' ', ('c', grey, '141715  -7  0.1 1059'), ' ', ('c', a, 'TJ1GD'), '       ',
         ('c', b, 'XE1RK'), '       EK09'],
        ['slot (UTC), SNR dB, DT s, audio Hz, message'],
        ['> at the start: a message to or from MY_CALL'],
    ]
    if colour:
        rows.append(['Each call keeps its color; ', ('tag', WHITE, 'MY_CALL'), 'inverted'])
    return rows + [[]] + RADIO + [[]] + ([VIEWS] if views else []) + BUTTONS


def map_rows(colours, keep, views=False):
    """The map's page. colours: (new, recent, old) exchange colours
    (0xRRGGBB); keep: seconds an exchange stays on the map."""
    new, recent, old = colours
    return [
        TITLE,
        [('h', 'MAP'), '  the exchanges, by their last message:'],
        [('line', new), ' 30 s  ', ('line', recent), ' 90 s  ', ('line', old), ' older  ',
         ('cross', WHITE, BLACK), ' home'],
        [('hollow', new), ' the other station\'s grid is not known'],
        [('tag', WHITE, 'K1ABC'), 'the newest exchanges\' calls; they go'],
        ['%d min after their last message. Below: the five' % (keep // 60)],
        ['newest (time, last message, km between them).'],
    ] + RADIO + [
        [('h', 'MAP'), '  i + / o -  zoom   arrows or w a s d  move'],
        ['r  fit the stations   v  save the screen (SD)'],
        ['z  clear the map (y / n)' + ('   m or l  the next view' if views else '')],
    ] + BUTTONS


class HelpPage:
    """A page of help over the screen below the status row. rows: each a
    list of str (text), ('h', text) (a heading), ('c', colour, text)
    (text in colour), ('tag', colour, text) (a call on colour, as the map
    draws it), ('cross', outline, colour) (home), ('line', colour) (an
    exchange: two stations and the line between them) or ('hollow',
    colour) (a station without its partner's grid); colours are
    0xRRGGBB. A mark takes two character cells (a line five), a tag one
    more than its text. A row has room for 51 characters, the page for
    18 rows.

    The page is drawn once, into the top of a bitmap with a transparent
    strip below it. A TileGrid of strips shows it: each tile is either
    the page's own strip or the transparent one, and step() changes one,
    so showing or hiding it never refreshes the whole screen."""

    def __init__(self, display, group, rows):
        self.display = display
        self.strips = (HEIGHT - HELP_TOP) // HELP_STRIP
        h = self.strips * HELP_STRIP
        self.bitmap = b = displayio.Bitmap(WIDTH, h + HELP_STRIP, 16)
        self.palette = pal = displayio.Palette(16)
        pal.make_transparent(0)
        pal[1] = FOREGROUND          # (terminalio's glyphs are 1)
        self.inks = {}
        bitmaptools.fill_region(b, 0, 0, WIDTH, h, self.ink(HELP_BORDER))
        bitmaptools.fill_region(b, 1, 1, WIDTH - 1, h - 1, self.ink(BACKGROUND))
        for k, row in enumerate(rows):
            self._row(row, HELP_X, HELP_Y + 12 * k)
        self.grid = displayio.TileGrid(b, pixel_shader=pal, width=1, height=self.strips,
                                       tile_width=WIDTH, tile_height=HELP_STRIP,
                                       default_tile=self.strips, y=HELP_TOP)
        group.append(self.grid)
        self.shown = False
        self.todo = []               # strips to show or hide

    def ink(self, colour):
        """The palette index for 0xRRGGBB."""
        k = self.inks.get(colour)
        if k is None:
            k = len(self.inks) + 2
            if k >= 16:
                raise ValueError('the help page has too many colours')
            self.inks[colour] = k
            self.palette[k] = colour
        return k

    def _fill(self, x1, y1, x2, y2, colour):
        bitmaptools.fill_region(self.bitmap, x1, y1, x2, y2, self.ink(colour))

    def _text(self, text, x, y, colour=None):
        """text at x, y (terminalio's font) in colour (None: FOREGROUND)."""
        b = self.bitmap
        for k, ch in enumerate(text):
            glyph = terminalio.FONT.get_glyph(ord(ch))
            if glyph:
                g = glyph.tile_index * 6
                bitmaptools.blit(b, terminalio.FONT.bitmap, x + 6 * k, y,
                                 x1=g, y1=0, x2=g + 6, y2=12, skip_source_index=0)
        if colour is not None and colour != FOREGROUND:
            v = self.ink(colour)
            for py in range(y, y + 12):
                for px in range(x, x + 6 * len(text)):
                    if b[px, py] == 1:
                        b[px, py] = v

    def _square(self, cx, cy, colour, hollow=False):
        """A station as the map draws it: 5x5 in colour, outlined in black."""
        self._fill(cx - 3, cy - 3, cx + 4, cy + 4, BLACK)
        self._fill(cx - 2, cy - 2, cx + 3, cy + 3, colour)
        if hollow:
            self._fill(cx - 1, cy - 1, cx + 2, cy + 2, BLACK)

    def _row(self, row, x, y):
        cy = y + 5                   # (a mark's centre: cx, cy)
        for item in row:
            if isinstance(item, str):
                self._text(item, x, y)
                x += 6 * len(item)
                continue
            kind = item[0]
            if kind in ('h', 'c'):
                text = item[-1]
                self._text(text, x, y, PROMPT if kind == 'h' else item[1])
                x += 6 * len(text)
                continue
            cx = x + 5
            if kind == 'tag':
                w = 6 * len(item[2]) + 2
                self._fill(x, y - 1, x + w, y + 13, BLACK)
                self._fill(x + 1, y, x + w - 1, y + 12, item[1])
                self._text(item[2], x + 1, y, BLACK)
                x += w + 4
                continue
            if kind == 'line':
                self._fill(cx, cy - 1, cx + 19, cy + 1, item[1])
                self._square(cx, cy, item[1])
                self._square(cx + 18, cy, item[1])
                x += 30
                continue
            if kind == 'cross':
                # (13 pixels across, as adafruit_maptiles' MapView.cross())
                self._fill(cx - 6, cy - 2, cx + 7, cy + 3, item[1])
                self._fill(cx - 2, cy - 6, cx + 3, cy + 7, item[1])
                self._fill(cx - 5, cy - 1, cx + 6, cy + 2, item[2])
                self._fill(cx - 1, cy - 5, cx + 2, cy + 6, item[2])
            else:
                self._square(cx, cy, item[1], kind == 'hollow')
            x += 12

    def show(self, shown):
        """Show (True) or hide the page, a strip per step()."""
        self.shown = shown
        self.todo = list(range(self.strips))

    def step(self):
        """One strip shown or hidden; False when there is none to do."""
        if not self.todo:
            return False
        k = self.todo.pop(0)
        self.grid[0, k] = k if self.shown else self.strips
        self.display.refresh(minimum_frames_per_second=0)
        return True

    def command(self, action, keys=()):
        """? shows or hides the page, Esc hides it. While it shows, keys
        (the display's own) do nothing. True if the action was used."""
        if action == '?' or action == 'esc' and self.shown:
            self.show(not self.shown)
            print('HELP', 'shown' if self.shown else 'hidden')
            return True
        return self.shown and action in keys
