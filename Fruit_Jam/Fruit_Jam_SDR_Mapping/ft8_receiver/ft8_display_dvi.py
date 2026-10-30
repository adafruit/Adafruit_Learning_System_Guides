# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""DVI (picodvi) display for ft8_receiver.py: one 320x240 text screen.
On boards without picodvi (the Metro ESP32-P4) the screen is the 2.8"
TFT shield (ft8_tft, the same size) and everything else is the same.

Two status rows at the top (frequency, UTC and clock; level, last slot,
log), then the decodes, one per row:

    143015 -12  0.2 1234 CQ          K1ABC       FN42
    (time, SNR dB, DT s, audio Hz, message; '>' marks MY_CALL)

The message's words are padded to COLUMN_WIDTH so the callsigns line up
down the screen (a longer word pushes the rest over).

Nothing ever redraws the whole screen while the USB stream runs (a full
redraw takes longer than the USB ring holds): only changed rows are
rewritten, so the decode area does not scroll. New lines are written over
the oldest one, with a blank row below the newest as a marker.

The receiver uses a display through these methods: message(text),
connecting(), ready(), show(status), add_decode(decode, my_call),
entry(text), screen(), and command(action) and step() for the help
page. entry() shows a console command being typed ('f14.074', 'c3') on
the first status row (entry_row()) until it is given None.
ft8_display_color.py builds on this one and only changes the terminal,
how rows are written and the help page's sample row.

? shows a page of help over the screen below the status row (what the
rows show, the keys and buttons; ? or Esc hides it again:
ft8_help.HelpPage). step() shows or hides it a strip at a time.

open_dvi() makes the framebuffer (None on the TFT) and its display; a display given
screen=(framebuffer, display) draws on that one instead, so several
views can share the screen (ft8_display_views.py), each in its own group
(self.group). views: the display is one of those (its help page lists the
m / l key).
"""
import board
import displayio
import framebufferio
import terminalio
import ft8_help

# pylint: disable=import-outside-toplevel

STATUS_ROWS = 2
COLUMN_WIDTH = 11    # a message column, the longest call heard: '<K6VHF/HR9>'


def format_frequency(hz):
    """14074000 -> '14.074.00 MHz' (10 Hz resolution)."""
    hz = int(hz)
    return '%d.%03d.%02d MHz' % (hz // 1000000, hz // 1000 % 1000, hz // 10 % 100)


def entry_row(text):
    """The status row while a console command is typed: text is 'f' and
    a frequency or 'c' and a preset number, as typed so far."""
    if text[:1] == 'f':
        return 'TUNE TO %s_  MHz or kHz, Enter; Esc cancels' % text[1:].strip()
    return 'GO TO PRESET %s_  Enter (none: list them)' % text[1:].strip()


def message_columns(text):
    """The columns of a message: its words, with a CQ's modifier kept with
    it ('CQ DX K1ABC FN42' -> 'CQ DX', 'K1ABC', 'FN42'). Free text (more
    than three words) is one column."""
    words = text.split()
    if len(words) == 4 and words[0] == 'CQ':
        words[:2] = [words[0] + ' ' + words[1]]
    return words if len(words) <= 3 else [text]


def join_columns(columns, shown=None):
    """The columns of a message, each but the last padded to COLUMN_WIDTH.
    shown: the columns as drawn (with color codes), if not columns."""
    shown = shown or columns
    padded = [shown[k] + ' ' * (COLUMN_WIDTH - len(columns[k])) for k in range(len(columns) - 1)]
    return ' '.join(padded + shown[-1:])


def open_dvi():
    """The 320x240 8-bit (RGB332) DVI framebuffer (picodvi) and its display, which
    only refreshes when told to: (framebuffer, display). Without picodvi:
    (None, the TFT shield's display); the RGB332 palettes work there too."""
    try:
        import picodvi           # (the Fruit Jam's DVI output)
    except ImportError:
        import ft8_tft
        return None, ft8_tft.open_display(320, 240)
    displayio.release_displays()
    fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
        red_dp=board.D0P, red_dn=board.D0N, green_dp=board.D1P, green_dn=board.D1N,
        blue_dp=board.D2P, blue_dn=board.D2N, color_depth=8)
    return fb, framebufferio.FramebufferDisplay(fb, auto_refresh=False)


def is_mine(text, my_call):
    """True if the message text has my_call as one of its words."""
    return bool(my_call) and my_call in text.split()


class DviDisplay:
    NAME = 'dvi'
    KEYS = ()                # the display's own keys: they do nothing while the help shows

    def __init__(self, screen=None, views=False):
        self.fb, self.display = screen or open_dvi()
        self.group = group = displayio.Group()
        fw, fh = terminalio.FONT.get_bounding_box()[:2]
        self.columns = 320 // fw
        self.rows = 240 // fh
        g = displayio.Group(y=(240 - self.rows * fh) // 2)
        g.append(self.make_terminal(fw, fh))
        group.append(g)
        self._shown = {}
        self.status_row = ''     # the first status row, from show()
        self.typing = None       # a command being typed, shown over it (entry())
        self.text_rows = self.rows - STATUS_ROWS - 1
        self.line = -1           # decode row last written (0 .. text_rows - 1)
        self.help = ft8_help.HelpPage(self.display, group, self.help_rows(views))
        self.display.root_group = group
        self.display.refresh(minimum_frames_per_second=0)
        self.row(STATUS_ROWS, '-' * (self.columns - 1))

    def make_terminal(self, fw, fh):
        """Set self.term (has write()) and return its TileGrid."""
        pal = displayio.Palette(2)
        pal[0] = 0x07111d
        pal[1] = 0xeaf1fa
        grid = displayio.TileGrid(terminalio.FONT.bitmap, pixel_shader=pal, width=self.columns,
                                  height=self.rows, tile_width=fw, tile_height=fh)
        self.term = terminalio.Terminal(grid, terminalio.FONT)
        return grid

    def help_rows(self, views):
        """The help page (ft8_help.HelpPage)."""
        return ft8_help.text_rows(False, views)

    def command(self, action):
        """A console action; True if the display used it (? and Esc: the help)."""
        return self.help.command(action, self.KEYS)

    def step(self):
        """Idle time: a strip of the help page shown or hidden; True if
        there was one."""
        return self.help.step()

    def row(self, row, text):
        """Rewrite one screen row if it changed (about 7 ms)."""
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

    def _text_row(self, k, text):
        self.row(STATUS_ROWS + 1 + k % self.text_rows, text)

    def add_line(self, text):
        """A decode, over the oldest one, with the blank marker row below."""
        self.line = (self.line + 1) % self.text_rows
        self._text_row(self.line, text)
        self._text_row(self.line + 1, '')

    def format_decode(self, d, my_call=''):
        """A decode (a dict from ft8_receiver.results) as one row."""
        return '%s%s %3d %4.1f %4d %s' % ('>' if is_mine(d['text'], my_call) else ' ', d['t'][7:],
                                          d['snr'], d['dt'], d['freq'],
                                          join_columns(message_columns(d['text'])))

    def add_decode(self, d, my_call=''):
        """A decode, as a new row; my_call: the call to mark with '>'."""
        self.add_line(self.format_decode(d, my_call))

    def screen(self):
        """The text on the screen, row by row (for tests without a capture card)."""
        return [self._shown.get(r, '') for r in range(self.rows)]

    def message(self, text):
        self.row(0, text)

    def connecting(self):
        self.row(0, 'CONNECTING: looking for the USB receiver')

    def ready(self):
        self.row(1, 'Listening: decodes appear after each 15 s slot')

    def entry(self, text):
        """A console command being typed (None: done; the status back)."""
        self.typing = text
        self.row(0, self.status_row if text is None else entry_row(text))

    def show(self, st):
        """The receiver's status (an ft8_receiver.Status)."""
        self.status_row = '%s USB %-4s %s %s' % (format_frequency(st.dial), st.label[:4], st.utc,
                                                 st.clock)
        self.row(0, self.status_row if self.typing is None else entry_row(self.typing))
        if st.decoding is not None:
            last = 'decoding'
        elif st.slot_decodes is None:
            last = 'waiting for a slot'
        else:
            last = 'last slot %d' % st.slot_decodes
        log = ('log %d' % st.logged) if st.sd else 'NO SD CARD'
        self.row(1, '%4.0f dB  %s  %s%s%s' % (st.level, last, log, ' MUTED' if st.muted else '',
                                             '  ' + st.note if st.note else ''))
