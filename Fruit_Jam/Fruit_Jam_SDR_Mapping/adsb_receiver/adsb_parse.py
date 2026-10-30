# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Mode S / ADS-B messages (already CRC-checked by _adsb) -> dicts, and the
aircraft they come from.

decode(msg) -> dict with 'df', 'icao' (hex string) and what the message
carries: 'callsign', 'category', 'alt' (ft), 'cpr' (odd, lat17, lon17,
surface), 'gs' (kt), 'track' (deg), 'heading', 'ias' / 'tas' (kt),
'vr' (ft/min), 'squawk', 'emergency'.

Aircraft keeps what is known about each one; Aircraft.update(m, now)
merges a message in and works out positions from CPR: globally from an
even and an odd frame less than 10 s apart, or locally from one frame and
a reference within 180 NM (the aircraft's last position, or home).
"""

import math

# pylint: disable=too-many-locals, too-many-branches, too-many-statements
# pylint: disable=unsubscriptable-object, unused-argument

AIS = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ##### ###############0123456789######'
EMERGENCY = ('', 'emergency', 'medical', 'fuel', 'comms', 'hijack', 'downed', 'reserved')
NZ = 15
CPR_MAX_AGE = 10.0           # s between an even and an odd frame for a global decode
LOCAL_MAX_AGE = 600.0        # s: an aircraft's last position stays a reference this long
MAX_RANGE_KM = 600           # positions further from home are thrown away
MAX_SPEED_KMS = 0.6          # km/s: jumps faster than this are thrown away (~1200 kt)


def _crc_table():
    t = []
    for b in range(256):
        c = b << 16
        for _ in range(8):
            c = ((c << 1) ^ 0xFFF409) if c & 0x800000 else (c << 1)
        t.append(c & 0xFFFFFF)
    return t


_CRC = _crc_table()


def residual(msg):
    """The Mode S CRC of msg xor its parity field: 0 for a good DF17, the
    aircraft's address for DF0/4/5/16/20/21."""
    c = 0
    for b in msg[:-3]:
        c = ((c << 8) & 0xFFFFFF) ^ _CRC[((c >> 16) ^ b) & 255]
    return c ^ ((msg[-3] << 16) | (msg[-2] << 8) | msg[-1])


def field(v, nbits, first, last):
    """Bits first..last (1 = most significant) of an nbits-bit integer."""
    return (v >> (nbits - last)) & ((1 << (last - first + 1)) - 1)


# ------------------------------------------------------------- altitude, squawk

def gillham(id13):
    """The 13-bit ID / AC field in Mode A order (A4 A2 A1 / B / C / D as
    hex digits: 0xABCD with each digit 0..7)."""
    h = 0
    for bit, out in ((0x1000, 0x0010), (0x0800, 0x1000), (0x0400, 0x0020), (0x0200, 0x2000),
                     (0x0100, 0x0040), (0x0080, 0x4000), (0x0020, 0x0100), (0x0010, 0x0001),
                     (0x0008, 0x0200), (0x0004, 0x0002), (0x0002, 0x0400), (0x0001, 0x0004)):
        if id13 & bit:
            h |= out
    return h


def squawk(id13):
    h = gillham(id13)
    return '%d%d%d%d' % ((h >> 12) & 7, (h >> 8) & 7, (h >> 4) & 7, h & 7)


def mode_c(h):
    """Gillham-coded altitude (Mode A order) -> feet, or None."""
    if h & 0xFFFF8889 or not h & 0xF0:
        return None
    hundreds = 0
    if h & 0x10:
        hundreds ^= 7
    if h & 0x20:
        hundreds ^= 3
    if h & 0x40:
        hundreds ^= 1
    if hundreds & 5 == 5:
        hundreds ^= 2
    if hundreds > 5:
        return None
    fives = 0
    for bit, x in ((0x0002, 0xFF), (0x0004, 0x7F), (0x1000, 0x3F), (0x2000, 0x1F), (0x4000, 0x0F),
                   (0x0100, 0x07), (0x0200, 0x03), (0x0400, 0x01)):
        if h & bit:
            fives ^= x
    if fives & 1:
        hundreds = 6 - hundreds
    return (fives * 5 + hundreds - 13) * 100


def ac13(a):
    """DF0/4/16/20 altitude code -> feet, or None (metres not decoded)."""
    if not a or a & 0x40:
        return None
    if a & 0x10:
        n = ((a & 0x1F80) >> 2) | ((a & 0x20) >> 1) | (a & 0x0F)
        return n * 25 - 1000
    return mode_c(gillham(a))


def ac12(a):
    """ADS-B airborne position altitude -> feet, or None."""
    if not a:
        return None
    if a & 0x10:
        return (((a & 0xFE0) >> 1) | (a & 0x0F)) * 25 - 1000
    return mode_c(gillham(((a & 0xFC0) << 1) | (a & 0x3F)))


# ---------------------------------------------------------------- messages

def decode(msg):
    df = msg[0] >> 3
    m = {'df': df}
    if df in (17, 18, 11):
        m['icao'] = '%02X%02X%02X' % (msg[1], msg[2], msg[3])
    elif df in (0, 4, 5, 16, 20, 21):
        m['icao'] = '%06X' % residual(msg)
    if df == 11:
        m['ca'] = msg[0] & 7
        return m
    if df in (0, 4, 16, 20):
        m['alt'] = ac13(((msg[2] & 0x1F) << 8) | msg[3])
        return m
    if df in (5, 21):
        m['squawk'] = squawk(((msg[2] & 0x1F) << 8) | msg[3])
        return m
    if df not in (17, 18) or len(msg) < 14:
        return m
    if df == 18 and msg[0] & 7 not in (0, 1, 6):
        m['tisb'] = True            # TIS-B / ADS-R rebroadcasts: other formats
    v = int.from_bytes(msg[4:11], 'big')
    tc = v >> 51
    m['tc'] = tc
    if 1 <= tc <= 4:
        m['category'] = '%s%d' % ('DCBA'[tc - 1], field(v, 56, 6, 8))
        chars = ''.join(AIS[field(v, 56, 9 + 6 * i, 14 + 6 * i)] for i in range(8))
        m['callsign'] = chars.replace('#', '').strip()
    elif 9 <= tc <= 18 or 20 <= tc <= 22:
        if tc <= 18:
            m['alt'] = ac12(field(v, 56, 9, 20))
        m['cpr'] = (field(v, 56, 22, 22), field(v, 56, 23, 39), field(v, 56, 40, 56), False)
    elif 5 <= tc <= 8:
        mov = field(v, 56, 6, 12)
        if field(v, 56, 13, 13):
            m['track'] = field(v, 56, 14, 20) * 360 / 128
        if mov == 1:
            m['gs'] = 0
        elif 2 <= mov <= 124:
            # piecewise ground speed (kt)
            for lo, base, step in ((2, 0.125, 0.125), (9, 1, 0.25), (13, 2, 0.5), (39, 15, 1),
                                   (94, 70, 2), (109, 100, 5)):
                if mov >= lo:
                    gs = base + (mov - lo) * step
            m['gs'] = gs
        m['cpr'] = (field(v, 56, 22, 22), field(v, 56, 23, 39), field(v, 56, 40, 56), True)
        m['ground'] = True
    elif tc == 19:
        st = field(v, 56, 6, 8)
        if st in (1, 2):
            vew, vns = field(v, 56, 15, 24), field(v, 56, 26, 35)
            if vew and vns:
                k = 4 if st == 2 else 1
                vx = (vew - 1) * k * (-1 if field(v, 56, 14, 14) else 1)
                vy = (vns - 1) * k * (-1 if field(v, 56, 25, 25) else 1)
                m['gs'] = math.sqrt(vx * vx + vy * vy)
                m['track'] = math.degrees(math.atan2(vx, vy)) % 360
        elif st in (3, 4):
            if field(v, 56, 14, 14):
                m['heading'] = field(v, 56, 15, 24) * 360 / 1024
            a = field(v, 56, 26, 35)
            if a:
                m['tas' if field(v, 56, 25, 25) else 'ias'] = (a - 1) * (4 if st == 4 else 1)
        vr = field(v, 56, 38, 46)
        if vr:
            m['vr'] = (vr - 1) * 64 * (-1 if field(v, 56, 37, 37) else 1)
    elif tc == 28 and field(v, 56, 6, 8) == 1:
        e = field(v, 56, 9, 11)
        m['squawk'] = squawk(field(v, 56, 12, 24))
        if e:
            m['emergency'] = EMERGENCY[e]
    return m


# --------------------------------------------------------------------- CPR

def nl(lat):
    """Number of longitude zones at a latitude."""
    lat = abs(lat)
    if lat < 1e-6:
        return 59
    if lat > 87:
        return 1
    if lat == 87:
        return 2
    a = 1 - (1 - math.cos(math.pi / (2 * NZ))) / math.cos(math.pi * lat / 180) ** 2
    return int(2 * math.pi / math.acos(a))


def cpr_global(even, odd, newest_odd, surface=False, ref=None):
    """Position from an even and an odd frame (lat17, lon17 each): (lat,
    lon) or None. Surface frames cover a quarter of the world: ref (any
    position within ~45 degrees) picks the quadrant."""
    span = 90 if surface else 360
    lat0, lon0 = even[0] / 131072, even[1] / 131072
    lat1, lon1 = odd[0] / 131072, odd[1] / 131072
    j = math.floor(59 * lat0 - 60 * lat1 + 0.5)
    rlat0 = span / 60 * (j % 60 + lat0)
    rlat1 = span / 59 * (j % 59 + lat1)
    if surface:
        if ref is None:
            return None
        # the northern or southern answer, whichever is nearer the reference
        if abs(rlat0 - 90 - ref[0]) < abs(rlat0 - ref[0]):
            rlat0 -= 90
            rlat1 -= 90
    else:
        if rlat0 >= 270:
            rlat0 -= 360
        if rlat1 >= 270:
            rlat1 -= 360
    if not -90 <= rlat0 <= 90 or not -90 <= rlat1 <= 90:
        return None
    if nl(rlat0) != nl(rlat1):
        return None
    if newest_odd:
        lat, n, lonx = rlat1, max(nl(rlat1) - 1, 1), lon1
    else:
        lat, n, lonx = rlat0, max(nl(rlat0), 1), lon0
    m = math.floor(lon0 * (nl(lat) - 1) - lon1 * nl(lat) + 0.5)
    lon = span / n * (m % n + lonx)
    if surface:
        # four answers 90 degrees apart: the nearest the reference
        best = None
        for k in range(4):
            c = (lon + 90 * k + 180) % 360 - 180
            d = abs((c - ref[1] + 180) % 360 - 180)
            if best is None or d < best[0]:
                best = (d, c)
        lon = best[1]
    elif lon >= 180:
        lon -= 360
    return lat, lon


def cpr_local(cpr, ref):
    """Position from one frame and a reference within 180 NM (45 NM on the
    surface): (lat, lon)."""
    odd, ylat, xlon, surface = cpr
    span = 90 if surface else 360
    dlat = span / (60 - odd)
    yz = ylat / 131072
    j = math.floor(ref[0] / dlat) + math.floor(0.5 + (ref[0] % dlat) / dlat - yz)
    lat = dlat * (j + yz)
    n = nl(lat) - odd
    dlon = span / n if n > 0 else span
    xz = xlon / 131072
    m = math.floor(ref[1] / dlon) + math.floor(0.5 + (ref[1] % dlon) / dlon - xz)
    lon = dlon * (m + xz)
    return lat, lon


def distance_km(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742 * math.asin(min(1, math.sqrt(h)))


def bearing(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(y, x)) % 360


# ---------------------------------------------------------------- aircraft

class Aircraft:
    """One aircraft: what its messages have said."""

    def __init__(self, icao):
        self.icao = icao
        self.callsign = None
        self.category = None
        self.alt = None
        self.gs = None
        self.track = None
        self.vr = None
        self.squawk = None
        self.emergency = None
        self.ground = False
        self.lat = self.lon = None
        self.pos_t = None
        self.first = None
        self.seen = None
        self.messages = 0
        self.positions = 0
        self.signal = None         # dBFS of the last message
        self.even = self.odd = None  # (lat17, lon17, t, surface)
        self.trail = []            # recent (lat, lon)

    def update(self, m, now, home=None):
        """Merge decoded message m (heard at monotonic time now). Returns
        True if this gave a new position."""
        self.seen = now
        if self.first is None:
            self.first = now
        self.messages += 1
        for k in ('callsign', 'category', 'alt', 'gs', 'track', 'vr', 'squawk'):
            if m.get(k) is not None:
                setattr(self, k, m[k])
        if 'heading' in m and self.track is None:
            self.track = m['heading']
        if m.get('emergency'):
            self.emergency = m['emergency']
        if 'cpr' in m:
            self.ground = m['cpr'][3]
            return self._position(m['cpr'], now, home)
        if m.get('tc') in (9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19):
            self.ground = False
        return False

    def _position(self, cpr, now, home):
        odd, lat17, lon17, surface = cpr
        frame = (lat17, lon17, now, surface)
        if odd:
            self.odd = frame
        else:
            self.even = frame
        pos = None
        e, o = self.even, self.odd
        recent = self.lat is not None and now - self.pos_t < LOCAL_MAX_AGE
        ref = (self.lat, self.lon) if recent else home
        if e and o and e[3] == o[3] == surface and abs(e[2] - o[2]) <= CPR_MAX_AGE:
            pos = cpr_global(e[:2], o[:2], odd, surface, ref)
        if pos is None and ref is not None:
            pos = cpr_local(cpr, ref)
        if pos is None:
            return False
        if home is not None and distance_km(home, pos) > MAX_RANGE_KM:
            return False   # (home: the tracker's reference, home or a first fix)
        if self.lat is not None and now - self.pos_t < 60:
            if distance_km((self.lat, self.lon), pos) > 2 + MAX_SPEED_KMS * (now - self.pos_t):
                return False
        if self.lat is not None:
            self.trail.append((self.lat, self.lon))
            if len(self.trail) > 30:
                self.trail.pop(0)
        self.lat, self.lon = pos
        self.pos_t = now
        self.positions += 1
        return True

    def json(self, now, home=None):
        d = {'icao': self.icao, 'msgs': self.messages, 'age': round(now - self.seen, 1)}
        for k in ('callsign', 'category', 'alt', 'squawk', 'emergency', 'vr'):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if self.gs is not None:
            d['gs'] = round(self.gs)
        if self.track is not None:
            d['track'] = round(self.track)
        if self.ground:
            d['ground'] = True
        if self.lat is not None:
            d['lat'] = round(self.lat, 5)
            d['lon'] = round(self.lon, 5)
            d['pos_age'] = round(now - self.pos_t, 1)
            if home is not None:
                d['km'] = round(distance_km(home, (self.lat, self.lon)), 1)
                d['bearing'] = round(bearing(home, (self.lat, self.lon)))
        if self.signal is not None:
            d['dbfs'] = round(self.signal, 1)
        return d


class Tracker:
    """The aircraft heard, by ICAO address."""

    def __init__(self, home=None, expire=300, reference=None):
        self.home = home
        self.expire = expire
        self.aircraft = {}
        # Where the receiver is, roughly: home, a given reference (the
        # map's centre), or else the first position
        # worked out from an even and an odd frame. Aircraft heard are
        # within ~200 km of it, so one frame and this reference give a
        # position (local CPR decoding is good to 180 NM).
        self.reference = home or reference

    def add(self, msg, now, dbfs=None):
        """A message (bytes) heard at now. Returns (decoded dict, Aircraft
        or None, new position?)."""
        m = decode(msg)
        icao = m.get('icao')
        if icao is None or m.get('tisb'):
            return m, None, False
        a = self.aircraft.get(icao)
        if a is None:
            a = self.aircraft[icao] = Aircraft(icao)
        if dbfs is not None:
            a.signal = dbfs
        moved = a.update(m, now, self.reference)
        if moved and self.reference is None and a.ground is False:
            self.reference = (a.lat, a.lon)
        return m, a, moved

    def clear(self):
        """Forget every aircraft (the reference stays)."""
        self.aircraft = {}

    def prune(self, now):
        for k in [k for k, a in self.aircraft.items() if now - a.seen > self.expire]:
            del self.aircraft[k]

    def sorted(self, now):
        """Most recently heard first."""
        return sorted(self.aircraft.values(), key=lambda a: -a.seen)
