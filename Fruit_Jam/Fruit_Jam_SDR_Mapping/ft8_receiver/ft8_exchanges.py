# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""FT8 exchanges (QSOs) heard recently, and where the stations are: what
the map display (ft8_display_map.py) draws.

parse(text) reads one message:

    CQ K1ABC FN42           a call: sender K1ABC, grid FN42
    CQ DX K1ABC FN42        (with a modifier)
    W5XYZ K1ABC FN42        K1ABC calls W5XYZ and sends its grid
    K1ABC W5XYZ R-12        W5XYZ answers K1ABC with a report
    W5XYZ K1ABC RR73        ...

as in ft8_farthest.py and ft8_explorer.html: the sender is the call
after CQ, otherwise the second word; the first word is who it is for.
Hashed calls ('<K6VHF/HR9>') count without the brackets; unresolved ones
('<...>') and free text are not calls.

Tracker keeps, by the log's UTC (seconds since 1970):

- every call's grid, from any message in which it sent one (its CQ, or
  its first reply), for GRID_SECONDS after it was last heard;
- the exchanges: a pair of calls with at least one message between them
  (in either direction), the time of the last one and its text. An
  exchange falls off keep seconds (KEEP_SECONDS) after its last message.

Plain Python: the same code runs on CircuitPython and on a PC.
"""
import maidenhead

KEEP_SECONDS = 180       # an exchange is shown this long after its last message
GRID_SECONDS = 6 * 3600  # a call's grid is remembered this long after it was last heard
MAX_CALLS = 1500         # calls remembered (the oldest half go when there are more)


def clean_call(word):
    """A callsign without hash brackets, or None if word is not one."""
    if not word:
        return None
    c = word[1:-1] if word[0] == '<' and word[-1] == '>' else word
    if not 3 <= len(c) <= 13 or maidenhead.is_grid(c) or c == 'RR73':
        return None
    letter = digit = False
    for ch in c:
        if 'A' <= ch <= 'Z':
            letter = True
        elif '0' <= ch <= '9':
            digit = True
        elif ch != '/':
            return None
    return c if letter and digit else None


def parse(text):
    """A message -> (to, sender, grid); any of them None. A CQ has no to."""
    words = text.split()
    if not words:
        return None, None, None
    to = None
    if words[0] in ('CQ', 'QRZ'):
        rest = words[1:]
        if len(rest) >= 2 and not maidenhead.is_grid(rest[1]):
            rest = rest[1:]                  # CQ DX, CQ POTA ...
        sender = clean_call(rest[0]) if rest else None
    elif len(words) >= 2:
        to = clean_call(words[0])
        sender = clean_call(words[1])
        if not sender:
            to = None
    else:
        return None, None, None
    grid = words[-1] if sender and len(words) >= 3 and maidenhead.is_grid(words[-1]) else None
    return to, sender, grid


def stamp_seconds(stamp):
    """'261020_125615' (WSJT-X's slot stamp) -> seconds since 1970 (UTC)."""
    # (70xxxx: 1970, from a board whose clock was not set)
    y, m, d = int(stamp[0:2]), int(stamp[2:4]), int(stamp[4:6])
    y += 1900 if y >= 70 else 2000
    # days since 1970-01-01 for (y, m, d)
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m - 3 if m > 2 else m + 9) + 2) // 5 + d - 1
    day = era * 146097 + yoe * 365 + yoe // 4 - yoe // 100 + doy - 719468
    return day * 86400 + int(stamp[7:9]) * 3600 + int(stamp[9:11]) * 60 + int(stamp[11:13])


class Exchange:
    """Messages between calls a and b (a < b)."""

    def __init__(self, a, b, t):
        self.a = a
        self.b = b
        self.first = t
        self.last = t            # the last message's time (its slot)
        self.messages = 0
        self.text = ''           # the last message
        self.sender = a          # ... its sender
        self.to = b              # ... and who it was for
        self.mine = False        # a message of it had my_call


class Tracker:

    def __init__(self, keep=KEEP_SECONDS, grid_seconds=GRID_SECONDS, max_calls=MAX_CALLS):
        self.keep = keep
        self.grid_seconds = grid_seconds
        self.max_calls = max_calls
        self.calls = {}          # call -> [grid, (lat, lon), last heard]
        self.exchanges = {}      # (a, b) -> Exchange
        self.version = 0         # goes up whenever what add() keeps changes

    def clear(self):
        """Forget the exchanges (the grids heard stay known)."""
        self.exchanges = {}
        self.version += 1

    def add(self, text, t, my_call=''):
        """A message heard at t (seconds since 1970): returns its Exchange,
        or None (a CQ, free text)."""
        to, sender, grid = parse(text)
        if sender is None:
            return None
        c = self.calls.get(sender)
        if grid:
            if c is None or c[0] != grid:
                if c is None and len(self.calls) >= self.max_calls:
                    self._forget()
                c = self.calls[sender] = [grid, maidenhead.to_latlon(grid), t]
                self.version += 1
        if c is not None:
            c[2] = max(c[2], t)
        if to is None or to == sender:
            return None
        key = (to, sender) if to < sender else (sender, to)
        e = self.exchanges.get(key)
        if e is None:
            e = self.exchanges[key] = Exchange(key[0], key[1], t)
        if t >= e.last:
            e.last = t
            e.text = text
            e.sender = sender
            e.to = to
        e.messages += 1
        if my_call and my_call in (to, sender):
            e.mine = True
        self.version += 1
        return e

    def _forget(self):
        """The oldest half of the calls (by when they were last heard)."""
        heard = sorted(c[2] for c in self.calls.values())
        cut = heard[len(heard) // 2]
        for call in [k for k, c in self.calls.items() if c[2] <= cut]:
            del self.calls[call]

    def where(self, call):
        """(lat, lon) of a call's grid, or None."""
        c = self.calls.get(call)
        return c[1] if c else None

    def grid(self, call):
        c = self.calls.get(call)
        return c[0] if c else None

    def current(self, now):
        """The exchanges with a message in the last keep seconds, the
        newest first."""
        out = [e for e in self.exchanges.values() if now - e.last <= self.keep]
        out.sort(key=lambda e: -e.last)
        return out

    def prune(self, now):
        """Forget exchanges past keep and grids past grid_seconds."""
        old = [k for k, e in self.exchanges.items() if now - e.last > self.keep]
        for k in old:
            del self.exchanges[k]
        for call in [k for k, c in self.calls.items() if now - c[2] > self.grid_seconds]:
            del self.calls[call]
        if old:
            self.version += 1
