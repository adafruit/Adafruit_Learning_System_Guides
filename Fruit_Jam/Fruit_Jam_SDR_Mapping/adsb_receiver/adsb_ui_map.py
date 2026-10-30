# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Map display for adsb_receiver.py: the aircraft on an OpenStreetMap map,
on the 320x240 screen (DVI via picodvi on the Fruit Jam, the TFT shield
on the Metro ESP32-P4).

    row 0       status: UTC, messages a minute, aircraft, share of the air
                time heard, zoom (notes: map tiles still to get, NO NET)
    12-179      the map (320x168): each aircraft with a position as a
                square in its altitude's colour, a line along its track,
                a trail (lines through its last positions) and a tag
                (callsign or address, and altitude in hundreds of feet);
                home as a cross
    180-239     the five aircraft heard most recently, a line each (or
                the selected aircraft's details, in cyan)

Colours by altitude: green below 5,000 ft, teal below 15,000, orange
below 25,000, red below 35,000, magenta above; grey on the ground, white
when unknown. A hollow square: no position for a minute. Aircraft not
heard for KEEP_SECONDS (90) are dropped from the map.

The map is centred on home, on centre=(lat, lon), or on the first
position heard. Console: i or + / o or - zoom in / out, the arrow keys or
w a s d move the map (a quarter of the screen a press), r fit the aircraft on the map: centred
on them, at the closest zoom that shows them all (no closer than the zoom
the map started with; with none: back to home, or the first position
heard), k / l select the next / previous aircraft on the screen (in
order of callsign or address; past either end: none), which is then drawn
over everything with a cyan ring round its square and its tag on cyan;
the rows below the map then show its details in cyan (until it leaves the
map). Esc deselects (back to the aircraft heard most recently). j hides
the tags (all but the selected aircraft's), or shows them again.
z clear the map: the status row asks (in yellow), y has the receiver
forget every aircraft (they come back as they are heard again), n (or
Esc) keeps them; other keys wait until it is answered. ? shows a page of
help over everything below the status row (the colours and marks, then
the keys; ? or Esc hides it: adsb_ui.HelpPage); while it is up the map's
keys do nothing and the map is not redrawn.

Drawing: the map is an adafruit_maptiles MapView (lib/adafruit_maptiles:
the tiles come from its cache on the SD card, /sd/tiles/osm, shared with
the APRS receiver and anything else using the library, as 8-bit BMPs in
the framebuffer's RGB332 colours). The tiles are read once per view into
the view's underlay. Every MAP_EVERY seconds the underlay is copied onto
the map and the aircraft drawn over it, then the screen refreshes
(~100 ms: the radio waits). Missing tiles are downloaded and converted
with the radio stopped (paused_step(), one tile at a time); until then
they are grey.
"""
import json
import math
import displayio
from adafruit_maptiles import rgb332_colour
from adafruit_maptiles.cache import TileCache
from adafruit_maptiles.map_view import BLACK, WHITE, MapView, text_bitmap
import adsb_parse
import adsb_ui

# pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-return-statements

USER_AGENT = 'FruitJam-ADSB-receiver/1.0 CircuitPython'   # for the tile server
ZOOM = 8                     # ~150 km across the screen at 40 degrees
ZOOMS = (3, 13)
ZOOM_KEYS = {'i': 1, '+': 1, 'o': -1, '-': -1}
MAP_EVERY = 2.0              # s between map redraws
PAN = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1),
       'a': (-1, 0), 'd': (1, 0), 'w': (0, -1), 's': (0, 1)}
PAN_STEP = 0.25              # of the screen, a press
# the map's own: not while the help shows (and Esc: deselect)
KEYS = tuple(ZOOM_KEYS) + tuple(PAN) + ('r', 'k', 'l', 'j', 'z')
CLEAR_PROMPT = 'CLEAR THE MAP? y: yes, n: no'
PROMPT = 0xFFE000            # the prompt's colour
DETAIL = 0x40FFFF            # the selected aircraft's details, below the map
KEEP_SECONDS = 90            # aircraft heard this recently are drawn
POSITION_SECONDS = 300       # ... if they have a position this recent
STALE_SECONDS = 60           # older than this: drawn hollow
TRAIL_SIZE = 4               # px: the trail's thickness

W = adsb_ui.WIDTH
MAP_TOP = 12
MAP_H = 168
LIST_ROWS = 5

# Colours are RGB332 values.
GREY = 0x92
GREEN = 0x1C
TEAL = 0x12
ORANGE = 0xF4
RED = 0xE0
MAGENTA = 0xE3
CYAN = 0x1F                  # the selected aircraft's ring and tag


def colour(a):
    if a.ground:
        return GREY
    if a.alt is None:
        return WHITE
    for limit, c in ((5000, GREEN), (15000, TEAL), (25000, ORANGE), (35000, RED)):
        if a.alt < limit:
            return c
    return MAGENTA


def plotted(aircraft, now):
    """The aircraft drawn on the map."""
    return [a for a in aircraft if a.lat is not None and now - a.seen <= KEEP_SECONDS
            and now - a.pos_t <= POSITION_SECONDS]


def label(a):
    text = a.callsign or a.icao
    if a.ground:
        return text + ' GND'
    if a.alt is not None:
        return '%s %d' % (text, (a.alt + 50) // 100)
    return text


def details(a, now, home):
    """The selected aircraft's rows below the map (LIST_ROWS)."""
    rows = ['%s  ICAO %s%s%s%s' % (a.callsign or '(no callsign)', a.icao,
                                   '  squawk %s' % a.squawk if a.squawk else '',
                                   '  cat %s' % a.category if a.category else '',
                                   '  ' + a.emergency.upper() if a.emergency else '')]
    if a.ground:
        rows.append('on the ground')
    else:
        t = 'altitude %d ft' % a.alt if a.alt is not None else 'altitude not known'
        if a.vr:
            t += '  %s %d ft/min' % ('climbing' if a.vr > 0 else 'descending', abs(a.vr))
        rows.append(t)
    rows.append('  '.join(t for t in ('speed %d kt' % a.gs if a.gs is not None else '',
                                      'track %d' % a.track if a.track is not None else '') if t))
    t = '%.4f %.4f  %d s ago' % (a.lat, a.lon, now - a.pos_t)
    if home is not None:
        t = '%.0f km %s of home  %s' % (
            adsb_parse.distance_km(home, (a.lat, a.lon)),
            adsb_ui.compass(adsb_parse.bearing(home, (a.lat, a.lon))), t)
    rows.append(t)
    rows.append('heard %d s ago%s  %d msgs' % (
        now - a.seen, '  %d dBFS' % a.signal if a.signal is not None else '', a.messages))
    return rows


def help_rows():
    """The help page (adsb_ui.HelpPage): the map's colours and marks,
    then the keys."""
    c = rgb332_colour
    return [
        adsb_ui.HELP_TITLE,
        [('h', 'MAP'), '  each aircraft by its altitude (feet):'],
        [('dot', c(GREEN)), ' below 5,000  ', ('dot', c(TEAL)), ' 15,000  ',
         ('dot', c(ORANGE)), ' 25,000  ', ('dot', c(RED)), ' 35,000'],
        [('dot', c(MAGENTA)), ' higher  ', ('dot', c(GREY)), ' on the ground  ',
         ('dot', c(WHITE)), ' not known'],
        [('plane', c(RED)), ' its trail, position and track'],
        [('hollow', c(RED)), ' no position for %d s   ' % STALE_SECONDS,
         ('ring', c(RED), c(CYAN)), ' selected  ', ('cross', c(WHITE), c(BLACK)), ' home'],
        [('tag', c(WHITE), 'SWA123 350'), 'callsign (or address), altitude'],
        ['in 100s of feet. Aircraft go after %d s unheard.' % KEEP_SECONDS],
        ['Below: the five heard last, or the selected one.'],
        ['Status row: messages/min, aircraft, % of the air'],
        ['time heard (snapshots), zoom.'],
    ] + adsb_ui.help_keys('h') + [
        [('h', 'MAP'), '  i + / o -  zoom   arrows or w a s d  move'],
        ['r  fit the aircraft   k / l  select next / previous'],
        ['j  hide / show tags   Esc  deselect   z  clear map'],
    ]


class MapDisplay(adsb_ui.Display):
    NAME = 'map'
    KEYS = KEYS

    def __init__(self, home=None, centre=None, zoom=None, tiles=None):
        self.home = home
        self.zoom_start = zoom or ZOOM
        self.points = []             # where the aircraft on the map are (for r)
        # the aircraft on the screen at the last redraw, in order (for k / l)
        self.visible = []
        # the ICAO address of the aircraft picked with k / l, or None
        self.selected = None
        self.tags_hidden = False     # j: only the selected aircraft's tag is drawn
        self.status = '1090 MHz ADS-B'   # the status row
        self.asking = False          # z: the status row asks whether to clear the map
        self.fb, self.display = adsb_ui.open_framebuffer()
        group = displayio.Group()
        self.top = adsb_ui.TextRows(self.display, group, 1)
        self.map = MapView(W, MAP_H, centre or home, self.zoom_start, y=MAP_TOP, zooms=ZOOMS,
                           cache=tiles or TileCache(user_agent=USER_AGENT))
        group.append(self.map)
        self.list = adsb_ui.TextRows(self.display, group, LIST_ROWS, y=MAP_TOP + MAP_H)
        self.help = adsb_ui.HelpPage(self.display, group, help_rows())
        self.tags = {}               # (label, background) -> its bitmap
        self.last_map = None
        self.display.root_group = group
        self._moved()
        self.display.refresh(minimum_frames_per_second=0)

    def _moved(self):
        """After the map's centre or zoom changed: its tiles (grey where
        they are missing: queued for paused_step()), and a redraw."""
        self.map.load()
        self.last_map = None

    # ---------------------------------------------------------- drawing

    def _tag(self, text, background=WHITE):
        b = self.tags.get((text, background))
        if b is None:
            if len(self.tags) > 60:
                self.tags = {}
            b = self.tags[(text, background)] = text_bitmap(text, background, outline=True)
        return b

    def _draw(self, shown, now):
        v = self.map
        v.restore()
        if v.centre is None:
            v.dirty()
            return
        if self.home:
            v.cross(*v.xy(*self.home))
        # oldest first: the newest on top (the selected one above all)
        visible = []
        for a in shown:
            x, y = v.xy(a.lat, a.lon)
            if 0 <= x < W and 0 <= y < MAP_H:
                visible.append((a.callsign or a.icao, a.icao))
        self.visible = [icao for _, icao in sorted(visible)]
        order = [a for a in reversed(shown) if a.icao != self.selected]
        order += [a for a in shown if a.icao == self.selected]
        for a in order:
            c = colour(a)
            x, y = v.xy(a.lat, a.lon)
            if not (-80 < x < W + 80 and -20 < y < MAP_H + 20):
                continue
            # the trail: straight lines from each position heard to the next
            h = TRAIL_SIZE // 2
            px = py = None
            for tx, ty in [v.xy(lat, lon) for lat, lon in a.trail] + [(x, y)]:
                if px is not None:
                    for d in range(-h, TRAIL_SIZE - h):   # TRAIL_SIZE lines side by side
                        if abs(tx - px) >= abs(ty - py):
                            v.line(px, py + d, tx, ty + d, c)
                        else:
                            v.line(px + d, py, tx + d, ty, c)
                v.fill(tx - h, ty - h, tx - h + TRAIL_SIZE, ty - h + TRAIL_SIZE, c)
                px, py = tx, ty
            selected = a.icao == self.selected
            if selected:
                v.fill(x - 5, y - 5, x + 6, y + 6, CYAN)
            if a.track is not None and not a.ground:
                r = math.radians(a.track)
                ex, ey = x + round(12 * math.sin(r)), y - round(12 * math.cos(r))
                v.line(x + 1, y + 1, ex + 1, ey + 1, BLACK)
                v.line(x, y, ex, ey, c)
            v.fill(x - 3, y - 3, x + 4, y + 4, BLACK)
            if now - a.pos_t <= STALE_SECONDS:
                v.fill(x - 2, y - 2, x + 3, y + 3, c)
            else:
                v.fill(x - 2, y - 2, x + 3, y + 3, c)
                v.fill(x - 1, y - 1, x + 2, y + 2, BLACK)
            if self.tags_hidden and not selected:
                continue
            t = self._tag(label(a), CYAN if selected else WHITE)
            lx = x + 6 if x + 6 + t.width <= W else x - 6 - t.width
            ly = y - 7
            if a.track is not None and not a.ground:
                # The trail runs back along the track: when it is on the
                # label's side, the label goes above it or below it.
                r = math.radians(a.track)
                if (math.sin(r) if lx < x else -math.sin(r)) > 0.5:
                    ly = y - 20 if math.cos(r) > 0 else y + 7
            v.blit(t, lx, ly)
        v.draw_legend()
        v.dirty()

    # ------------------------------------------------------- receiver calls

    @property
    def needs_pause(self):
        # (after a failed download only tiles already downloaded stay queued)
        return bool(self.map.missing)

    def paused_step(self):
        """One missing tile: download (if needed) and convert. Seconds."""
        if self.map.fetch_step() and self.map.load():
            self.last_map = None

    def prepare(self):
        """Before the radio starts: every missing tile."""
        total = len(self.map.missing)
        while self.needs_pause:
            self.message('Map: tile %d of %d (download, convert)'
                         % (total - len(self.map.missing) + 1, total))
            self.paused_step()

    def _status_row(self):
        self.top.colour(PROMPT if self.asking else adsb_ui.FOREGROUND)
        self.top.row(0, CLEAR_PROMPT if self.asking else self.status)

    def command(self, action):
        if self.asking:
            # (clear the map? y or n answers; other keys are ignored until then)
            if action in ('y', 'n', 'esc'):
                self.asking = False
                self._status_row()
                self.top.refresh()
            if action == 'y':
                self.points = self.visible = []
                self.selected = None
                self.last_map = None
                return 'clear'
            return True
        if self.help_command(action):
            if not self.help.shown:
                self.last_map = None     # (not redrawn while it was up)
            return True
        if action == 'z':
            self.asking = True
            self._status_row()
            self.top.refresh()
            return True
        if action in ZOOM_KEYS:
            changed = self.map.zoom_in() if ZOOM_KEYS[action] > 0 else self.map.zoom_out()
            if changed:
                self._moved()
            return True
        if action == 'r':
            if self.points:
                self.map.fit(self.points, self.zoom_start)
            else:
                self.map.set_view(self.home or self.reference_seen)
            self._moved()
            return True
        if action in ('k', 'l'):
            # the next (k) or previous (l) aircraft on the screen; past either end, none
            v = self.visible
            step = 1 if action == 'k' else -1
            if self.selected in v:
                k = v.index(self.selected) + step
                self.selected = v[k] if 0 <= k < len(v) else None
            else:
                self.selected = v[0 if step > 0 else -1] if v else None
            print('SELECT', json.dumps(self.selected))
            self.last_map = None
            return True
        if action == 'j':
            self.tags_hidden = not self.tags_hidden
            print('TAGS', 'hidden' if self.tags_hidden else 'shown')
            self.last_map = None
            return True
        if action == 'esc' and self.selected is not None:
            self.selected = None
            print('SELECT null')
            self.last_map = None
            return True
        if action in PAN:
            if self.map.centre is not None:
                dx, dy = PAN[action]
                self.map.pan(dx * PAN_STEP, dy * PAN_STEP)
                self._moved()
            return True
        return False

    reference_seen = None

    def show(self, st, aircraft, now):
        shown = plotted(aircraft, now)
        self.points = [(a.lat, a.lon) for a in shown]
        selected = [a for a in shown if a.icao == self.selected]
        if not selected and self.selected is not None:
            # (it left the map)
            self.selected = None
            self.last_map = None
        recent = [a for a in aircraft if now - a.seen <= adsb_ui.TABLE_SECONDS]
        note = ' z%d' % self.map.zoom
        if self.map.missing:
            note += ' map %d' % len(self.map.missing)
        if self.map.net_error:
            note += ' NO NET'
        heard = ' %.1f%%' % st.heard if st.heard is not None else ''
        self.status = 'ADS-B %s %s %d/min %d aircraft%s%s' % (
            st.utc, st.clock, round(st.per_minute), len(recent), heard, note)
        self._status_row()
        rows = details(selected[0], now, self.home) if selected else None
        self.list.colour(DETAIL if rows else adsb_ui.FOREGROUND)
        for i in range(LIST_ROWS):
            if rows:
                row = rows[i]
            elif i < len(recent):
                a = recent[i]
                row = '%-8s %6s %3s %3s %s' % ((a.callsign or a.icao)[:8], adsb_ui.altitude(a),
                                               '%d' % a.gs if a.gs is not None else '',
                                               '%d' % a.track if a.track is not None else '',
                                               adsb_ui.where(a, self.home, 20))
            else:
                row = ''
            self.list.row(i, row)
        if st.reference is not None:
            self.reference_seen = st.reference
            if self.map.centre is None:
                self.map.centre = st.reference
                self._moved()
        if not self.help.shown and (self.last_map is None or now - self.last_map >= MAP_EVERY):
            self.last_map = now
            self._draw(shown, now)
            self.top.dirty = True
        self.top.refresh()
        self.list.refresh()

    def message(self, text):
        self._status_row()
        self.list.row(0, text)
        self.top.refresh()
        self.list.refresh()

    def ready(self):
        self.list.row(0, 'Listening...')
        self.list.refresh()

    def screen(self):
        return self.top.text() + self.list.text()

    def close(self):
        self.map.close()
