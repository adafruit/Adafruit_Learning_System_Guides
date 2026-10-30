# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Text display for aprs_receiver.py: one 320x240 text screen (DVI via
picodvi on the Fruit Jam, the TFT shield on the Metro ESP32-P4).

Two status rows at the top (frequency, preset, UTC and clock; level,
carrier, packets, stations, log), then the packets, one per row:

    20:31 AE0WC-9   38.783N 94.825W 111km/h car
    (UTC hours:minutes, source call, a summary from aprs_parse.summary)

Nothing ever redraws the whole screen while the USB stream runs (a full
redraw takes longer than the USB ring holds): only changed rows are
rewritten, so the packet area does not scroll. New lines are written over
the oldest one, with a blank row below the newest as a marker.

? shows a page of help over the screen (the keys and buttons; ? or Esc
hides it again: aprs_ui.HelpPage).
"""
import displayio
import aprs_ui
from aprs_ui import format_frequency, packet_row

STATUS_ROWS = 2


class TextDisplay(aprs_ui.Display):
    NAME = 'text'

    def __init__(self, home=None):
        self.home = home
        self.fb, self.display = aprs_ui.open_framebuffer()
        group = displayio.Group()
        self.rows = aprs_ui.HEIGHT // 12
        # (top: status_row())
        self.lines = self.top = aprs_ui.TextRows(self.display, group, self.rows)
        self.columns = self.lines.columns
        self.text_rows = self.rows - STATUS_ROWS - 1
        self.line = -1           # packet row last written (0 .. text_rows - 1)
        self.help = aprs_ui.HelpPage(self.display, group,
                                     [aprs_ui.HELP_TITLE, []] + aprs_ui.help_keys('l')
                                     + [[], aprs_ui.HELP_BUTTONS])
        self.display.root_group = group
        self.display.refresh(minimum_frames_per_second=0)
        self.row(STATUS_ROWS, '-' * (self.columns - 1))

    def row(self, row, text):
        self.lines.row(row, text)

    def _text_row(self, k, text):
        self.row(STATUS_ROWS + 1 + k % self.text_rows, text)

    def add_line(self, text):
        """A line over the oldest one, with the blank marker row below."""
        self.line = (self.line + 1) % self.text_rows
        self._text_row(self.line, text)
        self._text_row(self.line + 1, '')

    def add_packet(self, p, hhmm):
        """A decoded packet (aprs_parse dict) heard at hhmm (UTC)."""
        self.add_line('%s %-9s %s' % packet_row(p, hhmm, self.home, self.columns - 17))

    def screen(self):
        """The text on the screen, row by row (for tests without a capture card)."""
        return self.lines.text()

    def message(self, text):
        self.row(0, text)

    def connecting(self):
        self.row(0, 'CONNECTING: looking for the USB receiver')

    def ready(self):
        self.row(1, 'Listening for APRS packets')

    def show(self, st):
        """The receiver's status (an aprs_ui.Status)."""
        # (a replay knows neither the frequency nor the level)
        freq = format_frequency(st.dial) + ' ' if st.dial is not None else ''
        self.status_row('%s%-9s %s %s' % (freq, st.label[:9], st.utc, st.clock))
        log = ('log %d' % st.logged) if st.sd else 'NO SD CARD'
        level = ('%4.0f dB %s ' % (st.level, 'DCD' if st.dcd else '   ')
                 if st.level is not None else '')
        self.row(1, '%spkts %d stns %d %s%s%s' % (
            level, st.packets, st.stations, log,
            ' MUTED' if st.muted else '', '  ' + st.note if st.note else ''))
