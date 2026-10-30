# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Map display for aprs_receiver.py: the stations heard, on an
OpenStreetMap map, on the 320x240 screen (DVI via picodvi on the Fruit
Jam, the TFT shield on the Metro ESP32-P4).

    row 0       status: frequency, preset, UTC, level, DCD, packets,
                stations, zoom, notes
    12-203      the map (320x192): a dot per station (red: vehicles,
                green: digipeaters, gateways, houses; blue: weather;
                magenta: objects; orange: the rest) with its call
                (for 30 min; the station goes after 60 min unheard);
                the newest one's call on yellow; home as a cross; a
                scale bar and the tiles' credit at the bottom
    204-239     the last three packets as text

The map is centred on home, on centre=(lat, lon), or on the first
position heard. Console: i or + / o or - zoom in / out, the arrow keys
or w a s d move the map a quarter of the screen, r fit the stations on
the map (centred on them, the closest zoom that shows them all, but no
closer than the zoom the map started with; with none: back to home or
the starting centre), k / l select the next / previous station on the map
(newest heard first; past either end: none), whose call is then drawn on
cyan over everything, with a cyan ring round its dot; the rows below the
map then show its latest packet in full, in cyan (the packet list only
has room for the first 36 characters of each). Esc deselects (back to
the packet list). z clears the map: the status row asks (in yellow), y
forgets every station and the packets below the map, n (or Esc) keeps
them; other keys wait until it is answered. Long presses: B1 zoom out,
B2 fit (as r), B3 zoom in. ? shows a page of help over everything below
the status row: what the colours mean, then the keys and buttons (? or
Esc hides it; the map's keys do nothing while it shows, the receiver's
still work).

Drawing: the map is one 8-bit bitmap in the framebuffer's own colours
(RGB332), over a second one with just the tiles (the underlay). Tiles
come from aprs_tiles' cache as BMPs in the same colours, read a strip of
rows at a time into the underlay. Redrawing a rectangle copies it back
from the underlay, then draws what overlaps it (station dots, their
calls, home, scale bar, credit; the calls are pre-drawn small bitmaps).
add_packet() only notes what changed; step() then redraws one strip,
rectangle or text row at a time (each 5-15 ms): refreshing the whole
screen takes ~100 ms, longer than the receiver can leave the USB
stream. Tiles not on the SD card yet are downloaded and converted with
the stream paused (paused_step, one tile at a time while the channel is
quiet); until then they are grey.
"""
import json
import time
import bitmaptools
import displayio
import terminalio
import aprs_tiles
import aprs_ui
from aprs_tiles import BMP_HEADER, TILE, mercator, unmercator, world_x, world_y
from aprs_ui import packet_row

# pylint: disable=too-many-locals, too-many-branches, too-many-return-statements
# pylint: disable=too-many-nested-blocks, broad-except

TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
TILE_DIR = '/sd/tiles/osm'
CREDIT = '(C) OpenStreetMap contributors'
ZOOM = 9                     # ~75 km across the screen at 40 degrees
ZOOMS = (3, 15)
ZOOM_KEYS = {'i': 1, '+': 1, 'o': -1, '-': -1}
PAN = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1),
       'a': (-1, 0), 'd': (1, 0), 'w': (0, -1), 's': (0, 1)}
PAN_STEP = 0.25              # of the screen, a press
FIT_MARGIN = 24              # px: r keeps the stations this far inside the map
MAP_KEYS = tuple(ZOOM_KEYS) + tuple(PAN) + ('r', 'k', 'l', 'z')    # (and Esc: deselect)
CLEAR_PROMPT = 'CLEAR THE MAP? y: yes, n: no'

W = aprs_ui.WIDTH
MAP_TOP = 12
MAP_H = 192
LIST_ROWS = 3
STRIP = 8                    # map rows loaded per step
MAX_STATIONS = 60
LABEL_SECONDS = 1800         # calls are shown for stations heard this recently
KEEP_SECONDS = 3600          # stations not heard this long fall off the map

# Colours are RGB332 values.
BLACK = 0x00
WHITE = 0xff                 # (terminalio's font draws its value 1: dark blue)
YELLOW = 0xfc
NO_TILE = 0xb6
WAITING = 0x49
RED = 0xe0
GREEN = 0x14
BLUE = 0x0b
MAGENTA = 0xe3
ORANGE = 0xf4
CYAN = 0x1f
DETAIL = 0x40ffff            # the selected station's packet, below the map
MOBILE = ">kjuvUbR<sYafX^'OPe=CF"
FIXED = '#&-rnyzm'


def marker_colour(p):
    if p.get('type') in ('object', 'item'):
        return MAGENTA
    sym = p.get('sym') or '  '
    if sym[1:] == '_' or p.get('wx'):
        return BLUE
    if sym[1:] and sym[1] in FIXED:
        return GREEN
    if sym[1:] and sym[1] in MOBILE:
        return RED
    return ORANGE


def wrap(text, width, rows):
    """text in rows of at most width characters, broken at spaces where
    it can be; '>' at the end if it does not all fit."""
    out = []
    while text and len(out) < rows:
        if len(text) <= width:
            out.append(text)
            text = ''
            break
        cut = text.rfind(' ', 0, width + 1)
        if cut < width // 2:
            cut = width
        out.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        out[-1] = out[-1][:width - 1] + '>'
    return out + [''] * (rows - len(out))


def detail(p, hhmm, home):
    """All of a packet that the screen shows: its summary, untruncated,
    then course, altitude and path."""
    text = '%s %-9s %s' % packet_row(p, hhmm, home, 1000)
    if p.get('course'):
        text += ' course %d' % p['course']
    if p.get('alt') is not None:
        text += ' alt %dm' % p['alt']
    if p.get('path'):
        text += ' via ' + ','.join(p['path'])
    return text


def help_rows():
    """The help page (aprs_ui.HelpPage): the map's colours, then the keys."""
    c = aprs_tiles.rgb332_colour
    return [
        aprs_ui.HELP_TITLE,
        [('dot', c(RED)), ' vehicle  ', ('dot', c(GREEN)), ' digi, gateway, house  ',
         ('dot', c(BLUE)), ' weather'],
        [('dot', c(MAGENTA)), ' object, item  ', ('dot', c(ORANGE)), ' other  ',
         ('cross', c(WHITE), c(BLACK)), ' home'],
        [('tag', c(YELLOW), 'CALL'), 'newest heard  ',
         ('ring', c(RED), c(CYAN)), ('tag', c(CYAN), 'CALL'), 'selected (k / l)'],
        [('box', c(NO_TILE)), ' map tile not here yet (status: map N, NO NET)'],
        ['Calls go after %d min unheard, stations after %d.'
         % (LABEL_SECONDS // 60, KEEP_SECONDS // 60)],
    ] + aprs_ui.help_keys('c Enter') + [
        [('h', 'MAP')],
        ['i + / o -  zoom in / out   arrows or w a s d  move'],
        ['r  fit the stations   k / l  select next / previous'],
        ['Esc  deselect   z  clear the map (y / n)'],
        aprs_ui.HELP_BUTTONS,
        ['         held: B1 zoom out  B2 fit  B3 zoom in'],
    ]


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


_glyphs = {}


def tag(text, background, width=None, outline=False):
    """text on background (terminalio's font, 1 pixel margin; with a black
    outline, 14 pixels high), as a bitmap."""
    b = displayio.Bitmap(width or 6 * len(text) + 2, 14 if outline else 13, 256)
    if outline:
        b.fill(BLACK)
        bitmaptools.fill_region(b, 1, 1, b.width - 1, b.height - 1, background)
    else:
        b.fill(background)
    for k, ch in enumerate(text):
        g = _glyphs.get(ch)
        if g is None:
            glyph = terminalio.FONT.get_glyph(ord(ch))
            g = _glyphs[ch] = glyph.tile_index * 6 if glyph else -1
        if g >= 0:
            bitmaptools.blit(b, terminalio.FONT.bitmap, b.width - 6 * len(text) - 1 + 6 * k, 1,
                             x1=g, y1=0, x2=g + 6, y2=12, skip_source_index=0)
    return b


class Station:
    def __init__(self, key):
        self.key = key
        self.label = key[:9]
        self.lat = self.lon = self.merc = 0.0
        self.colour = ORANGE
        self.heard = 0.0
        self.labelled = True
        self.tag = None              # its call, drawn (when first needed)
        self.last = None             # (latest packet, hh:mm)
        self.xy = None               # on the map (pixels), or None when off it
        self.box = None              # where its call goes
        self.rect = None             # what it covers on the map


class MapDisplay(aprs_ui.Display):
    NAME = 'map'
    LONG_PRESS = ('o', 'r', 'i')
    KEYS = MAP_KEYS

    def __init__(self, home=None, centre=None, zoom=None, tiles=None):
        self.home = home
        self.centre = centre or home
        self.zoom = zoom or ZOOM
        self.zoom_start = self.zoom  # r: no closer than this
        self.start = self.centre     # r with no stations: back here
        self.tiles = tiles or aprs_tiles.TileCache(TILE_DIR, TILE_URL)
        self.fb, self.display = aprs_ui.open_framebuffer()
        group = displayio.Group()
        self.top = aprs_ui.TextRows(self.display, group, 1)
        self.columns = self.top.columns
        self.bitmap = displayio.Bitmap(W, MAP_H, 256)
        palette = displayio.Palette(256)
        for v in range(256):
            palette[v] = aprs_tiles.rgb332_colour(v)
        group.append(displayio.TileGrid(self.bitmap, pixel_shader=palette, y=MAP_TOP))
        self.list = aprs_ui.TextRows(self.display, group, LIST_ROWS, y=MAP_TOP + MAP_H)
        self.under = displayio.Bitmap(W, MAP_H, 256)
        self.rows = displayio.Bitmap(TILE, STRIP, 256)     # a tile's rows, read from its file
        self.rows_mv = memoryview(self.rows)
        self.credit = tag(CREDIT, WHITE)
        self.scale = None
        self.newest_tag = None
        self.selected = None         # the station picked with k / l
        self.selected_tag = None
        self.stations = {}
        self.order = []              # stations, oldest heard first (drawing order)
        self.newest = None
        self.lines = []              # the last LIST_ROWS packets
        self.list_rows = []          # what the rows below the map show
        self.list_todo = []          # list rows to rewrite
        self.rects = []              # map rectangles to redraw
        self.todo = []               # map strips to (re)load
        self.queue = []              # (z, x, y) tiles to download / convert
        self.files = {}              # (x, y) -> open tile BMP, or None, while strips load
        self.net_error = None
        self.next_age = 0.0
        self.now = time.monotonic    # seconds, for the stations' ages (a replay sets the log's)
        self.help = aprs_ui.HelpPage(self.display, group, help_rows())
        self.display.root_group = group
        self.set_view()
        if self.centre is None:
            while self.step():
                pass
        self.display.refresh(minimum_frames_per_second=0)

    # ------------------------------------------------------------ view

    def set_view(self):
        """Start (re)loading the map for self.centre and self.zoom."""
        self._close_files()
        self.todo = list(range((MAP_H + STRIP - 1) // STRIP))
        self.rects = []
        self.queue = []
        self.net_error = None
        if self.centre is None:
            return
        z = self.zoom
        lat, lon = self.centre
        self.x0 = int(world_x(lon, z)) - W // 2
        self.y0 = int(world_y(lat, z)) - MAP_H // 2
        self.clon = lon
        self.cmerc = mercator(lat)
        self.world = TILE << z
        n = 1 << z
        ctx, cty = (self.x0 + W // 2) >> 8, (self.y0 + MAP_H // 2) >> 8
        need = []
        for ty in range(self.y0 >> 8, ((self.y0 + MAP_H - 1) >> 8) + 1):
            for tx in range(self.x0 >> 8, ((self.x0 + W - 1) >> 8) + 1):
                if 0 <= ty < n and not self.tiles.ready(z, tx % n, ty):
                    need.append(((tx - ctx) ** 2 + (ty - cty) ** 2, tx % n, ty))
        self.queue = [(z, x, y) for _, x, y in sorted(need)]
        # The scale bar: the longest 1, 2 or 5 x 10^k that fits in 80 pixels.
        mpp = aprs_tiles.metres_per_pixel(lat, z)
        step = 1
        while step * 10 <= mpp * 80:
            step *= 10
        metres = max(m for m in (step, 2 * step, 5 * step) if m <= mpp * 80 or m == step)
        px = max(1, int(metres / mpp))
        text = ('%d km' % (metres // 1000)) if metres >= 1000 else ('%d m' % metres)
        self.scale = tag(text, WHITE, px + 8 + 6 * len(text))
        bitmaptools.fill_region(self.scale, 3, 9, 3 + px, 11, BLACK)
        bitmaptools.fill_region(self.scale, 3, 4, 4, 11, BLACK)
        bitmaptools.fill_region(self.scale, 2 + px, 4, 3 + px, 11, BLACK)
        for s in self.order:
            self._place(s)

    def _place(self, s):
        """Where s goes on the map, and the rectangle it covers."""
        s.xy = s.box = s.rect = None
        if self.centre is None:
            return
        x = W // 2 + round((s.lon - self.clon) / 360 * self.world)
        y = MAP_H // 2 + round((s.merc - self.cmerc) * self.world)
        if not (-60 < x < W + 60 and -20 < y < MAP_H + 20):
            return
        s.xy = (x, y)
        d = 5 if s is self.selected else 3
        r = [x - d, y - d, x + d + 1, y + d + 1]
        if s.labelled or s is self.selected:
            w = 6 * len(s.label) + 2
            lx = x + 5 if x + 5 + w <= W else x - 5 - w
            s.box = (lx, y - 7)
            r = [min(r[0], lx), y - 7, max(r[2], lx + w), y + 7]
        s.rect = r

    def _tile_file(self, x, y):
        key = (x, y)
        if key not in self.files:
            try:
                self.files[key] = open(self.tiles.path(self.zoom, x, y), 'rb')
            except OSError:
                self.files[key] = None
        return self.files[key]

    def _close_files(self):
        for f in self.files.values():
            if f:
                f.close()
        self.files = {}

    def _load_strip(self, k):
        """Map rows k * STRIP .. into the underlay, then onto the screen."""
        y1 = k * STRIP
        y2 = min(MAP_H, y1 + STRIP)
        if self.centre is None:
            bitmaptools.fill_region(self.under, 0, y1, W, y2, WAITING)
        n = 1 << self.zoom
        y = y1
        while y < y2 and self.centre:
            # Rows y .. y + h are in the same row of tiles.
            gy = self.y0 + y
            ty = gy >> 8
            h = min(y2 - y, TILE - (gy & 255))
            sx = 0
            while sx < W:
                gx = self.x0 + sx
                off = gx & 255
                m = min(TILE - off, W - sx)
                f = self._tile_file((gx >> 8) % n, ty) if 0 <= ty < n else None
                if f is None:
                    bitmaptools.fill_region(self.under, sx, y, sx + m, y + h, NO_TILE)
                else:
                    f.seek(BMP_HEADER + (gy & 255) * TILE)
                    f.readinto(self.rows_mv[:h * TILE])
                    bitmaptools.blit(self.under, self.rows, sx, y, x1=off, y1=0, x2=off + m, y2=h)
                sx += m
            y += h
        self._show((0, y1, W, y2))

    # ---------------------------------------------------------- drawing

    def _fill(self, x1, y1, x2, y2, colour, clip):
        x1 = max(x1, clip[0])
        y1 = max(y1, clip[1])
        x2 = min(x2, clip[2])
        y2 = min(y2, clip[3])
        if x1 < x2 and y1 < y2:
            bitmaptools.fill_region(self.bitmap, x1, y1, x2, y2, colour)

    def _blit(self, src, x, y, clip):
        """The bitmap src with its top left at x, y, inside clip."""
        x1 = max(x, clip[0])
        y1 = max(y, clip[1])
        x2 = min(x + src.width, clip[2])
        y2 = min(y + src.height, clip[3])
        if x1 < x2 and y1 < y2:
            bitmaptools.blit(self.bitmap, src, x1, y1, x1=x1 - x, y1=y1 - y, x2=x2 - x, y2=y2 - y)

    def _show(self, rect):
        """Tiles and everything over them, again, in rect; then refresh."""
        x1 = max(0, rect[0])
        y1 = max(0, rect[1])
        x2 = min(W, rect[2])
        y2 = min(MAP_H, rect[3])
        if x1 >= x2 or y1 >= y2:
            return
        clip = (x1, y1, x2, y2)
        bitmaptools.blit(self.bitmap, self.under, x1, y1, x1=x1, y1=y1, x2=x2, y2=y2)
        if self.centre is not None:
            if self.home:
                hx = W // 2 + round((self.home[1] - self.clon) / 360 * self.world)
                hy = MAP_H // 2 + round((mercator(self.home[0]) - self.cmerc) * self.world)
                if overlaps((hx - 6, hy - 6, hx + 7, hy + 7), clip):
                    self._fill(hx - 6, hy - 2, hx + 7, hy + 3, WHITE, clip)
                    self._fill(hx - 2, hy - 6, hx + 3, hy + 7, WHITE, clip)
                    self._fill(hx - 5, hy - 1, hx + 6, hy + 2, BLACK, clip)
                    self._fill(hx - 1, hy - 5, hx + 2, hy + 6, BLACK, clip)
            for s in self.order:
                if s.rect and overlaps(s.rect, clip):
                    x, y = s.xy
                    self._fill(x - 3, y - 3, x + 4, y + 4, BLACK, clip)
                    self._fill(x - 2, y - 2, x + 3, y + 3, s.colour, clip)
                    if s.box and s is not self.selected:
                        if s is self.newest:
                            if self.newest_tag is None:
                                self.newest_tag = tag(s.label, YELLOW, outline=True)
                            self._blit(self.newest_tag, s.box[0], s.box[1], clip)
                        else:
                            if s.tag is None:
                                s.tag = tag(s.label, WHITE, outline=True)
                            self._blit(s.tag, s.box[0], s.box[1], clip)
            self._blit(self.scale, 0, MAP_H - 13, clip)
            self._blit(self.credit, W - self.credit.width, MAP_H - 13, clip)
            s = self.selected
            if s and s.rect and overlaps(s.rect, clip):
                # Over everything: a ring round its dot, its call on cyan.
                x, y = s.xy
                self._fill(x - 5, y - 5, x + 6, y + 6, CYAN, clip)
                self._fill(x - 3, y - 3, x + 4, y + 4, BLACK, clip)
                self._fill(x - 2, y - 2, x + 3, y + 3, s.colour, clip)
                if self.selected_tag is None:
                    self.selected_tag = tag(s.label, CYAN, outline=True)
                self._blit(self.selected_tag, s.box[0], s.box[1], clip)
        self.bitmap.dirty(x1, y1, x2, y2)
        self.display.refresh(minimum_frames_per_second=0)

    def _redraw(self, rect):
        """Redraw rect later (step()); overlapping rectangles merge."""
        if rect is None or rect[0] >= W or rect[2] <= 0 or rect[1] >= MAP_H or rect[3] <= 0:
            return
        r = list(rect)
        for q in self.rects:
            if overlaps(q, r):
                self.rects.remove(q)
                r = [min(q[0], r[0]), min(q[1], r[1]), max(q[2], r[2]), max(q[3], r[3])]
                self._redraw(r)
                return
        self.rects.append(r)

    # ------------------------------------------------------- receiver calls

    def prepare(self):
        """Before the stream starts: every missing tile, then the whole map."""
        total = len(self.queue)
        while self.queue:
            self.message('Map: tile %d of %d (download, convert)'
                         % (total - len(self.queue) + 1, total))
            self.paused_step()
        while self.step():
            pass

    def step(self):
        """One piece of drawing: a strip of the help page, a text row, a
        rectangle or a strip of map."""
        if super().step():
            pass
        elif self.list_todo:
            k = self.list_todo.pop(0)
            self.list.colour(DETAIL if self.selected and self.selected.last else aprs_ui.FOREGROUND)
            self.list.row(k, self.list_rows[k] if k < len(self.list_rows) else '')
        elif self.rects:
            self._show(self.rects.pop(0))
        elif self.todo:
            self._load_strip(self.todo.pop(0))
        else:
            if self.files:
                self._close_files()
            return False
        return True

    @property
    def needs_pause(self):
        return bool(self.queue)

    def paused_step(self):
        """Download and / or convert the next missing tile."""
        z, x, y = self.queue.pop(0)
        t = time.monotonic()
        fetch = not self.tiles.has_png(z, x, y)
        try:
            self.tiles.convert(z, x, y, self.tiles.fetch(z, x, y) if fetch else None)
        except Exception as error:
            print('TILE_ERROR', json.dumps({'tile': [z, x, y],
                                            'error': '%s %s' % (type(error).__name__, error)}))
            if fetch:
                # No network (or no server): only convert what is on the card.
                self.net_error = type(error).__name__
                self.queue = [q for q in self.queue if self.tiles.has_png(*q)]
            return
        print('TILE', json.dumps({'tile': [z, x, y], 'fetched': fetch,
                                  's': round(time.monotonic() - t, 2)}))
        if z != self.zoom or self.centre is None:
            return
        f = self.files.pop((x, y), None)
        if f:
            f.close()
        # Reload the strips the tile is in.
        top = (y << 8) - self.y0
        for k in range(max(0, top // STRIP), min(MAP_H, top + TILE) // STRIP + 1):
            if k * STRIP < MAP_H and k not in self.todo:
                self.todo.append(k)

    def command(self, action):
        if self.asking:
            # (clear the map? y or n answers; other keys are ignored until then)
            if action == 'y':
                self.clear()
            if action in ('y', 'n', 'esc'):
                self.asking = None
                self.status_row(self.status_text)
            return True
        if self.help_command(action):
            return True
        if action == 'z':
            self.asking = CLEAR_PROMPT
            self.status_row(self.status_text)
            return True
        if action in ZOOM_KEYS:
            z = max(ZOOMS[0], min(ZOOMS[1], self.zoom + ZOOM_KEYS[action]))
            if z != self.zoom and self.centre:
                self.zoom = z
                self.set_view()
            print('MAP', json.dumps({'zoom': self.zoom, 'centre': self.centre}))
            return True
        if action == 'r':
            if self.order:
                self._fit()
            elif self.start:
                self.centre, self.zoom = self.start, self.zoom_start
                self.set_view()
            print('MAP', json.dumps({'zoom': self.zoom, 'centre': self.centre}))
            return True
        if action in PAN:
            if self.centre:
                dx, dy = PAN[action]
                x = self.x0 + W // 2 + dx * PAN_STEP * W
                y = self.y0 + MAP_H // 2 + dy * PAN_STEP * MAP_H
                self.centre = (unmercator(y / self.world - 0.5),
                               (x / self.world * 360.0) % 360.0 - 180.0)
                self.set_view()
            print('MAP', json.dumps({'zoom': self.zoom, 'centre': self.centre}))
            return True
        if action in ('k', 'l'):
            self._select(1 if action == 'k' else -1)
            return True
        if action == 'esc':
            if self.selected:
                self._set_selected(None)
                print('SELECT null')
            return True
        return False

    def clear(self):
        """Forget every station on the map and the packets below it."""
        self.stations = {}
        self.order = []
        self.newest = self.newest_tag = None
        self.selected = self.selected_tag = None
        self.lines = []
        self._show_list()
        # The whole map again, a strip at a time (step()).
        self.rects = [[0, y, W, min(MAP_H, y + STRIP)] for y in range(0, MAP_H, STRIP)]
        print('CLEAR')

    def _fit(self):
        """Centre the map on the stations, at the closest zoom (up to the
        starting one) that shows them all, FIT_MARGIN px inside the map."""
        # (around the copy of the world nearest the first one)
        lon0 = self.order[0].lon
        lons = [lon0 + (s.lon - lon0 + 180) % 360 - 180 for s in self.order]
        ys = [s.merc for s in self.order]
        z = self.zoom_start
        while z > ZOOMS[0] and ((max(lons) - min(lons)) / 360 * (TILE << z) > W - 2 * FIT_MARGIN
                                or (max(ys) - min(ys)) * (TILE << z) > MAP_H - 2 * FIT_MARGIN):
            z -= 1
        lon = (max(lons) + min(lons)) / 2
        self.centre = (unmercator((max(ys) + min(ys)) / 2), (lon + 180) % 360 - 180)
        self.zoom = z
        self.set_view()

    def _select(self, step):
        """The next (step 1) or previous (-1) station on the map, newest
        heard first; past either end, none."""
        shown = [s for s in reversed(self.order)
                 if s.xy and 0 <= s.xy[0] < W and 0 <= s.xy[1] < MAP_H]
        if self.selected in shown:
            k = shown.index(self.selected) + step
            pick = shown[k] if 0 <= k < len(shown) else None
        else:
            pick = shown[0 if step > 0 else -1] if shown else None
        self._set_selected(pick)
        s = pick
        print('SELECT', json.dumps({'call': s.key, 'lat': s.lat, 'lon': s.lon,
                                    'age_s': round(self.now() - s.heard)} if s else None))

    def _set_selected(self, s):
        before, self.selected = self.selected, s
        self.selected_tag = None
        self._show_list()
        for t in (before, s):
            if t is not None:
                old = t.rect
                self._place(t)
                self._redraw(old)
                self._redraw(t.rect)

    def add_packet(self, p, hhmm):
        """A decoded packet (aprs_parse dict) heard at hhmm (UTC)."""
        self._add_line('%s %-9s %s' % packet_row(p, hhmm, self.home, self.columns - 17))
        named = p.get('type') in ('object', 'item') and p.get('name')
        key = p['name'] if named else p['src']
        s = self.stations.get(key)
        if 'lat' in p and not (p['lat'] == 0 and p['lon'] == 0):
            if p.get('killed'):
                if s:
                    self._remove(s)
                return
            if self.centre is None:
                self.centre = (p['lat'], p['lon'])
                self.set_view()
            if s is None:
                s = self.stations[key] = Station(key)
                if len(self.order) >= MAX_STATIONS:
                    self._remove(self.order[0])
            else:
                self.order.remove(s)
            s.lat, s.lon = p['lat'], p['lon']
            s.merc = mercator(s.lat)
            s.colour = marker_colour(p)
        elif s is None:
            return
        else:
            self.order.remove(s)
        # Heard now: on top, with its call on yellow.
        self.order.append(s)
        s.last = (p, hhmm)
        if s is self.selected:
            self._show_list()
        s.heard = self.now()
        s.labelled = True
        old = s.rect
        self._place(s)
        before, self.newest = self.newest, s
        if before is not s:
            self.newest_tag = None
            if before is not None:
                self._redraw(before.rect)
        self._redraw(old)
        self._redraw(s.rect)

    def _remove(self, s):
        self.order.remove(s)
        del self.stations[s.key]
        if self.newest is s:
            self.newest = None
        if self.selected is s:
            self.selected = None
            self._show_list()
        self._redraw(s.rect)

    def _add_line(self, text):
        self.lines = (self.lines + [text])[-LIST_ROWS:]
        self._show_list()

    def _show_list(self):
        """Below the map: the selected station's latest packet, or the
        last packets."""
        s = self.selected
        if s and s.last:
            self.list_rows = wrap(detail(s.last[0], s.last[1], self.home),
                                  self.columns - 1, LIST_ROWS)
        else:
            self.list_rows = self.lines
        self.list_todo = list(range(LIST_ROWS))

    def show(self, st):
        """The receiver's status (an aprs_ui.Status), about once a second."""
        notes = (' MUTED' if st.muted else '') + ('' if st.sd else ' NO SD')
        if self.queue:
            notes += ' map %d' % len(self.queue)
        if self.net_error:
            notes += ' NO NET'
        if st.note:
            notes += ' ' + st.note
        # (a replay knows neither the frequency nor the level)
        freq = ('%d.%03d ' % (st.dial // 1000000, st.dial // 1000 % 1000)
                if st.dial is not None else '')
        level = ('%4.0fdB %s ' % (st.level, 'DCD' if st.dcd else '   ')
                 if st.level is not None else '')
        self.status_row('%s%-8s %s %s%dp %ds z%d%s' % (
            freq, st.label[:8], st.utc, level, st.packets, st.stations, self.zoom, notes))
        # Stations not heard for KEEP_SECONDS go; their calls go after
        # LABEL_SECONDS.
        now = self.now()
        if now >= self.next_age:
            self.next_age = now + 30
            for s in [s for s in self.order if now - s.heard > KEEP_SECONDS]:
                self._remove(s)
            for s in self.order:
                if s.labelled and now - s.heard > LABEL_SECONDS:
                    s.labelled = False
                    s.tag = None
                    self._redraw(s.rect)
                    self._place(s)

    def message(self, text):
        self.top.row(0, text)

    def connecting(self):
        self.top.row(0, 'CONNECTING: looking for the USB receiver')

    def ready(self):
        self._add_line('Listening for APRS packets')
        if self.centre is None:
            self._add_line('The map centres on the first position heard')
        while self.list_todo:
            self.step()

    def screen(self):
        return self.top.text() + self.list.text()

    def close(self):
        self._close_files()
