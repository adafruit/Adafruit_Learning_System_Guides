# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The receiver's screen on the Fruit Jam's DVI output (picodvi, 320x240,
8-bit), or on boards without picodvi (the Metro ESP32-P4) the 2.8" TFT
shield (adsb_tft, the same size): what adsb_receiver.py
needs from a display, the parts the displays share, and the table display.

Displays: TableDisplay (here: a line per aircraft) and
adsb_ui_map.MapDisplay (the aircraft on an OpenStreetMap map, a few
lines below it). open_display('map' | 'table') makes one.

The receiver calls, from its main loop:
    message(text)                  start-up progress
    prepare()                      before the radio starts: slow set-up (map tiles)
    ready()
    show(status, aircraft, now)    about every second; aircraft most recently heard first
    command(action)                a console action; True if the display used it, 'clear'
                                   to have the receiver forget every aircraft (the map's z, y);
                                   asked first: ? shows / hides the help page (HelpPage)
    snapshot(path)                 the screen as a BMP (False: this screen cannot, the TFT)
    screen()                       the text on the screen (for tests)
    close()
The radio waits while the display works (each call costs air time, but
nothing is lost from a stream), so these just should not be slow often.

The table:

    1090 MHz ADS-B  19:31:05Z NTP   heard 7.5%    status
    msgs 123  46.0/min  aircraft 5 log 120
    ICAO   FLIGHT   SQWK    ALT SPD TRK DIST          dB
    A8921D SWA1234  4521  5775. 169 240   23km NE    -18

The aircraft most recently heard first; '*' after the altitude when
climbing, '.' descending; DIST from home (without it, the position as
latitude and longitude); dB: the last message's level (dBFS). Aircraft
not heard for a minute leave the table.

? shows a page of help over everything below the status row (what the
screen shows, then the keys; ? or Esc hides it: HelpPage). While it is
up the display's own keys (the map's) do nothing; the receiver's still
work.
"""
import bitmaptools
import board
import displayio
import framebufferio
import terminalio

import adsb_parse

# pylint: disable=import-outside-toplevel, broad-except

WIDTH = 320
HEIGHT = 240
BACKGROUND = 0x07111D
FOREGROUND = 0xEAF1FA
TABLE_SECONDS = 60
PROMPT = 0xFFE000            # headings on the help page
HELP_TOP = 12                # the help page covers the screen below the status row
HELP_BORDER = 0x3A4A5E
HELP_X = 6
HELP_Y = 6


class Status:
    """What the receiver tells the display."""

    def __init__(self):
        self.utc = ''
        self.clock = 'NO CLOCK'
        self.messages = 0
        self.per_minute = 0.0
        self.heard = 0.0            # % of the air time captured (None: unknown, a replay)
        self.logged = 0
        self.sd = False
        self.reference = None       # home, or the first position heard (adsb_parse.Tracker)
        self.note = None


def open_framebuffer():
    """The 320x240 8-bit (RGB332) DVI framebuffer (picodvi) and its display,
    which only refreshes when told to. Without picodvi: (None, the TFT
    shield's display); the bitmaps' RGB332 palettes work there too."""
    try:
        import picodvi           # (the Fruit Jam's DVI output)
    except ImportError:
        import adsb_tft
        return None, adsb_tft.open_display(WIDTH, HEIGHT)
    displayio.release_displays()
    fb = picodvi.Framebuffer(WIDTH, HEIGHT, clk_dp=board.CKP, clk_dn=board.CKN,
                             red_dp=board.D0P, red_dn=board.D0N,
                             green_dp=board.D1P, green_dn=board.D1N,
                             blue_dp=board.D2P, blue_dn=board.D2N, color_depth=8)
    return fb, framebufferio.FramebufferDisplay(fb, auto_refresh=False)


def snapshot(fb, path):
    """The framebuffer (8-bit RGB332) as a top-down BMP file."""
    from adafruit_maptiles.png import bmp_header
    with open(path, 'wb') as f:
        f.write(bmp_header(WIDTH, HEIGHT))
        f.write(memoryview(fb))


def compass(deg):
    return ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')[int((deg + 22.5) // 45) % 8]


def altitude(a):
    """'5775' and '*' climbing / '.' descending, or 'GND'."""
    if a.ground:
        return 'GND'
    if a.alt is None:
        return ''
    t = '%d' % a.alt
    if a.vr is not None and abs(a.vr) >= 256:
        t += '*' if a.vr > 0 else '.'
    return t


def where(a, home, width=12):
    if a.lat is None:
        return ''
    if home is not None:
        return '%4.0fkm %-2s' % (adsb_parse.distance_km(home, (a.lat, a.lon)),
                                compass(adsb_parse.bearing(home, (a.lat, a.lon))))
    return ('%.2f %.2f' % (a.lat, a.lon))[:width]


def aircraft_row(a, home):
    """One table row (52 characters)."""
    return '%s %-8s %4s %6s %3s %3s %-12s %3s' % (
        a.icao, (a.callsign or '')[:8], a.squawk or '', altitude(a),
        '%d' % a.gs if a.gs is not None else '', '%d' % a.track if a.track is not None else '',
        where(a, home), '%d' % a.signal if a.signal is not None else '')


class TextRows:
    """Rows of terminalio text (6x12 cells) at y in a group. Only rows that
    changed are rewritten; refresh() shows them (one refresh for all)."""

    def __init__(self, display, group, rows, y=0):
        self.display = display
        fw, fh = terminalio.FONT.get_bounding_box()[:2]
        self.columns = WIDTH // fw
        self.rows = rows
        pal = self.palette = displayio.Palette(2)
        pal[0] = BACKGROUND
        pal[1] = FOREGROUND
        grid = displayio.TileGrid(terminalio.FONT.bitmap, pixel_shader=pal, width=self.columns,
                                  height=rows, tile_width=fw, tile_height=fh, y=y)
        self.term = terminalio.Terminal(grid, terminalio.FONT)
        group.append(grid)
        self._shown = {}
        self.fg = FOREGROUND
        self.dirty = False

    def colour(self, colour):
        """The text's colour (0xRRGGBB), for every row."""
        if colour != self.fg:
            self.fg = self.palette[1] = colour
            self.dirty = True

    def row(self, row, text):
        if row >= self.rows:
            return
        # One column short: filling the last column wraps and scrolls.
        text = ('%-*s' % (self.columns - 1, text))[:self.columns - 1]
        if self._shown.get(row) == text:
            return
        self._shown[row] = text
        self.term.write('\x1b[%d;1H%s' % (row + 1, text))
        self.dirty = True

    def refresh(self):
        if self.dirty:
            self.dirty = False
            self.display.refresh(minimum_frames_per_second=0)

    def text(self):
        return [self._shown.get(r, '') for r in range(self.rows)]


def status_rows(st, recent):
    tail = ' log %d' % st.logged if st.sd else ' no SD'
    if st.note:
        tail += ' ' + st.note
    heard = 'heard %.1f%%' % st.heard if st.heard is not None else ''
    return ('1090 MHz ADS-B  %s %-8s %s' % (st.utc, st.clock, heard),
            'msgs %d  %.1f/min  aircraft %d%s' % (st.messages, st.per_minute, len(recent), tail))


HELP_TITLE = [('h', 'HELP'), '%47s' % '? or Esc: close']
HELP_KEYS = [
    [('h', 'KEYS'), '  (serial console or a USB keyboard)'],
    ['#  status   %s  list the aircraft (console)'],
    ['q  quiet / verbose   v  save the screen (SD card)'],
    ['g400 Enter  tuner gain 40.0 dB   g Enter  its AGC'],
]


def help_keys(list_keys):
    """The help page's rows for the receiver's keys (see HelpPage);
    list_keys: the keys that list the aircraft."""
    return HELP_KEYS[:1] + [[HELP_KEYS[1][0] % list_keys]] + HELP_KEYS[2:]


def help_rows():
    """The table's help page."""
    return [
        HELP_TITLE,
        [('h', 'TABLE'), '  the aircraft heard most recently first'],
        ['ICAO  its address   FLIGHT  callsign   SQWK  squawk'],
        ['ALT  feet (* climbing, . descending, GND)'],
        ['SPD  ground speed (knots)   TRK  track (degrees)'],
        ['DIST  from HOME (without it: LAT LON)'],
        ['dB  the last message\'s level (dBFS)'],
        ['Aircraft leave the table %d s after their last' % TABLE_SECONDS],
        ['message. heard (status row): the share of the air'],
        ['time the radio hears (it listens in snapshots).'],
        [],
    ] + help_keys('l or h')


class HelpPage:
    """A page of help over the screen below the status row (? shows and
    hides it, Esc hides it: Display.help_command()). rows: each a list of
    str (text), ('h', text) (a heading), ('dot', colour) (an aircraft's
    square), ('hollow', colour) (one without a recent position), ('ring',
    colour, ring) (a selected one's), ('plane', colour) (its trail, square
    and track line), ('cross', outline, colour) (home) or ('tag', colour,
    text) (a label on colour,
    as the map draws it); colours are 0xRRGGBB. A mark takes two
    character cells (a plane five), a tag one more than its text. A row
    has room for 51 characters, the page for 18 rows.

    The page is drawn once, when the display opens, into its own
    TileGrid, which is hidden until shown. Showing or hiding it is one
    refresh of the screen below the status row (~100 ms, like a map
    redraw: the radio waits)."""

    def __init__(self, display, group, rows):
        self.display = display
        h = HEIGHT - HELP_TOP
        self.bitmap = b = displayio.Bitmap(WIDTH, h, 16)
        self.palette = pal = displayio.Palette(16)
        pal[0] = BACKGROUND
        pal[1] = FOREGROUND          # (terminalio's glyphs are 1)
        self.inks = {}
        bitmaptools.fill_region(b, 0, 0, WIDTH, h, self.ink(HELP_BORDER))
        bitmaptools.fill_region(b, 1, 1, WIDTH - 1, h - 1, self.ink(BACKGROUND))
        for k, row in enumerate(rows):
            self._row(row, HELP_X, HELP_Y + 12 * k)
        self.grid = displayio.TileGrid(b, pixel_shader=pal, y=HELP_TOP)
        self.grid.hidden = True
        group.append(self.grid)
        self.shown = False

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
        if colour is not None:
            v = self.ink(colour)
            for py in range(y, y + 12):
                for px in range(x, x + 6 * len(text)):
                    if b[px, py] == 1:
                        b[px, py] = v

    def _square(self, cx, cy, colour, hollow=False, ring=None):
        """An aircraft as the map draws it: 5x5 in colour, outlined in black
        (and with a ring in ring round it, when selected)."""
        if ring is not None:
            self._fill(cx - 5, cy - 5, cx + 6, cy + 6, ring)
        self._fill(cx - 3, cy - 3, cx + 4, cy + 4, 0)
        self._fill(cx - 2, cy - 2, cx + 3, cy + 3, colour)
        if hollow:
            self._fill(cx - 1, cy - 1, cx + 2, cy + 2, 0)

    def _row(self, row, x, y):
        cy = y + 5                   # (a mark's centre: cx, cy)
        for item in row:
            if isinstance(item, str):
                self._text(item, x, y)
                x += 6 * len(item)
                continue
            kind = item[0]
            if kind == 'h':
                self._text(item[1], x, y, PROMPT)
                x += 6 * len(item[1])
                continue
            cx = x + 5
            if kind == 'tag':
                w = 6 * len(item[2]) + 2
                self._fill(x, y - 1, x + w, y + 13, 0)
                self._fill(x + 1, y, x + w - 1, y + 12, item[1])
                self._text(item[2], x + 1, y, 0)
                x += w + 4
                continue
            if kind == 'plane':
                # its trail from the left, its square, its track line up to the right
                self._fill(x, cy - 2, cx + 12, cy + 2, item[1])
                for k in range(10):
                    self._fill(cx + 13 + k, cy - k // 2, cx + 14 + k, cy - k // 2 + 1, 0)
                    self._fill(cx + 12 + k, cy - 1 - k // 2, cx + 13 + k, cy - k // 2, item[1])
                self._square(cx + 12, cy, item[1])
                x += 30
                continue
            if kind == 'cross':
                self._fill(cx - 6, cy - 2, cx + 7, cy + 3, item[1])
                self._fill(cx - 2, cy - 6, cx + 3, cy + 7, item[1])
                self._fill(cx - 5, cy - 1, cx + 6, cy + 2, item[2])
                self._fill(cx - 1, cy - 5, cx + 2, cy + 6, item[2])
            else:
                self._square(cx, cy, item[1], kind == 'hollow', item[2] if kind == 'ring' else None)
            x += 12

    def show(self, shown):
        """Show (True) or hide the page."""
        self.shown = shown
        self.grid.hidden = not shown
        self.display.refresh(minimum_frames_per_second=0)


class Display:
    """What the receiver calls that a display may not need."""
    NAME = 'none'
    KEYS = ()                    # the display's own keys: they do nothing while the help shows
    needs_pause = False
    help = None                  # the help page (a HelpPage), if the display has one

    def help_command(self, action):
        """? shows or hides the help page, Esc hides it. While it shows,
        the display's own keys (KEYS) do nothing; the receiver's still
        work (the status row stays in view). True if the action was used."""
        page = self.help
        if page is None:
            return False
        if action == '?' or action == 'esc' and page.shown:
            page.show(not page.shown)
            print('HELP', 'shown' if page.shown else 'hidden')
            return True
        return page.shown and action in self.KEYS

    def paused_step(self):
        pass

    def prepare(self):
        pass

    def command(self, action):
        return self.help_command(action)

    def snapshot(self, path):
        if self.fb is None:
            return False         # (an SPI display: its pixels cannot be read back)
        snapshot(self.fb, path)
        return True

    def close(self):
        pass


class TableDisplay(Display):
    NAME = 'table'

    def __init__(self, home=None):
        self.home = home
        self.fb, self.display = open_framebuffer()
        group = displayio.Group()
        self.text = TextRows(self.display, group, HEIGHT // 12)
        self.help = HelpPage(self.display, group, help_rows())
        self.display.root_group = group

    def message(self, text):
        self.text.row(0, '1090 MHz ADS-B')
        self.text.row(2, text)
        self.text.refresh()

    def ready(self):
        self.text.row(2, '')
        self.text.row(3, 'Listening...')
        self.text.refresh()

    def show(self, st, aircraft, now):
        recent = [a for a in aircraft if now - a.seen <= TABLE_SECONDS]
        top = status_rows(st, recent)
        self.text.row(0, top[0])
        self.text.row(1, top[1])
        self.text.row(2, 'ICAO   FLIGHT   SQWK    ALT SPD TRK %-12s  dB'
                      % ('DIST' if self.home else 'LAT LON'))
        for i in range(self.text.rows - 3):
            self.text.row(3 + i, aircraft_row(recent[i], self.home) if i < len(recent) else '')
        self.text.refresh()

    def screen(self):
        return self.text.text()


def open_display(display, home=None, map_centre=None, map_zoom=None):
    """A display, or None. display: 'map', 'table' (True: the map),
    False / None, or a display object."""
    if not display:
        return None
    if not isinstance(display, (str, bool)):
        return display
    try:
        if display == 'table':
            return TableDisplay(home=home)
        from adsb_ui_map import MapDisplay
        return MapDisplay(home=home, centre=map_centre, zoom=map_zoom)
    except Exception as error:
        print('DISPLAY_ERROR', type(error).__name__, error)
        return None
