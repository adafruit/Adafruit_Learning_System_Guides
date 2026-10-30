# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The receiver's screen: what aprs_receiver.py needs from a display, and
the parts the two displays share (the 320x240 screen, rows of text, the
status, packet summaries). The screen is the Fruit Jam's DVI output
(picodvi, 8-bit), or on boards without picodvi (the Metro ESP32-P4) the
2.8" TFT shield (aprs_tft, the same size).

Displays: aprs_ui_text.TextDisplay (packets as lines of text) and
aprs_ui_map.MapDisplay (stations on a map, the newest packets below it).
open_display('map' | 'text') makes one.

The receiver calls, all from its main loop:

    message(text), connecting(), ready()   start-up progress
    prepare()                     before the radio stream starts: slow set-up
    show(status)                  about once a second (a Status)
    add_packet(p, hhmm)           a decoded packet (aprs_parse dict), not a repeat
    step()                        idle time: one short piece of work; True if it did any
    needs_pause                   True when work is waiting that has to run with
                                  the stream paused (paused_step(), when the channel is quiet)
    command(action)               a console / button action; True if the display used it
                                  (asked first: the display's keys win over the receiver's;
                                  ? shows / hides the help page, see HelpPage)
    entry(text)                   a console command being typed ('f144.39', 'c1'), shown on
                                  the status row (entry_row()) until entry(None)
    LONG_PRESS                    actions for long presses of B1, B2, B3 (None: as short presses)
    snapshot(path)                the screen as a BMP (stream paused; False: this
                                  screen cannot, the TFT)
    screen()                      the text on the screen (for tests)
    close()

Each call has to come back quickly (well under the USB ring's 64-128 ms):
a full-screen refresh takes ~100 ms, so a display only ever redraws
part of the screen at a time.
"""
import math
import board
import bitmaptools
import displayio
import framebufferio
import terminalio
import aprs_parse

# pylint: disable=import-outside-toplevel, broad-except

WIDTH = 320
HEIGHT = 240
BACKGROUND = 0x07111d
FOREGROUND = 0xeaf1fa
PROMPT = 0xffe000            # a question on the status row (asking)
HELP_TOP = 12                # the help page covers the screen below the status row
HELP_STRIP = 12              # px: it is shown / hidden this many rows at a time
HELP_BORDER = 0x3a4a5e
HELP_X = 6
HELP_Y = 6


def format_frequency(hz):
    """144390000 -> '144.390 MHz' (1 kHz resolution)."""
    hz = int(hz)
    return '%d.%03d MHz' % (hz // 1000000, hz // 1000 % 1000)


class Status:
    """What the display shows. The receiver keeps it up to date and calls
    ui.show(status); the display formats it."""

    def __init__(self):
        self.dial = 0               # Hz; None: not known (a replay)
        self.label = ''
        self.utc = ''               # 'HH:MM:SSZ'
        self.clock = 'NO CLOCK'
        self.level = -99.0          # dB; None: not known (a replay)
        self.dcd = False            # a packet is coming in (HDLC flags seen)
        self.packets = 0
        self.stations = 0
        self.muted = False
        self.sd = False
        self.logged = 0
        self.note = None


def entry_row(text):
    """The status row while a console command is typed: text is 'f' and
    a frequency or 'c' and a preset number, as typed so far."""
    if text[:1] == 'f':
        return 'TUNE TO %s_  MHz or kHz, Enter; Esc cancels' % text[1:].strip()
    return 'GO TO PRESET %s_  Enter (none: list them)' % text[1:].strip()


def distance(lat, lon, home):
    """(km, compass point) from home to lat, lon."""
    p1, p2 = math.radians(home[0]), math.radians(lat)
    dl = math.radians(lon - home[1])
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    km = 12742 * math.asin(min(1, math.sqrt(a)))
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    brg = math.degrees(math.atan2(y, x))
    points = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')
    return km, points[int((brg + 382.5) // 45) % 8]


def packet_row(p, hhmm, home, width):
    """(hh:mm, source, summary) for the screen."""
    text = aprs_parse.summary(p, max(80, width))
    if home and 'lat' in p:
        km, point = distance(p['lat'], p['lon'], home)
        # The summary's position is its first lat/lon part: replace it.
        pos = '%.3f%s %.3f%s' % (abs(p['lat']), 'N' if p['lat'] >= 0 else 'S',
                                 abs(p['lon']), 'E' if p['lon'] >= 0 else 'W')
        text = text.replace(pos, '%.0fkm %s' % (km, point), 1)
    return hhmm, p['src'][:9], text[:width]


def open_framebuffer():
    """The 320x240 8-bit (RGB332) DVI framebuffer (picodvi) and its display, which
    only refreshes when told to. Without picodvi: (None, the TFT shield's
    display); the bitmaps' RGB332 palettes work there too."""
    try:
        import picodvi           # (the Fruit Jam's DVI output)
    except ImportError:
        import aprs_tft
        return None, aprs_tft.open_display(WIDTH, HEIGHT)
    displayio.release_displays()
    fb = picodvi.Framebuffer(WIDTH, HEIGHT, clk_dp=board.CKP, clk_dn=board.CKN,
        red_dp=board.D0P, red_dn=board.D0N, green_dp=board.D1P, green_dn=board.D1N,
        blue_dp=board.D2P, blue_dn=board.D2N, color_depth=8)
    return fb, framebufferio.FramebufferDisplay(fb, auto_refresh=False)


def snapshot(fb, path):
    """The framebuffer (8-bit RGB332) as a top-down BMP file."""
    from adafruit_maptiles.png import bmp_header
    with open(path, 'wb') as f:
        f.write(bmp_header(WIDTH, HEIGHT))
        f.write(memoryview(fb))


class TextRows:
    """Rows of terminalio text (6x12 cells) at y in the display's group.
    Only rows that changed are rewritten (about 7 ms each)."""

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

    def row(self, row, text):
        """Rewrite one row if it changed."""
        if row >= self.rows:
            return
        # One column short of the width: filling the last row wraps the
        # cursor, which scrolls the terminal and blanks that row.
        text = ('%-*s' % (self.columns - 1, text))[:self.columns - 1]
        if self._shown.get(row) == text:
            return
        self._shown[row] = text
        self.term.write('\x1b[%d;1H%s' % (row + 1, text))
        self.display.refresh(minimum_frames_per_second=0)

    def colour(self, colour):
        """The text's colour (0xRRGGBB); redraws all the rows when it changes."""
        if self.palette[1] != colour:
            self.palette[1] = colour
            self.display.refresh(minimum_frames_per_second=0)

    def text(self):
        return [self._shown.get(r, '') for r in range(self.rows)]


def help_keys(list_presets):
    """The help page's rows for the receiver's keys (see HelpPage);
    list_presets: the key that lists the presets."""
    return [
        [('h', 'RADIO')],
        ['. ,  or n p  next / previous preset   1-9  preset'],
        ['f144.39 Enter  tune there   [ ]  5 kHz down / up'],
        ['c<n> Enter  preset n, from 0   %s  list them' % list_presets],
        ['x  mute   # status, h  stations heard (console)'],
        ['u  save 20 s of audio   v  save the screen (SD)'],
    ]


HELP_TITLE = [('h', 'HELP'), '%47s' % '? or Esc: close']
HELP_BUTTONS = [('h', 'BUTTONS'), '  B1 previous preset  B2 mute  B3 next']


class HelpPage:
    """A page of help over the screen below the status row (? shows and
    hides it, Esc hides it: Display.help_command()). rows: each a list of
    str (text), ('h', text) (a heading), ('dot', colour) (a station's
    dot), ('ring', colour, ring) (a selected station's), ('cross',
    outline, colour) (home), ('box', colour) (a square) or ('tag',
    colour, text) (a call on colour, as the map draws it); colours are
    0xRRGGBB. A mark takes two character cells, a tag one more than its
    text. A row has room for 51 characters, the page for 18 rows.

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
        if colour is not None:
            v = self.ink(colour)
            for py in range(y, y + 12):
                for px in range(x, x + 6 * len(text)):
                    if b[px, py] == 1:
                        b[px, py] = v

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
            if kind == 'cross':
                self._fill(cx - 5, cy - 2, cx + 6, cy + 3, item[1])
                self._fill(cx - 2, cy - 5, cx + 3, cy + 6, item[1])
                self._fill(cx - 4, cy - 1, cx + 5, cy + 2, item[2])
                self._fill(cx - 1, cy - 4, cx + 2, cy + 5, item[2])
            elif kind == 'box':
                self._fill(cx - 5, cy - 5, cx + 6, cy + 6, 0)
                self._fill(cx - 4, cy - 4, cx + 5, cy + 5, item[1])
            else:
                if kind == 'ring':
                    self._fill(cx - 5, cy - 5, cx + 6, cy + 6, item[2])
                self._fill(cx - 3, cy - 3, cx + 4, cy + 4, 0)
                self._fill(cx - 2, cy - 2, cx + 3, cy + 3, item[1])
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


class Display:
    """What the receiver calls that a display may not need."""
    NAME = 'none'
    LONG_PRESS = None
    KEYS = ()                    # the display's own keys: they do nothing while the help shows
    needs_pause = False
    status_text = ''             # the first status row, from show()
    typing = None                # a command being typed, shown over it (entry())
    asking = None                # a y / n question shown over it (the map's z)
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

    def entry(self, text):
        """A console command being typed (None: done; the status back)."""
        self.typing = text
        self.status_row(self.status_text)

    def status_row(self, text):
        """The first status row: text, or the command being typed, or the
        question being asked."""
        self.status_text = text
        if self.typing is not None:
            text = entry_row(self.typing)
        elif self.asking:
            text = self.asking
        self.top.colour(PROMPT if self.asking and self.typing is None else FOREGROUND)
        self.top.row(0, text)

    def prepare(self):
        pass

    def step(self):
        return self.help is not None and self.help.step()

    def paused_step(self):
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


def open_display(display, home=None, map_centre=None, map_zoom=None):
    """A display, or None. display: 'map', 'text' (or True: the map),
    False / None, or a display object."""
    if not display:
        return None
    if not isinstance(display, (str, bool)):
        return display
    try:
        if display == 'text':
            from aprs_ui_text import TextDisplay  # pylint: disable=cyclic-import
            return TextDisplay(home=home)
        from aprs_ui_map import MapDisplay  # pylint: disable=cyclic-import
        return MapDisplay(home=home, centre=map_centre, zoom=map_zoom)
    except Exception as error:
        print('DISPLAY_ERROR', type(error).__name__, error)
        return None
