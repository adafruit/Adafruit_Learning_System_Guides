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

Drawing: the map is an adafruit_maptiles MapView (lib/adafruit_maptiles:
the tiles come from its cache on the SD card, /sd/tiles/osm, shared with
the ADS-B receiver and anything else using the library, as 8-bit BMPs in
the framebuffer's RGB332 colours). They are read a strip of rows at a
time into the view's underlay. Redrawing a rectangle copies it back from
the underlay, then draws what overlaps it (station dots, their calls,
home, scale bar, credit; the calls are pre-drawn small bitmaps).
add_packet() only notes what changed; step() then redraws one strip,
rectangle or text row at a time (each 5-15 ms): refreshing the whole
screen takes ~100 ms, longer than the receiver can leave the USB
stream. Tiles not on the SD card yet are downloaded and converted with
the stream paused (paused_step, one tile at a time while the channel is
quiet); until then they are grey.
"""
import json
import time
import displayio
from adafruit_maptiles import rgb332_colour
from adafruit_maptiles.cache import TileCache
from adafruit_maptiles.map_view import BLACK, NO_TILE, WHITE, MapView, overlaps, text_bitmap
import aprs_ui
from aprs_ui import packet_row

# pylint: disable=too-many-branches, too-many-return-statements, too-many-nested-blocks

USER_AGENT = 'FruitJam-APRS-receiver/1.0 CircuitPython'   # for the tile server
ZOOM = 9                     # ~75 km across the screen at 40 degrees
ZOOMS = (3, 15)
ZOOM_KEYS = {'i': 1, '+': 1, 'o': -1, '-': -1}
PAN = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1),
       'a': (-1, 0), 'd': (1, 0), 'w': (0, -1), 's': (0, 1)}
PAN_STEP = 0.25              # of the screen, a press
MAP_KEYS = tuple(ZOOM_KEYS) + tuple(PAN) + ('r', 'k', 'l', 'z')    # (and Esc: deselect)
CLEAR_PROMPT = 'CLEAR THE MAP? y: yes, n: no'

W = aprs_ui.WIDTH
MAP_TOP = 12
MAP_H = 192
LIST_ROWS = 3
STRIP = 8                    # map rows loaded or redrawn per step
MAX_STATIONS = 60
LABEL_SECONDS = 1800         # calls are shown for stations heard this recently
KEEP_SECONDS = 3600          # stations not heard this long fall off the map

# Colours are RGB332 values.
YELLOW = 0xfc
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
    c = rgb332_colour
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


class Station:
    def __init__(self, key):
        self.key = key
        self.label = key[:9]
        self.lat = self.lon = 0.0
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
        self.zoom_start = zoom or ZOOM   # r: no closer than this
        self.start = centre or home  # r with no stations: back here
        self.fb, self.display = aprs_ui.open_framebuffer()
        group = displayio.Group()
        self.top = aprs_ui.TextRows(self.display, group, 1)
        self.columns = self.top.columns
        self.map = MapView(W, MAP_H, self.start, self.zoom_start, y=MAP_TOP, zooms=ZOOMS,
                           strip=STRIP, cache=tiles or TileCache(user_agent=USER_AGENT))
        group.append(self.map)
        self.list = aprs_ui.TextRows(self.display, group, LIST_ROWS, y=MAP_TOP + MAP_H)
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
        self.next_age = 0.0
        self.now = time.monotonic    # seconds, for the stations' ages (a replay sets the log's)
        self.help = aprs_ui.HelpPage(self.display, group, help_rows())
        self.display.root_group = group
        if self.map.centre is None:
            while self.step():
                pass
        self.display.refresh(minimum_frames_per_second=0)

    # ------------------------------------------------------------ view

    def _moved(self):
        """After the map's centre or zoom changed: the strips to load are
        the map's own (step()); the stations go where they now are."""
        self.rects = []
        for s in self.order:
            self._place(s)

    def _near(self, lon):
        """lon, moved by 360 degrees to the copy of the world nearest the
        map's centre."""
        return self.map.clon + (lon - self.map.clon + 180) % 360 - 180

    def _place(self, s):
        """Where s goes on the map, and the rectangle it covers."""
        s.xy = s.box = s.rect = None
        if self.map.centre is None:
            return
        x, y = self.map.xy(s.lat, self._near(s.lon))
        if not (-60 < x < W + 60 and -20 < y < MAP_H + 20):
            return
        s.xy = (x, y)
        d = 5 if s is self.selected else 3
        r = [x - d, y - d, x + d + 1, y + d + 1]
        if s.labelled or s is self.selected:
            w = 6 * len(s.label) + 5     # (text_bitmap() with an outline)
            lx = x + 5 if x + 5 + w <= W else x - 5 - w
            s.box = (lx, y - 7)
            r = [min(r[0], lx), y - 7, max(r[2], lx + w), y + 7]
        s.rect = r

    # ---------------------------------------------------------- drawing

    def _show(self, rect):
        """Tiles and everything over them, again, in rect; then refresh."""
        clip = (max(0, rect[0]), max(0, rect[1]), min(W, rect[2]), min(MAP_H, rect[3]))
        if clip[0] >= clip[2] or clip[1] >= clip[3]:
            return
        v = self.map
        v.restore(clip)
        if v.centre is not None:
            if self.home:
                hx, hy = v.xy(self.home[0], self._near(self.home[1]))
                v.cross(hx, hy, clip)
            for s in self.order:
                if s.rect and overlaps(s.rect, clip):
                    x, y = s.xy
                    v.fill(x - 3, y - 3, x + 4, y + 4, BLACK, clip)
                    v.fill(x - 2, y - 2, x + 3, y + 3, s.colour, clip)
                    if s.box and s is not self.selected:
                        if s is self.newest:
                            if self.newest_tag is None:
                                self.newest_tag = text_bitmap(s.label, YELLOW, outline=True)
                            v.blit(self.newest_tag, s.box[0], s.box[1], clip)
                        else:
                            if s.tag is None:
                                s.tag = text_bitmap(s.label, WHITE, outline=True)
                            v.blit(s.tag, s.box[0], s.box[1], clip)
            v.draw_legend(clip)
            s = self.selected
            if s and s.rect and overlaps(s.rect, clip):
                # Over everything: a ring round its dot, its call on cyan.
                x, y = s.xy
                v.fill(x - 5, y - 5, x + 6, y + 6, CYAN, clip)
                v.fill(x - 3, y - 3, x + 4, y + 4, BLACK, clip)
                v.fill(x - 2, y - 2, x + 3, y + 3, s.colour, clip)
                if self.selected_tag is None:
                    self.selected_tag = text_bitmap(s.label, CYAN, outline=True)
                v.blit(self.selected_tag, s.box[0], s.box[1], clip)
        v.dirty(clip)
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
        total = len(self.map.missing)
        while self.map.missing:
            self.message('Map: tile %d of %d (download, convert)'
                         % (total - len(self.map.missing) + 1, total))
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
        elif self.map.loading:
            self._show(self.map.load_step())
            if not self.map.loading:
                self.map.close()
        else:
            return False
        return True

    @property
    def needs_pause(self):
        return bool(self.map.missing)

    def paused_step(self):
        """Download and / or convert the next missing tile (step() then
        reloads the strips it is in)."""
        self.map.fetch_step()

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
        v = self.map
        if action in ZOOM_KEYS:
            if v.centre and (v.zoom_in() if ZOOM_KEYS[action] > 0 else v.zoom_out()):
                self._moved()
            print('MAP', json.dumps({'zoom': v.zoom, 'centre': v.centre}))
            return True
        if action == 'r':
            if self.order:
                # (around the copy of the world nearest the first one)
                lon0 = self.order[0].lon
                v.fit([(s.lat, lon0 + (s.lon - lon0 + 180) % 360 - 180) for s in self.order],
                      self.zoom_start)
                self._moved()
            elif self.start:
                v.set_view(self.start, self.zoom_start)
                self._moved()
            print('MAP', json.dumps({'zoom': v.zoom, 'centre': v.centre}))
            return True
        if action in PAN:
            if v.centre:
                dx, dy = PAN[action]
                v.pan(dx * PAN_STEP, dy * PAN_STEP)
                self._moved()
            print('MAP', json.dumps({'zoom': v.zoom, 'centre': v.centre}))
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
            if self.map.centre is None:
                self.map.centre = (p['lat'], p['lon'])
                self._moved()
            if s is None:
                s = self.stations[key] = Station(key)
                if len(self.order) >= MAX_STATIONS:
                    self._remove(self.order[0])
            else:
                self.order.remove(s)
            s.lat, s.lon = p['lat'], p['lon']
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
        if self.map.missing:
            notes += ' map %d' % len(self.map.missing)
        if self.map.net_error:
            notes += ' NO NET'
        if st.note:
            notes += ' ' + st.note
        # (a replay knows neither the frequency nor the level)
        freq = ('%d.%03d ' % (st.dial // 1000000, st.dial // 1000 % 1000)
                if st.dial is not None else '')
        level = ('%4.0fdB %s ' % (st.level, 'DCD' if st.dcd else '   ')
                 if st.level is not None else '')
        self.status_row('%s%-8s %s %s%dp %ds z%d%s' % (
            freq, st.label[:8], st.utc, level, st.packets, st.stations, self.map.zoom, notes))
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
        if self.map.centre is None:
            self._add_line('The map centres on the first position heard')
        while self.list_todo:
            self.step()

    def screen(self):
        return self.top.text() + self.list.text()

    def close(self):
        self.map.close()
