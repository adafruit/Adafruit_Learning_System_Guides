# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared game state for online games between two boards over Adafruit IO.

Network code lives in chess_net. Each player publishes to a public feed on
their own Adafruit IO account ("user/feed", default feed "cpchess") and reads
the opponent's. Every message holds the whole game, so a board that restarted
or missed a message only needs the newest value of each feed:

  {"v": 1,                protocol version
   "g": 7,                game number (a new game uses the highest seen + 1)
   "c": "alice/cpchess",  who started the game (breaks ties in "g")
   "w": "alice/cpchess",  white
   "b": "bob/cpchess",    black
   "n": 23,               plies played since the start
   "f": "<FEN>",          position before the moves in "m" ("" = start position)
   "m": "e2e4 e7e5",      UCI moves since "f"
   "by": "bob/cpchess"}   who sent it

"f" advances at every pawn move or capture, since earlier positions can't repeat
after one. This keeps "m" short enough to fit a feed value's 1 KB limit while
still giving the engine every position needed to detect repetition draws.

The newest state wins, compared by key() = (g, c, n): a new game beats any move
of an older one, simultaneous new games are ordered by creator name (both boards
agree), and within a game the longer move list wins.
"""

import json

PROTOCOL = 1
DEFAULT_FEED = "cpchess"
WHITE, BLACK = 0, 1


def parse_id(text, default_feed=DEFAULT_FEED):
    """'bob' or 'bob/feed' -> ('bob', 'feed'). Usernames keep their case for use
    in URLs and MQTT topics; use norm() to compare ids."""
    text = (text or "").strip().strip("/")
    if not text:
        return None
    if "/" in text:
        user, feed = text.split("/", 1)
    else:
        user, feed = text, default_feed
    return user, (feed or default_feed).lower()


def norm(user, feed):
    return (user + "/" + feed).lower()


class State:
    def __init__(self, g, c, w, b, n=0, f="", m=None, by=""):
        self.g, self.c, self.w, self.b = g, c, w, b
        self.n, self.f = n, f
        self.m = m if m is not None else []
        self.by = by

    def key(self):
        return (self.g, self.c, self.n)

    def same_game(self, other):
        return other is not None and self.g == other.g and self.c == other.c

    def colour_of(self, who):
        """WHITE, BLACK or None."""
        if who == self.w:
            return WHITE
        if who == self.b:
            return BLACK
        return None

    def to_json(self):
        return json.dumps(
            {
                "v": PROTOCOL,
                "g": self.g,
                "c": self.c,
                "w": self.w,
                "b": self.b,
                "n": self.n,
                "f": self.f,
                "m": " ".join(self.m),
                "by": self.by,
            }
        )

    @staticmethod
    def from_json(text):
        """Parses a feed value. Returns a State, or None if it isn't a valid one."""
        try:
            d = json.loads(text)
            if d.get("v") != PROTOCOL:
                return None
            s = State(
                int(d["g"]),
                str(d["c"]),
                str(d["w"]),
                str(d["b"]),
                int(d["n"]),
                str(d.get("f", "")),
                str(d.get("m", "")).split(),
                str(d.get("by", "")),
            )
        except (ValueError, TypeError, KeyError, AttributeError):
            return None
        if s.g < 0 or s.n < 0 or s.w == s.b or len(s.m) > s.n:
            return None
        return s

    def after(self, uci, fen_before, irreversible, by):
        """The state after one more move. If the move is irreversible (pawn move
        or capture), fen_before becomes the new base position."""
        if irreversible:
            f, m = fen_before, [uci]
        else:
            f, m = self.f, self.m + [uci]
        return State(self.g, self.c, self.w, self.b, self.n + 1, f, m, by)

    def __repr__(self):
        return "State(g=%d c=%s n=%d w=%s b=%s last=%s)" % (
            self.g,
            self.c,
            self.n,
            self.w,
            self.b,
            self.m[-1] if self.m else "-",
        )


class Online:
    """This board's view of the online game, shared by chess_ctrl and chess_net.

    me, opp: ('user', 'feed') for this board and the opponent, or None if not
    set in settings.toml (error then says what is missing)."""

    def __init__(self, me, opp, error=None):
        self.me, self.opp = me, opp
        self.me_id = norm(*me) if me else ""
        self.opp_id = norm(*opp) if opp else ""
        self.error = error
        if not error and self.me_id == self.opp_id:
            self.error = "Opponent is this board's own feed"
        self.state = None  # newest State of our game with the opponent
        self.outbox = None  # our newest State not yet published
        self.max_g = 0  # highest game number seen on either feed
        self.synced = False  # both feeds have been read since start-up
        self.status = "Not connected"
        self.status_bad = False
        self.connected = False
        # the opponent's newest state is a game with someone else
        self.opp_elsewhere = False

    @property
    def configured(self):
        return self.error is None

    def opp_name(self):
        """The opponent's display name: username, plus feed if not the default."""
        if not self.opp:
            return "?"
        user, feed = self.opp
        return user if feed == DEFAULT_FEED else user + "/" + feed

    def opp_short(self):
        """The opponent's username cut to 8 characters, so a status line with a
        move still fits the shield's 72 px panel."""
        if not self.opp:
            return "?"
        user = self.opp[0]
        return user if len(user) <= 8 else user[:7] + "."

    def involves_us(self, s):
        return {s.w, s.b} == {self.me_id, self.opp_id}

    def offer(self, s, from_opp=True):
        """Checks a state read from a feed. Returns True if it is a game between
        us and the opponent and newer than ours."""
        if s is None:
            return False
        self.max_g = max(self.max_g, s.g)
        if not self.involves_us(s):
            if from_opp:
                self.opp_elsewhere = True
            return False
        if from_opp:
            self.opp_elsewhere = False
        if self.state is not None and s.key() <= self.state.key():
            return False
        return True

    def new_game(self, white):
        """Starts a new game from this board, playing white if white is True."""
        g = self.max_g + 1
        self.max_g = g
        w, b = (self.me_id, self.opp_id) if white else (self.opp_id, self.me_id)
        s = State(g, self.me_id, w, b, 0, "", [], self.me_id)
        self.state = self.outbox = s
        return s

    def moved(self, s):
        """Records our move's new state and queues it to send."""
        self.state = self.outbox = s

    def colour(self):
        return self.state.colour_of(self.me_id) if self.state else None
