# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Map display for ft8_receiver.py (display='map'): the FT8 exchanges
heard in the last few minutes, as lines on an OpenStreetMap map between
the two stations' grid squares, on the 320x240 screen (DVI via picodvi on
the Fruit Jam, the TFT shield on the Metro ESP32-P4).

    row 0       status: frequency, band, UTC, clock, exchanges shown, zoom
                (notes: map tiles still to get, NO NET)
    12-179      the map (320x168): a line along the great circle between
                the two stations of each exchange whose grids are known,
                a square on each station, callsign tags for the newest
                exchanges; home (the receiver's grid) as a cross
    180-239     the five newest exchanges: time of the last message (UTC),
                the message, the distance between the stations

An exchange is any message from one call to another (ft8_exchanges.py):
'W5XYZ K1ABC FN42' starts one between K1ABC and W5XYZ, and every later
message between them, either way, keeps it on. Grids come from any
message a station sent one in (its CQ, or its first reply), so a QSO's
reports and 73s are drawn too. A station whose partner's grid is not
known gets a hollow square and no line. Exchanges fall off the map keep
seconds (KEEP_SECONDS, 180) after their last message. Colours by the
age of the last message: red within the last two slots, orange within
90 s, grey after that.

The map is centred on centre=(lat, lon), on home (a grid, e.g. 'EM28'),
or on the first station heard with a grid. Console keys: i or + / o or
- zoom in / out, the arrow keys or w a s d move the map a quarter of the
screen, r fit the stations on the map (no closer than the zoom it
started with; with none: back to the start), v save the screen as
/sd/ft8/screen_NNNN.bmp, z clear the map: the status row asks (in
yellow), y forgets the exchanges (the grids heard stay known), n (or Esc)
keeps them; other keys wait until it is answered. ? shows a page of help
over everything below the status row (what the colours and marks mean,
then the keys and buttons; ? or Esc hides it: ft8_help.HelpPage), a
strip at a time from step(). While it shows, the map's keys do nothing
(but v); the receiver's still work.

Drawing: an adafruit_maptiles MapView (lib/adafruit_maptiles: tiles from
the SD card cache /sd/tiles/osm, shared with the ADS-B and APRS
receivers). Drawing the map and refreshing it takes longer than the USB
ring holds, so while listening it is only done in paused_step(), which
the receiver calls once a slot, late in it (after the transmissions),
with the radio stream stopped, as for its garbage collections. Missing
tiles are downloaded there too, one a slot; a download takes seconds,
so the slot (and the next) is lost. prepare() gets the starting view's
tiles before the radio starts, when the centre is known.
"""
import os
import displayio
import terminalio
from adafruit_maptiles import mercator, rgb332_colour
from adafruit_maptiles.cache import TileCache
from adafruit_maptiles.map_view import BLACK, WHITE, MapView, text_bitmap
import ft8_help
import maidenhead
from ft8_display_dvi import entry_row, open_dvi
from ft8_exchanges import KEEP_SECONDS, Tracker, stamp_seconds

# pylint: disable=too-many-locals, too-many-branches, too-many-return-statements
# pylint: disable=import-outside-toplevel, unsubscriptable-object

USER_AGENT = 'FruitJam-FT8-receiver/1.0 CircuitPython'   # for the tile server
ZOOM = 3                     # ~4800 km across the screen at 40 degrees
ZOOMS = (1, 10)
ZOOM_KEYS = {'i': 1, '+': 1, 'o': -1, '-': -1}
PAN = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1),
       'a': (-1, 0), 'd': (1, 0), 'w': (0, -1), 's': (0, 1)}
PAN_STEP = 0.25              # of the screen, a press
# the map's own (but v): not while the help shows
KEYS = tuple(ZOOM_KEYS) + tuple(PAN) + ('r', 'z')
CLEAR_PROMPT = 'CLEAR THE MAP? y: yes, n: no'
PROMPT = 0xFFE000            # the prompt's colour
AGE_STEP = 15                # s: colours change with the slots: redraw this often
TAGS = 6                     # exchanges (the newest) whose calls get a tag
LINE_KM = 800                # km per straight piece of a great circle line
SCREEN_DIR = '/sd/ft8'

W = 320
H = 240
MAP_TOP = 12
MAP_H = 168
LIST_ROWS = 5
BACKGROUND = 0x07111D
FOREGROUND = 0xEAF1FA

# Colours are RGB332 values.
RED = 0xE0
ORANGE = 0xF0
GREY = 0x92


def colour(age):
    """An exchange's colour by the age of its last message (s)."""
    if age <= 30:
        return RED
    if age <= 90:
        return ORANGE
    return GREY


def hms(t):
    """Seconds since 1970 -> 'HH:MM:SS'."""
    s = int(t) % 86400
    return '%02d:%02d:%02d' % (s // 3600, s // 60 % 60, s % 60)


def mhz(hz):
    """14074000 -> '14.074'."""
    return '%d.%03d' % (hz // 1000000, hz // 1000 % 1000)


def exchange_row(e, tracker):
    """One list row (52 characters at most)."""
    pa, pb = tracker.where(e.a), tracker.where(e.b)
    dist = '%5d km' % int(maidenhead.distance_km(pa, pb)) if pa and pb else ''
    return '%s%s %-34s %s' % ('>' if e.mine else ' ', hms(e.last).replace(':', ''), e.text[:34],
                              dist)


class TextRows:
    """Rows of terminalio text (6x12 cells) at y in a group. Only rows that
    changed are rewritten; refresh() shows them (one refresh for all)."""

    def __init__(self, display, group, rows, y=0):
        self.display = display
        fw, fh = terminalio.FONT.get_bounding_box()[:2]
        self.columns = W // fw
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

    def colour(self, rgb):
        """The text's colour (0xRRGGBB), for every row."""
        if rgb != self.fg:
            self.fg = self.palette[1] = rgb
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


class MapDisplay:
    NAME = 'map'
    OPTIONS = True               # takes the receiver's display_options

    def __init__(self, home=None, centre=None, zoom=None, keep=KEEP_SECONDS, tiles=None,
                 screen=None, views=False):
        """home: your grid; centre: (lat, lon); zoom; keep: seconds an
        exchange stays; tiles: a TileCache; screen: (framebuffer, display)
        to share (ft8_display_dvi.open_dvi()), or None for a new one;
        views: one of several displays on the screen (the help says m / l)."""
        self.home = maidenhead.to_latlon(home) if home else None
        self.start = centre or self.home       # where 'r' goes back to with nothing on the map
        self.zoom_start = zoom or ZOOM
        self.tracker = Tracker(keep=keep)
        self.now = 0                 # the log's UTC (s since 1970), from show()
        self.drawn = None            # (tracker.version, now) at the last drawing
        self.drawn_any = False       # exchanges were on the map then
        self.moved = True            # the view changed: draw again
        self.shot = False            # a screenshot to save at the next paused_step()
        self.paths = {}              # (grid, grid) -> great circle as (lon, Mercator y) points
        self.tags = {}               # call -> its tag bitmap
        self.last_prune = 0
        self.status = 'FT8 map'      # the status row, without the map's notes
        self.typing = None           # a console command being typed, shown over it (entry())
        self.asking = False          # z: the status row asks whether to clear the map
        self.fb, self.display = screen or open_dvi()
        self.group = group = displayio.Group()
        self.top = TextRows(self.display, group, 1)
        self.map = MapView(W, MAP_H, self.start, self.zoom_start, y=MAP_TOP, zooms=ZOOMS,
                           cache=tiles or TileCache(user_agent=USER_AGENT))
        group.append(self.map)
        self.list = TextRows(self.display, group, LIST_ROWS, y=MAP_TOP + MAP_H)
        self.help = ft8_help.HelpPage(self.display, group, ft8_help.map_rows(
            [rgb332_colour(c) for c in (RED, ORANGE, GREY)], keep, views))
        self.display.root_group = group
        if self.map.centre is None:
            self.map.redraw()        # (no tiles: the 'waiting' grey)
        self.display.refresh(minimum_frames_per_second=0)

    # ---------------------------------------------------------- drawing

    def _tag(self, call):
        b = self.tags.get(call)
        if b is None:
            if len(self.tags) > 60:
                self.tags = {}
            b = self.tags[call] = text_bitmap(call, WHITE, outline=True)
        return b

    def _near(self, lon):
        """lon, moved by 360 degrees to the copy of the world nearest the
        map's centre."""
        return self.map.clon + (lon - self.map.clon + 180) % 360 - 180

    def _path(self, ga, gb, pa, pb):
        key = (ga, gb)
        p = self.paths.get(key)
        if p is None:
            if len(self.paths) > 300:
                self.paths = {}
            n = min(16, 1 + int(maidenhead.distance_km(pa, pb) / LINE_KM))
            p = self.paths[key] = [(lon, mercator(lat))
                                   for lat, lon in maidenhead.great_circle(pa, pb, n)]
        return p

    def _line(self, path, c):
        """A great circle path, 2 pixels wide."""
        v = self.map
        shift = self._near(path[len(path) // 2][0]) - path[len(path) // 2][0]
        k = v.world / 360
        cx, cy = v.width // 2 - (v.clon - shift) * k, v.height // 2 - v.cmerc * v.world
        px = py = None
        for lon, my in path:
            x, y = round(cx + lon * k), round(cy + my * v.world)
            if px is not None:
                if abs(x - px) >= abs(y - py):
                    v.line(px, py, x, y, c)
                    v.line(px, py + 1, x, y + 1, c)
                else:
                    v.line(px, py, x, y, c)
                    v.line(px + 1, py, x + 1, y, c)
            px, py = x, y

    def _draw(self):
        v = self.map
        v.restore()
        now = self.now
        shown = self.tracker.current(now)
        if self.home:
            v.cross(*v.xy(self.home[0], self._near(self.home[1])))
        # Oldest first: the newest on top.
        dots = []
        for e in reversed(shown):
            c = colour(now - e.last)
            pa, pb = self.tracker.where(e.a), self.tracker.where(e.b)
            if pa and pb:
                self._line(self._path(self.tracker.grid(e.a), self.tracker.grid(e.b), pa, pb), c)
            for p in (pa, pb):
                if p:
                    dots.append((v.xy(p[0], self._near(p[1])), c, not (pa and pb)))
        for (x, y), c, hollow in dots:
            v.fill(x - 3, y - 3, x + 4, y + 4, BLACK)
            v.fill(x - 2, y - 2, x + 3, y + 3, c)
            if hollow:
                v.fill(x - 1, y - 1, x + 2, y + 2, BLACK)
        # Tags: the newest exchanges' calls, where they do not cover another tag.
        placed = []
        tagged = set()
        for e in shown[:TAGS]:
            for call in (e.sender, e.to):
                p = self.tracker.where(call)
                if p is None or call in tagged:
                    continue
                x, y = v.xy(p[0], self._near(p[1]))
                if not (0 <= x < W and 0 <= y < MAP_H):
                    continue
                t = self._tag(call)
                lx = x + 5 if x + 5 + t.width <= W else x - 5 - t.width
                r = (lx, y - 7, lx + t.width, y + 7)
                if any(r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3] for q in placed):
                    continue
                placed.append(r)
                tagged.add(call)
                v.blit(t, lx, y - 7)
        v.draw_legend()
        v.dirty()
        self.drawn = (self.tracker.version, now)
        self.drawn_any = bool(shown)
        self.moved = False

    def _status_row(self):
        note = ' z%d' % self.map.zoom
        if self.map.missing:
            note += ' map %d' % len(self.map.missing)
        if self.map.net_error:
            note += ' NO NET'
        if self.typing is not None:
            text = entry_row(self.typing)
        else:
            text = CLEAR_PROMPT if self.asking else self.status + note
        self.top.colour(PROMPT if self.asking and self.typing is None else FOREGROUND)
        self.top.row(0, text)

    # ------------------------------------------------------ receiver calls

    @property
    def needs_pause(self):
        """True when the map has work that must wait for the radio to pause
        (paused_step())."""
        if self.map.missing or self.map.loading or self.shot:
            return True
        if self.map.centre is None:
            return False
        return (self.moved or self.drawn is None or self.drawn[0] != self.tracker.version
                or self.drawn_any and self.now - self.drawn[1] >= AGE_STEP)

    def paused_step(self):
        """The slow work, with the radio paused: one missing tile (seconds),
        the map's tiles, the exchanges drawn over them, the screenshot."""
        if self.map.missing:
            self.map.fetch_step()
        self.map.load()
        if self.map.centre is not None:
            self._draw()
        self._status_row()
        # (one refresh for the map and the text)
        self.display.refresh(minimum_frames_per_second=0)
        self.top.dirty = self.list.dirty = False
        if self.shot:
            self.shot = False
            self._save_screen()

    def prepare(self):
        """Before the radio starts: every missing tile of the starting view."""
        total = len(self.map.missing)
        while self.map.missing:
            self.message('Map: tile %d of %d (download, convert)'
                         % (total - len(self.map.missing) + 1, total))
            self.map.fetch_step()
        self.message('Map: loading the tiles')
        self.paused_step()

    def command(self, action):
        """A console action; True if it was the map's."""
        v = self.map
        if self.asking:
            # (clear the map? y or n answers; other keys are ignored until then)
            if action == 'y':
                self.tracker.clear()
            if action in ('y', 'n', 'esc'):
                self.asking = False
                self._status_row()
                self.top.refresh()
            return True
        if self.help.command(action, KEYS):
            return True
        if action == 'z':
            self.asking = True
            self._status_row()
            self.top.refresh()
            return True
        if action in ZOOM_KEYS:
            if v.zoom_in() if ZOOM_KEYS[action] > 0 else v.zoom_out():
                self.moved = True
            return True
        if action == 'r':
            points = [p for e in self.tracker.current(self.now)
                      for p in (self.tracker.where(e.a), self.tracker.where(e.b)) if p]
            if self.home:
                points.append(self.home)
            if points:
                # (around the copy of the world nearest the first one)
                lon0 = points[0][1]
                v.fit([(lat, lon0 + (lon - lon0 + 180) % 360 - 180) for lat, lon in points],
                      self.zoom_start)
            elif self.start:
                v.set_view(self.start, self.zoom_start)
            self.moved = True
            return True
        if action in PAN:
            if v.centre is not None:
                dx, dy = PAN[action]
                v.pan(dx * PAN_STEP, dy * PAN_STEP)
                self.moved = True
            return True
        if action == 'v':
            self.shot = True
            return True
        return False

    def step(self):
        """Idle time: a strip of the help page shown or hidden; True if
        there was one."""
        return self.help.step()

    def add_decode(self, d, my_call=''):
        """A decode (a dict from ft8_receiver.results)."""
        t = stamp_seconds(d['t'])
        self.now = max(self.now, t)
        e = self.tracker.add(d['text'], t, my_call)
        if e is not None and self.map.centre is None:
            p = self.tracker.where(e.a) or self.tracker.where(e.b)
            if p:
                self.map.centre = p
                self.start = p
                self.moved = True

    def learn(self, d, my_call=''):
        """A decode from before a log replay's start (the grids and the
        exchanges a listener would have heard by then): as add_decode()."""
        self.add_decode(d, my_call)

    def show(self, st):
        """The receiver's status (an ft8_receiver.Status); about once a second."""
        self.now = st.utc_s
        if self.now - self.last_prune >= AGE_STEP:
            self.last_prune = self.now
            self.tracker.prune(self.now)
        shown = self.tracker.current(self.now)
        self.status = '%s %s %s %s %d QSO%s%s' % (mhz(st.dial), st.label[:6], st.utc, st.clock,
                                                  len(shown), '' if len(shown) == 1 else 's',
                                                  ' ' + st.note if st.note else '')
        self._status_row()
        for i in range(LIST_ROWS):
            self.list.row(i, exchange_row(shown[i], self.tracker) if i < len(shown) else '')
        self.top.refresh()
        self.list.refresh()

    def entry(self, text):
        """A console command being typed, on the status row (None: done)."""
        self.typing = text
        self._status_row()
        self.top.refresh()

    def message(self, text):
        self._status_row()
        self.list.row(0, text)
        self.top.refresh()
        self.list.refresh()

    def connecting(self):
        self.message('CONNECTING: looking for the USB receiver')

    def ready(self):
        self.list.row(0, 'Listening: exchanges appear after each 15 s slot')
        self.list.refresh()

    def screen(self):
        """The text on the screen, row by row (for tests)."""
        return self.top.text() + self.list.text()

    def _save_screen(self):
        """The framebuffer (8-bit RGB332) as a top-down BMP, the next free
        SCREEN_DIR/screen_NNNN.bmp."""
        if self.fb is None:
            # (an SPI display: its pixels cannot be read back)
            print('NO_SCREENSHOT', 'this screen cannot be saved')
            return
        from adafruit_maptiles.png import bmp_header
        try:
            names = os.listdir(SCREEN_DIR)
            k = 0
            while 'screen_%04d.bmp' % k in names:
                k += 1
            path = '%s/screen_%04d.bmp' % (SCREEN_DIR, k)
            with open(path, 'wb') as f:
                f.write(bmp_header(W, H))
                f.write(memoryview(self.fb))
            print('SCREENSHOT', path)
        except OSError as error:
            print('SCREENSHOT_ERROR', error)

    def close(self):
        self.map.close()
