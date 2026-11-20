# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=attribute-defined-outside-init, import-outside-toplevel
# pylint: disable=too-many-branches, too-many-public-methods, too-many-return-statements
"""Game logic: turns, piece selection, hints, undo, menus and dialogs.

Contains no display code. The view reads the Controller's attributes and draws
them; taps arrive through tap_square(), choose_promotion() and dialog_action().
While searching() is True, call step() from the main loop to run the engine.

Game modes (self.players):
  1       one person against the engine (colour and level from settings)
  2       two people taking turns on one screen (the engine only gives hints)
  ONLINE  against another board over Adafruit IO (state in chess_online,
          transport in chess_net); while the opponent is to move the mode is
          REMOTE and taps on the board are ignored

Squares are 0-63 with a1 = 0. Board codes match _chess_engine.board():
0 empty, 1-6 white P N B R Q K, 9-14 black.
"""

# Engine settings
DEFAULT_LEVEL = 10
MAX_LEVEL = 20
HINT_TIME_MS = 2000
ENGINE_NAME = "Computer"
ENGINE_SHORT = "CPU"

# Score constants; these must match the engine's
VALUE_MATE = 32000
VALUE_MATE_IN_MAX_PLY = VALUE_MATE - 64
PAWN_VALUE_EG = 213

# Results from _chess_engine.result()
ONGOING, WHITE_MATES, BLACK_MATES, STALEMATE, FIFTY, REPETITION, MATERIAL = range(7)

# Modes (REMOTE: waiting for the other board's move in an online game)
PLAYER, ENGINE, HINT, OVER, REMOTE = range(5)

# Value of Controller.players for an online game
ONLINE = 3

DRAW_REASONS = {
    STALEMATE: "Stalemate",
    FIFTY: "50-move rule",
    REPETITION: "Repetition",
    MATERIAL: "Material",
}

PROMOTION_NEEDED = 1
WHITE, BLACK = 0, 1


def engine_time_ms(level):
    """Engine thinking time per move at a level."""
    return 500 + level * 125


def square(name):
    """'e4' -> 28."""
    return (ord(name[0]) - 97) + 8 * (ord(name[1]) - 49)


def colour_of(code):
    return BLACK if code & 8 else WHITE


def format_eval(score_white):
    """Engine score from white's side -> '+0.35', '-M3', '#'."""
    if abs(score_white) >= VALUE_MATE_IN_MAX_PLY:
        plies = VALUE_MATE - abs(score_white)
        if plies == 0:
            return "#"
        return "%sM%d" % ("+" if score_white > 0 else "-", (plies + 1) // 2)
    cp = (
        score_white * 100 // PAWN_VALUE_EG
        if score_white >= 0
        else -((-score_white) * 100 // PAWN_VALUE_EG)
    )
    return "%s%d.%02d" % ("+" if cp >= 0 else "-", abs(cp) // 100, abs(cp) % 100)


def eval_share(score_white):
    """White's share of the eval bar, 0 to 1."""
    if abs(score_white) >= VALUE_MATE_IN_MAX_PLY:
        return 1.0 if score_white > 0 else 0.0
    return 0.5 + 0.5 * score_white / (abs(score_white) + 600)


class Controller:
    def __init__(self, tf, stack, settings, now_ms, menu=False, online=None):
        """tf: the engine module. stack: bytearray for the search. settings: a
        chess_settings.Settings. now_ms: function returning milliseconds.
        menu: True starts at the menu, "online" starts at the online dialog (which
        resumes the online game once the feeds are read), False starts a
        one-player game. online: a chess_online.Online, or None."""
        self.tf = tf
        self.stack = stack
        self.settings = settings
        self.now_ms = now_ms
        self.board = bytearray(64)
        self.version = 0  # incremented on every change the view must redraw
        self.flash = None  # button the view should show pressed this frame
        self.log = None  # optional function(str) for console messages
        self.players = 1  # 1, 2 or ONLINE
        # open dialog: None, "menu", "new" or "online"
        self.dialog = ("online" if menu == "online" else "menu") if menu else None
        self.online = online
        self.online_white = True  # colour picked in the online dialog
        self.auto_resume = menu == "online"  # resume the online game once synced
        self.remote_san = ""  # the other board's last move (SAN)
        self._shown = None  # the online State currently loaded in the engine
        self.mode = PLAYER
        self.menu_cancel = False  # menu can be closed (a game is in progress)
        self.dialog_back = False  # new-game dialog's cancel returns to the menu
        self.dialog_white = True
        self.dialog_level = DEFAULT_LEVEL
        self.new_game()

    # ------------------------------------------------------------ state helpers

    def _changed(self):
        self.version += 1

    def _say(self, text):
        if self.log:
            self.log(text)  # pylint: disable=not-callable

    @property
    def human(self):
        """The colour the local player moves (with two players, the side to move)."""
        if self.players == 2:
            return self.side
        if self.players == ONLINE:
            c = self.online.colour()
            return WHITE if c is None else c
        return WHITE if self.settings.human_white else BLACK

    @property
    def flipped(self):
        if self.players == ONLINE:
            return self.human == BLACK
        return self.players == 1 and not self.settings.human_white

    def searching(self):
        return self.mode in (ENGINE, HINT)

    def _sync(self):
        """Copies what the view needs from the engine. Not for use mid-search."""
        tf = self.tf
        tf.board(self.board)
        self.ply = tf.ply()
        self.side = tf.side_to_move()
        self.check_sq = tf.check_square()
        self.result = tf.result()
        self.material = (tf.material(WHITE), tf.material(BLACK))
        last = tf.last_move()
        if last:
            self.last_from, self.last_to = square(last[0:2]), square(last[2:4])
        else:
            self.last_from = self.last_to = -1

    def _clear_selection(self):
        self.selected = -1
        self.targets = ()

    def can_undo(self):
        if self.searching() or self.dialog or self.players == ONLINE:
            return False
        return self.ply >= (1 if self.players == 2 or self.human == WHITE else 2)

    def can_hint(self):
        return self.mode == PLAYER and not self.dialog

    # ------------------------------------------------------------ game flow

    def _stop_search(self):
        tf = self.tf
        if tf.thinking():
            tf.think_stop()
            while tf.think_step(1000) is None:
                pass
        if self.searching():
            self.mode = PLAYER

    def new_game(self):
        tf = self.tf
        self._stop_search()
        tf.reset()
        tf.new_game()
        self._shown = None
        self._reset_game_info()
        self._sync()
        if self.players == 2:
            self._say("New game: two players")
        else:
            self._say(
                "New game: player has %s, level %d"
                % ("white" if self.human == WHITE else "black", self.settings.level)
            )
        self._after_move()

    def _reset_game_info(self):
        self._clear_selection()
        self.promo = None  # (from, to) while the promotion picker is open
        self.hint_from = self.hint_to = -1
        self.hint_san = ""
        self.engine_san = ""
        self.has_eval = False
        self.eval_white = 0
        self.search_info = ""  # depth / nodes / speed of the last search
        self.search_start = 0
        self.search_ms = 0
        self.stop_requested = False
        self.remote_san = ""

    def _after_move(self):
        self._clear_selection()
        self.promo = None
        if self.result != ONGOING:
            self.mode = OVER
        elif self.players == ONLINE:
            self.mode = PLAYER if self.side == self.human else REMOTE
        elif self.side == self.human or self.dialog in ("menu", "online"):
            # with the menu open the engine waits until a game is chosen
            self.mode = PLAYER
        else:
            self._start_search(ENGINE)
        self._changed()

    def _start_search(self, kind):
        level = self.settings.level
        if kind == ENGINE:
            movetime = engine_time_ms(level)
            depth = level + 1 if level < MAX_LEVEL else 0
            skill = level
        else:
            movetime, depth, skill = HINT_TIME_MS, 0, MAX_LEVEL
        self.tf.think_start(self.stack, skill, movetime, depth)
        self.mode = kind
        self.search_start = self.now_ms()
        self.search_ms = movetime
        self.stop_requested = False

    def progress(self):
        """Fraction of the search time used so far, 0 to 1."""
        if not self.searching() or self.search_ms <= 0:
            return 0.0
        p = (self.now_ms() - self.search_start) / self.search_ms
        return 0.0 if p < 0 else 1.0 if p > 1 else p

    def step(self, budget_ms):
        """Runs the engine for up to budget_ms. Returns True if the search finished."""
        if not self.searching():
            return False
        r = self.tf.think_step(budget_ms)
        if r is None:
            return False
        self._finish_search(r)
        return True

    def _finish_search(self, r):
        best, _ponder, score, depth, nodes, ms = r
        kind = self.mode
        nps = nodes * 1000 // ms if ms else 0
        self.search_info = "Depth %d  %s nodes  %s/s" % (depth, _k(nodes), _k(nps))
        self._say(
            "%s: %s  score %d  depth %d  nodes %d  %d ms  (%d nodes/s)"
            % (
                "Engine" if kind == ENGINE else "Hint",
                best,
                score,
                depth,
                nodes,
                ms,
                nps,
            )
        )
        self.mode = PLAYER  # _after_move() sets the real mode
        if not best or best == "0000":
            self._sync()
            self._after_move()
            return
        # The engine's score is from the side to move's point of view
        self.has_eval = True
        self.eval_white = score if self.tf.side_to_move() == WHITE else -score
        san = self.tf.san(best)
        if kind == HINT:
            self.hint_san = san
            self.hint_from, self.hint_to = square(best[0:2]), self._display_to(best)
            self._changed()
            return
        self.engine_san = san
        self.tf.push(best)
        self._sync()
        self._after_move()

    @staticmethod
    def _display_to(uci):
        # castling is shown by the king's destination, as in UCI
        return square(uci[2:4])

    def stop(self):
        """MOVE NOW: asks the engine to finish its search early."""
        if self.searching() and not self.stop_requested:
            self.tf.think_stop()
            self.stop_requested = True
            self._changed()

    def _player_move(self, uci):
        san = self.tf.san(uci)
        if self.players == 2:
            self._say("%s: %s" % ("White" if self.side == WHITE else "Black", san))
        else:
            self._say("You: %s" % san)
        if self.players == ONLINE:
            # a pawn move or capture restarts the online state's move list
            frm, to = square(uci[0:2]), square(uci[2:4])
            irreversible = (self.board[frm] & 7) == 1 or self.board[to] != 0
            o = self.online
            o.moved(o.state.after(uci, self.tf.fen(), irreversible, o.me_id))
        self.tf.push(uci)
        self.hint_from = self.hint_to = -1
        self.hint_san = ""
        self._sync()
        self._after_move()

    def undo(self):
        if not self.can_undo():
            return False
        # Take back moves until one of the player's own moves is undone
        # (with two players, just the last move)
        tf = self.tf
        while tf.ply() > 0:
            mover = 1 - tf.side_to_move()
            tf.pop()
            if self.players == 2 or mover == self.human:
                break
        self.hint_from = self.hint_to = -1
        self.hint_san = self.engine_san = ""
        self.has_eval = False
        self._sync()
        self._say("Move taken back")
        self._after_move()
        return True

    def hint(self):
        if not self.can_hint():
            return False
        self._clear_selection()
        self.promo = None
        self._start_search(HINT)
        self._changed()
        return True

    # ------------------------------------------------------------ taps

    def tap_square(self, s):
        """Handles a tap on square s. Returns 'ok', 'warn' (illegal) or None (ignored)."""
        if self.mode != PLAYER or self.dialog:
            return None
        if self.promo:  # tapping the board cancels the promotion
            self.promo = None
            self._clear_selection()
            self._changed()
            return "ok"
        code = self.board[s]
        own = code and colour_of(code) == self.human
        targets = self.tf.targets(s) if own else ()
        if self.selected < 0:
            if targets:
                self.selected, self.targets = s, targets
                self._changed()
                return "ok"
            return "warn"
        if s == self.selected:  # tapping the selected piece deselects it
            self._clear_selection()
            self._changed()
            return "ok"
        if s in self.targets:
            m = self.tf.find_move(self.selected, s)
            if m == PROMOTION_NEEDED:
                self.promo = (self.selected, s)
                self._changed()
                return "ok"
            if m:
                self._player_move(m)
                return "ok"
        if targets:  # another of our pieces: select it instead
            self.selected, self.targets = s, targets
            self._changed()
            return "ok"
        self._clear_selection()
        self._changed()
        return "warn"

    def choose_promotion(self, piece):
        """piece: 'q', 'r', 'b' or 'n'."""
        if not self.promo:
            return False
        frm, to = self.promo
        m = self.tf.find_move(frm, to, piece)
        self.promo = None
        if m and m != PROMOTION_NEEDED:
            self._player_move(m)
        else:
            self._changed()
        return True

    # ------------------------------------------------------------ menu and new game dialog

    def open_menu(self):
        """NEW GAME: opens the menu over the current game."""
        if self.searching():
            return False
        self.dialog = "menu"
        self.menu_cancel = True
        self.promo = None
        self._clear_selection()
        self._changed()
        return True

    def open_dialog(self, back=False):
        """Opens the one-player new-game dialog (colour, level). With back=True,
        its cancel button returns to the menu."""
        if self.searching():
            return False
        self.dialog = "new"
        self.dialog_back = back
        self.dialog_white = self.settings.human_white
        self.dialog_level = self.settings.level
        self.promo = None
        self._clear_selection()
        self._changed()
        return True

    def dialog_action(self, what):
        """Handles a menu or dialog button.
        Menu: 'one', 'two', 'online', 'close'.
        New-game dialog: 'white', 'black', 'level-', 'level+', 'start', 'cancel'.
        Online dialog: the same names with an 'o_' prefix."""
        if what == "one":
            self.open_dialog(back=True)
            return
        elif what == "online":
            self.open_online()
            return
        elif what.startswith("o_"):
            self._online_action(what[2:])
        elif what == "two":
            self.dialog = None
            self.players = 2
            self._save_mode(2)
            self.new_game()
        elif what == "close":
            if self.menu_cancel:
                self.dialog = None
                o = self.online
                if self.players == ONLINE and o.state is not self._shown:
                    self._play_state(o.state)  # moves arrived while the menu was open
        elif what == "white":
            self.dialog_white = True
        elif what == "black":
            self.dialog_white = False
        elif what == "level-":
            self.dialog_level = max(0, self.dialog_level - 1)
        elif what == "level+":
            self.dialog_level = min(MAX_LEVEL, self.dialog_level + 1)
        elif what == "cancel":
            self.dialog = "menu" if self.dialog_back else None
        elif what == "start":
            self.dialog = None
            self.players = 1
            s = self.settings
            if s.human_white != self.dialog_white or s.level != self.dialog_level:
                s.human_white = self.dialog_white
                s.level = self.dialog_level
                s.save()
            self._save_mode(1)
            self.new_game()
        self._changed()

    def _save_mode(self, players):
        s = self.settings
        if getattr(s, "mode", players) != players:
            s.mode = players
            s.save()

    # ------------------------------------------------------------ online games

    def open_online(self):
        """Opens the online dialog (resume the current online game or start one)."""
        if self.searching() or self.online is None:
            return False
        self.dialog = "online"
        c = self.online.colour()
        if c is not None:
            self.online_white = c == WHITE
        self.promo = None
        self._clear_selection()
        self._changed()
        return True

    def can_resume(self):
        o = self.online
        return o is not None and o.state is not None

    def can_start_online(self):
        o = self.online
        return o is not None and o.configured and o.synced

    def _online_action(self, what):
        if what == "white":
            self.online_white = True
        elif what == "black":
            self.online_white = False
        elif what == "back":
            self.auto_resume = False
            self.dialog = "menu"
        elif what == "resume":
            if self.can_resume():
                self._enter_online(self.online.state)
        elif what == "start":
            if self.can_start_online():
                self._enter_online(self.online.new_game(self.online_white))

    def _enter_online(self, st):
        self.auto_resume = False
        prev, prev_fen = self.players, self.tf.fen()
        self.players = ONLINE
        if not self._play_state(st, fresh=True):
            self.players = prev
            # restore the previous position (its move history is lost)
            self.tf.set_fen(prev_fen)
            self._sync()
            self.net_status("Bad game data", True)
            return False
        self.dialog = None
        self._save_mode(ONLINE)
        return True

    def _load(self, st):
        """Loads state st into the engine. Returns the SAN of its last move (or "").
        Raises ValueError if st isn't a legal game."""
        tf = self.tf
        self._stop_search()
        tf.reset()
        if st.f:
            if len(st.f) > 100:
                raise ValueError("FEN")
            tf.set_fen(st.f)
        san = ""
        for i, m in enumerate(st.m):
            if i == len(st.m) - 1:
                san = tf.san(m)
            tf.push(m)
        return san

    def _play_state(self, st, fresh=False):
        """Shows online state st (a newer position or a different game). Returns
        False and keeps the current game if st isn't legal."""
        o = self.online
        same = st.same_game(self._shown)
        try:
            san = self._load(st)
        except (ValueError, RuntimeError) as e:
            self._say("Online: bad game data (%s): %r" % (e, st))
            if not fresh and self._shown is not None:
                try:
                    self._load(self._shown)
                except (ValueError, RuntimeError):
                    pass
            return False
        if fresh or not same:
            self.tf.new_game()
            self._reset_game_info()
            self._say(
                "Online game %d: you play %s against %s"
                % (
                    st.g,
                    "white" if st.colour_of(o.me_id) == WHITE else "black",
                    o.opp_name(),
                )
            )
        o.state = st
        self._shown = st
        self.hint_from = self.hint_to = -1
        self.hint_san = ""
        mover = st.by != o.me_id
        self.remote_san = san if mover and st.m else (self.remote_san if same else "")
        if mover and san:
            self._say("%s: %s" % (o.opp_name(), san))
        self._sync()
        self._after_move()
        return True

    def remote_state(self, text, from_opp=True):
        """Handles a value read from a feed (the opponent's, or our own at start-up).
        Returns True if it is a newer state of our game; it is shown right away if
        the online game is on screen."""
        from chess_online import State

        o = self.online
        if o is None:
            return False
        st = State.from_json(text)
        was_elsewhere = o.opp_elsewhere
        if not o.offer(st, from_opp):
            if o.opp_elsewhere != was_elsewhere:
                self._changed()
            return False
        if self.players == ONLINE and self.dialog is None:
            if not self._play_state(st):
                return False
        else:
            o.state = st  # validated when played (RESUME)
            self._changed()
        return True

    def net_status(self, text, bad=False, connected=None):
        """Called by chess_net to update the connection status line."""
        o = self.online
        if o is None:
            return
        if connected is not None:
            o.connected = connected
        if text != o.status or bad != o.status_bad:
            o.status, o.status_bad = text, bad
            self._changed()

    def net_synced(self):
        """Called by chess_net once both feeds have been read. If the app started
        in online mode, this resumes the online game."""
        o = self.online
        o.synced = True
        if self.auto_resume and self.dialog == "online":
            self.auto_resume = False
            if o.state is not None:
                self._enter_online(o.state)
        self._changed()

    def net_sent(self):
        """Called by chess_net after sending our move, to clear "Sending..."."""
        self._changed()

    def online_note(self):
        """A one-line summary of the online game, shown with the RESUME button."""
        o = self.online
        st = o.state if o else None
        if st is None:
            return "No game yet"
        mine = st.colour_of(o.me_id)
        turn = (_fen_side(st.f) + len(st.m)) % 2 if st.f else st.n % 2
        who = "your move" if turn == mine else "their move"
        return "Move %d, %s (%s)" % (
            st.n // 2 + 1,
            who,
            "white" if mine == WHITE else "black",
        )

    # ------------------------------------------------------------ text for the panel

    def status(self):
        """The panel's two status lines: (line1, colour name, line2, colour name)."""
        if self.players == 2:
            return self._status2()
        if self.players == ONLINE:
            return self._status_online()
        if self.mode == OVER:
            r = self.result
            if r in (WHITE_MATES, BLACK_MATES):
                won = (r == WHITE_MATES) == (self.human == WHITE)
                return (
                    "Checkmate!",
                    "good" if won else "bad",
                    "You win!" if won else "You lost",
                    "text",
                )
            return ("Draw", "accent", DRAW_REASONS.get(r, ""), "text")
        if self.mode == ENGINE:
            return (
                "Moving..." if self.stop_requested else "Thinking...",
                "accent",
                "Level %d" % self.settings.level,
                "muted",
            )
        if self.mode == HINT:
            return ("Thinking...", "accent", "Hint", "muted")
        if self.engine_san:
            line2 = "%s: %s" % (ENGINE_SHORT, self.engine_san)
        else:
            line2 = "You are %s" % ("white" if self.human == WHITE else "black")
        if self.check_sq >= 0:
            return ("Check!", "bad", line2, "text")
        return ("Your move", "good", line2, "text")

    def _status2(self):
        """status() for two players. Lines are short to fit the shield's 72 px panel."""
        name = "White" if self.side == WHITE else "Black"
        if self.mode == OVER:
            r = self.result
            if r in (WHITE_MATES, BLACK_MATES):
                return (
                    "Checkmate!",
                    "good",
                    "%s wins!" % ("White" if r == WHITE_MATES else "Black"),
                    "text",
                )
            return ("Draw", "accent", DRAW_REASONS.get(r, ""), "text")
        if self.mode == HINT:
            return ("Thinking...", "accent", "Hint", "muted")
        if self.check_sq >= 0:
            return (name, "bad", "in check!", "bad")
        return (name, "good", "to move", "text")

    def _status_online(self):
        """status() for an online game, with short lines like _status2()."""
        o = self.online
        if self.mode == OVER:
            r = self.result
            if r in (WHITE_MATES, BLACK_MATES):
                won = (r == WHITE_MATES) == (self.human == WHITE)
                return (
                    "Checkmate!",
                    "good" if won else "bad",
                    "You win!" if won else "You lost",
                    "text",
                )
            return ("Draw", "accent", DRAW_REASONS.get(r, ""), "text")
        if self.mode == HINT:
            return ("Thinking...", "accent", "Hint", "muted")
        if o.outbox is not None:
            line2, c2 = "Sending...", "accent"
        elif not o.connected:
            line2, c2 = "Offline", "bad"
        elif self.mode == REMOTE:
            line2, c2 = o.opp_short(), "text"
        elif self.remote_san:
            line2, c2 = "%s: %s" % (o.opp_short(), self.remote_san), "text"
        else:
            line2, c2 = "vs " + o.opp_short(), "text"
        if self.mode == REMOTE:
            return ("Waiting", "accent", line2, c2)
        if self.check_sq >= 0:
            return ("Check!", "bad", line2, c2)
        return ("Your move", "good", line2, c2)

    def material_text(self):
        w, b = self.material
        if w == b:
            return "Even"
        return "%s +%d" % ("White" if w > b else "Black", abs(w - b))

    def eval_text(self):
        return format_eval(self.eval_white) if self.has_eval else "-"


def _fen_side(fen):
    """0 if white is to move in fen, 1 if black."""
    parts = fen.split()
    return 1 if len(parts) > 1 and parts[1] == "b" else 0


def _k(n):
    """Short number: 1234 -> '1.2k', 12345 -> '12k', 1234567 -> '1.23M'."""
    if n >= 1000000:
        return "%d.%02dM" % (n // 1000000, n // 10000 % 100)
    if n >= 10000:
        return "%dk" % (n // 1000)
    if n >= 1000:
        return "%d.%dk" % (n // 1000, n // 100 % 10)
    return str(n)
