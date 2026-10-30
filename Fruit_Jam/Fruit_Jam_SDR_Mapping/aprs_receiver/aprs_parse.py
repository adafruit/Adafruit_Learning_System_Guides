# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""AX.25 frames and APRS packets, decoded into dicts. Runs on CircuitPython
and on a PC (the tests use it there too).

ax25(frame) splits a frame (no FCS) into source, destination, path and
info; tnc2() formats it the usual way (SRC>DST,PATH:info), from_tnc2()
reads that back (a log replay). aprs(src, dst,
info) decodes the APRS part: position reports (plain, compressed, with
or without a timestamp), Mic-E (most mobile radios), objects, items,
messages, status, weather, telemetry and third-party packets. Unknown
or malformed parts are left as text: nothing here raises on bad input
(decode() catches what it does not expect).

Keys in the result (only those present): type, lat, lon (degrees, north /
east positive), sym (2 chars: table, code), course (degrees), speed
(km/h), alt (m), comment, name (object / item), killed, to / text / id
(message), status, wx {temp_c, wind_dir, wind_kmh, gust_kmh, rain_1h_mm,
humidity, pressure_hpa}, mice (Mic-E message), via (third-party header).
"""

# pylint: disable=too-many-return-statements, too-many-branches, too-many-locals
# pylint: disable=too-many-statements, unbalanced-tuple-unpacking

# Short words for the common symbols ('/' primary table, '\\' alternate).
SYMBOLS = {
    '/!': 'police', '/#': 'digi', '/$': 'phone', '/%': 'DX', '/&': 'HF gate', "/'": 'plane',
    '/(': 'mobile sat', '/)': 'wheelchair', '/*': 'snowmobile', '/+': 'red cross', '/,': 'scouts',
    '/-': 'house', '/.': 'X', '//': 'dot', '/0': 'circle', '/:': 'fire', '/;': 'camp',
    '/<': 'motorcycle', '/=': 'train', '/>': 'car', '/?': 'server', '/@': 'hurricane',
    '/A': 'aid stn', '/B': 'BBS', '/C': 'canoe', '/E': 'eyeball', '/F': 'tractor',
    '/G': 'grid sq', '/H': 'hotel', '/I': 'TCP/IP', '/K': 'school', '/L': 'PC user',
    '/M': 'MacAPRS', '/N': 'NTS stn', '/O': 'balloon', '/P': 'police', '/R': 'RV',
    '/S': 'shuttle', '/T': 'SSTV', '/U': 'bus', '/V': 'ATV', '/W': 'NWS', '/X': 'helicopter',
    '/Y': 'yacht', '/Z': 'WinAPRS', '/[': 'jogger', '/\\': 'triangle', '/]': 'mailbox',
    '/^': 'aircraft',
    '/_': 'weather', '/`': 'dish', '/a': 'ambulance', '/b': 'bicycle', '/c': 'command post',
    '/d': 'fire dept', '/e': 'horse', '/f': 'fire truck', '/g': 'glider', '/h': 'hospital',
    '/i': 'IOTA', '/j': 'jeep', '/k': 'truck', '/l': 'laptop', '/m': 'mic-rptr', '/n': 'node',
    '/o': 'EOC', '/p': 'dog', '/q': 'grid sq', '/r': 'repeater', '/s': 'ship', '/t': 'truck stop',
    '/u': 'semi', '/v': 'van', '/w': 'water', '/x': 'xAPRS', '/y': 'yagi', '/z': 'shelter',
    '\\#': 'digi', '\\&': 'gateway', '\\-': 'house', '\\>': 'car', '\\_': 'weather', '\\a': 'ARES',
    '\\k': 'SUV', '\\n': 'triangle', '\\r': 'restroom', '\\s': 'ship', '\\u': 'truck', '\\v': 'van',
    '\\j': 'jeep', '\\S': 'satellite', '\\0': 'circle', '\\y': 'skywarn', '\\W': 'NWS',
}

MICE_STD = ('Emergency', 'Priority', 'Special', 'Committed', 'Returning', 'In Service', 'En Route',
            'Off Duty')


def symbol_name(sym):
    if not sym or len(sym) != 2:
        return ''
    name = SYMBOLS.get(sym)
    if name is None and sym[0] not in '/\\':
        name = SYMBOLS.get('\\' + sym[1])       # an overlay character on the alternate table
    return name or ''


# ------------------------------------------------------------------ AX.25

def ax25(frame):
    """(src, dst, [path], info bytes) or None. A path entry ends in '*'
    when that digipeater has repeated the packet."""
    calls = []
    i = 0
    n = len(frame)
    while True:
        if i + 7 > n or len(calls) > 9:
            return None
        call = ''
        for k in range(6):
            c = frame[i + k] >> 1
            if c != 32:
                call += chr(c)
        ssid = (frame[i + 6] >> 1) & 15
        if ssid:
            call += '-%d' % ssid
        calls.append((call, frame[i + 6] & 0x80))
        last = frame[i + 6] & 1
        i += 7
        if last:
            break
    if len(calls) < 2 or i + 2 > n:
        return None
    # UI frames only (control 0x03, PID 0xF0, "no layer 3"), as APRS uses.
    if frame[i] & 0xef != 0x03 or frame[i + 1] != 0xf0:
        return None
    path = [c + ('*' if h else '') for c, h in calls[2:]]
    return calls[1][0], calls[0][0], path, bytes(frame[i + 2:])


def tnc2(src, dst, path, info):
    head = src + '>' + dst
    for p in path:
        head += ',' + p
    return head + ':' + text(info)


def text(b):
    """Bytes to printable text (control bytes as '.', the rest Latin-1)."""
    return ''.join(chr(c) if 32 <= c < 127 or c >= 160 else '.' for c in b)


# ------------------------------------------------------------------ APRS

def decode(frame):
    """A whole frame: dict with src, dst, path, raw (TNC2 text) and the
    APRS fields, or None if it is not an AX.25 UI frame."""
    head = ax25(frame)
    if not head:
        return None
    src, dst, path, info = head
    while info and info[-1] in (10, 13, 0):      # (many radios end with CR)
        info = info[:-1]
    out = {'src': src, 'dst': dst, 'path': path, 'raw': tnc2(src, dst, path, info)}
    try:
        out.update(aprs(src, dst, info))
    except (ValueError, IndexError, KeyError, TypeError, OverflowError, ZeroDivisionError):
        out['type'] = 'unparsed'
        out['comment'] = text(info)
    return out


def from_tnc2(raw):
    """A packet as tnc2() writes it (SRC>DST,PATH:info, a line of the log)
    -> the dict decode() gives, or None if it is not one."""
    gt = raw.find('>')
    colon = raw.find(':', gt)
    if gt < 1 or colon < 0:
        return None
    head = raw[:colon].split(',')
    src = raw[:gt]
    dst = head[0][gt + 1:]
    out = {'src': src, 'dst': dst, 'path': head[1:], 'raw': raw}
    try:
        # (text() kept each byte as one character: back to the bytes)
        out.update(aprs(src, dst, bytes(ord(c) & 255 for c in raw[colon + 1:])))
    except (ValueError, IndexError, KeyError, TypeError, OverflowError, ZeroDivisionError):
        out['type'] = 'unparsed'
        out['comment'] = raw[colon + 1:]
    return out


def aprs(src, dst, info):
    while info and info[-1] in (10, 13, 0):
        info = info[:-1]
    if not info:
        return {'type': 'empty'}
    t = chr(info[0])
    if t in '`\'\x1c\x1d':
        return mic_e(dst, info)
    s = text(info)
    if t in '!=':
        if len(s) > 1 and s[1] == '!':              # (a "!!" Ultimeter weather station)
            return {'type': 'weather', 'comment': s}
        r = position(s, 1)
        r['type'] = 'position'
        return r
    if t in '/@':
        r = position(s, 8)
        r['type'] = 'position'
        return r
    if t == ';':
        r = position(s, 18)
        r['type'] = 'object'
        r['name'] = s[1:10].rstrip()
        r['killed'] = s[10] == '_'
        return r
    if t == ')':
        end = min([k for k in (s.find('!', 1), s.find('_', 1)) if k > 0] or [len(s)])
        r = position(s, end + 1)
        r['type'] = 'item'
        r['name'] = s[1:end]
        r['killed'] = end < len(s) and s[end] == '_'
        return r
    if t == ':':
        return message(s)
    if t == '>':
        return {'type': 'status', 'status': s[1:]}
    if t == '_':
        return {'type': 'weather', 'wx': weather(s[9:])}
    if t == 'T':
        return {'type': 'telemetry', 'comment': s[1:]}
    if t == '}':
        inner = s[1:]
        colon = inner.find(':')
        gt = inner.find('>')
        if 0 < gt < colon:
            via = inner[:colon]
            isrc = inner[:gt]
            idst = inner[gt + 1:colon].split(',', 1)[0]
            r = aprs(isrc, idst, info[colon + 2:])
            r['via'] = via
            r['third_party'] = isrc
            return r
        return {'type': 'third party', 'comment': inner}
    if t == '<':
        return {'type': 'capabilities', 'comment': s[1:]}
    if t == '?':
        return {'type': 'query', 'comment': s}
    if t == '$':
        return {'type': 'NMEA', 'comment': s}
    # An object without its ';' (some repeater beacons, e.g. '442.700+
    # *111111z3856.83N/09244.74Wr T77'): decoded as the object it is.
    if len(s) > 17 and s[9] in '*_' and s[10:16].isdigit() and s[16] in 'zh/':
        try:
            return aprs(src, dst, b';' + info)
        except (ValueError, IndexError):
            pass
    return {'type': 'other', 'comment': s}


def message(s):
    to = s[1:10].strip()
    body = s[11:] if len(s) > 10 and s[10] == ':' else s[10:]
    r = {'type': 'message', 'to': to}
    if body.startswith('ack') or body.startswith('rej'):
        r['type'] = body[:3]
        r['id'] = body[3:].strip()
        return r
    brace = body.rfind('{')
    if brace >= 0:
        r['id'] = body[brace + 1:].strip()
        body = body[:brace]
    if to.startswith('BLN'):
        r['type'] = 'bulletin'
    r['text'] = body
    return r


def position(s, at):
    """Position starting at s[at] (uncompressed or compressed), then the
    symbol and comment."""
    r = {}
    if len(s) <= at:
        return r
    c = s[at]
    if c.isdigit() or c == ' ':
        lat = s[at:at + 8]
        table = s[at + 8]
        lon = s[at + 9:at + 18]
        code = s[at + 18]
        r['lat'] = latlon(lat[:2], lat[2:7], lat[7])
        r['lon'] = latlon(lon[:3], lon[3:8], lon[8])
        r['sym'] = table + code
        comment = s[at + 19:]
        # Course/speed (knots) or other 7-byte data extensions.
        if (len(comment) >= 7 and comment[3] == '/' and comment[:3].isdigit()
                and comment[4:7].isdigit()):
            if code != '_':
                r['course'] = int(comment[:3])
                r['speed'] = round(int(comment[4:7]) * 1.852)
                comment = comment[7:]
    else:
        table = c
        r['lat'] = 90 - base91(s[at + 1:at + 5]) / 380926
        r['lon'] = -180 + base91(s[at + 5:at + 9]) / 190463
        code = s[at + 9]
        r['sym'] = table + code
        cs, typ = s[at + 10:at + 12], s[at + 12] if len(s) > at + 12 else ' '
        if len(cs) == 2 and cs[0] != ' ':
            tbits = ord(typ) - 33
            if tbits & 0x18 == 0x10:
                r['alt'] = round(1.002 ** base91(cs) * 0.3048)
            elif cs[0] != '{':
                r['course'] = (ord(cs[0]) - 33) * 4
                r['speed'] = round((1.08 ** (ord(cs[1]) - 33) - 1) * 1.852)
        comment = s[at + 13:]
    if r.get('sym', ' _')[1] == '_' and comment:
        r['wx'] = weather(comment)
        return r
    alt = comment.find('/A=')
    if alt >= 0 and comment[alt + 3:alt + 9].lstrip('-').isdigit():
        r['alt'] = round(int(comment[alt + 3:alt + 9]) * 0.3048)
        comment = comment[:alt] + comment[alt + 9:]
    comment = extras(comment)
    if comment.strip():
        r['comment'] = comment.strip()
    return r


def latlon(deg, mins, hemi):
    """'39', '04.32', 'N' -> 39.072 (spaces of position ambiguity read as 0)."""
    v = int(deg.replace(' ', '0')) + float(mins.replace(' ', '0')) / 60
    if hemi in 'SsWw':
        v = -v
    elif hemi not in 'NnEe':
        raise ValueError(hemi)
    return v


def base91(s):
    v = 0
    for c in s:
        v = v * 91 + ord(c) - 33
    return v


def weather(s):
    """'220/004g005t077r000p000P000h50b09900' -> dict (metric)."""
    wx = {}
    i = 0
    if len(s) >= 7 and s[3] == '/':
        if s[:3].isdigit():
            wx['wind_dir'] = int(s[:3])
        if s[4:7].isdigit():
            wx['wind_kmh'] = round(int(s[4:7]) * 1.609)
        i = 7
    fields = {'c': 3, 's': 3, 'g': 3, 't': 3, 'r': 3, 'p': 3, 'P': 3, 'h': 2, 'b': 5,
              'L': 3, 'l': 3}
    while i < len(s) and s[i] in fields:
        k = s[i]
        v = s[i + 1:i + 1 + fields[k]]
        i += 1 + fields[k]
        try:
            n = int(v)
        except ValueError:
            continue
        if k == 'c':
            wx['wind_dir'] = n
        elif k == 's':
            wx['wind_kmh'] = round(n * 1.609)
        elif k == 'g':
            wx['gust_kmh'] = round(n * 1.609)
        elif k == 't':
            wx['temp_c'] = round((n - 32) * 5 / 9, 1)
        elif k == 'r':
            wx['rain_1h_mm'] = round(n * 0.254, 1)
        elif k == 'h':
            wx['humidity'] = 100 if n == 0 else n
        elif k == 'b':
            wx['pressure_hpa'] = n / 10
    return wx


def mic_e(dst, info):
    """Mic-E: latitude and message bits in the destination field,
    longitude, speed and course in the info field."""
    d = dst.split('-')[0]
    if len(d) != 6 or len(info) < 9:
        raise ValueError('short Mic-E')
    digits = ''
    bits = []
    for k, c in enumerate(d):
        if '0' <= c <= '9':
            digits += c
            bits.append(0)
        elif 'A' <= c <= 'J':
            digits += chr(ord(c) - 17)
            bits.append(2)
        elif 'P' <= c <= 'Y':
            digits += chr(ord(c) - 32)
            bits.append(1)
        elif c in 'KLZ':
            digits += '0'
            bits.append({'K': 2, 'L': 0, 'Z': 1}[c])
        else:
            raise ValueError('Mic-E destination')
    north = bits[3] == 1
    lon_100 = bits[4] == 1
    west = bits[5] == 1
    lat = int(digits[:2]) + float(digits[2:4] + '.' + digits[4:6]) / 60
    if not north:
        lat = -lat
    deg = info[1] - 28 + (100 if lon_100 else 0)
    if 180 <= deg <= 189:
        deg -= 80
    elif 190 <= deg <= 199:
        deg -= 190
    mins = info[2] - 28
    if mins >= 60:
        mins -= 60
    lon = deg + (mins + (info[3] - 28) / 100) / 60
    if west:
        lon = -lon
    sp, dc, se = info[4] - 28, info[5] - 28, info[6] - 28
    speed = sp * 10 + dc // 10
    if speed >= 800:
        speed -= 800
    course = (dc % 10) * 100 + se
    if course >= 400:
        course -= 400
    r = {'type': 'mic-e', 'lat': lat, 'lon': lon, 'sym': chr(info[8]) + chr(info[7]),
         'speed': round(speed * 1.852), 'course': course}
    a, b, c = bits[:3]
    if 2 in (a, b, c):
        custom = 7 - ((a > 0) * 4 + (b > 0) * 2 + (c > 0))
        r['mice'] = 'Custom-%d' % custom if a | b | c else 'Emergency'
    else:
        r['mice'] = MICE_STD[a * 4 + b * 2 + c]
    comment = text(info[9:])
    # Altitude: 3 base-91 digits and '}' (metres + 10000), often after a
    # radio type byte.
    k = comment.find('}')
    if k >= 3:
        r['alt'] = base91(comment[k - 3:k]) - 10000
        comment = comment[:k - 3] + comment[k + 1:]
    # Radio type codes (Kenwood '>' ']', Yaesu '`..._x' etc.): not comment.
    if comment[:1] in ('>', ']'):
        comment = comment[1:]
        if comment[-1:] == '=' or comment[-1:] == '^':
            comment = comment[:-1]
    elif comment[:1] == '`' or comment[:1] == "'":
        comment = comment[1:]
        if len(comment) >= 2 and comment[-2] == '_':
            comment = comment[:-2]
    if comment[-2:] in ('|3', '|4'):             # (Byonics TinyTrack 3 / 4)
        comment = comment[:-2]
    comment = extras(comment)
    if comment.strip():
        r['comment'] = comment.strip()
    return r


def extras(comment):
    """The comment without base-91 telemetry (|ss11|) and the !DAO!
    precision extension."""
    a = comment.find('|')
    b = comment.find('|', a + 1) if a >= 0 else -1
    if 0 <= a < b and (b - a - 1) in (4, 6, 8, 10, 12, 14):
        comment = comment[:a] + comment[b + 1:]
    k = comment.find('!')
    if k >= 0 and len(comment) >= k + 5 and comment[k + 4] == '!' and comment[k + 1] in 'wWT':
        comment = comment[:k] + comment[k + 5:]
    return comment


# --------------------------------------------------------------- summary

def summary(p, width=40):
    """One short line about a decoded packet (for the screen)."""
    t = p.get('type')
    parts = []
    if p.get('name'):
        parts.append(('x ' if p.get('killed') else '') + p['name'])
    if 'lat' in p:
        parts.append('%.3f%s %.3f%s' % (abs(p['lat']), 'N' if p['lat'] >= 0 else 'S',
                                        abs(p['lon']), 'E' if p['lon'] >= 0 else 'W'))
    if p.get('speed'):
        parts.append('%dkm/h' % p['speed'])
    if t in ('message', 'bulletin'):
        parts.append('>%s %s' % (p.get('to', ''), p.get('text', '')))
    elif t in ('ack', 'rej'):
        parts.append('%s %s to %s' % (t, p.get('id', ''), p.get('to', '')))
    elif t == 'status':
        parts.append(p.get('status', ''))
    wx = p.get('wx')
    if wx:
        w = []
        if 'temp_c' in wx:
            w.append('%.0fC' % wx['temp_c'])
        if 'wind_kmh' in wx:
            w.append('%dkm/h' % wx['wind_kmh'])
        if 'humidity' in wx:
            w.append('%d%%' % wx['humidity'])
        if 'pressure_hpa' in wx:
            w.append('%.0fhPa' % wx['pressure_hpa'])
        parts.append('WX ' + ' '.join(w))
    elif t not in ('message', 'bulletin', 'status', 'ack', 'rej'):
        name = symbol_name(p.get('sym'))
        if name:
            parts.append(name)
        if p.get('comment'):
            parts.append(p['comment'])
        elif p.get('mice') and p['mice'] != 'Off Duty':
            parts.append(p['mice'])
    line = ' '.join(parts) if parts else (t or '')
    return line[:width]
