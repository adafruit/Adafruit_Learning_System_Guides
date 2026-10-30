# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Several displays (views) on the one screen, for ft8_receiver.py:
display=('color', 'map') shows the first, and the m or l key (serial
console or a USB keyboard) shows the next: either key steps through the
views (m for map, l for list, if that is easier to remember).

Each view draws in its own displayio group on a shared framebuffer
(ft8_display_dvi.open_dvi()); showing a view makes its group the
screen's root group. Every view is given every decode, so the one that
comes back is up to date: the text views keep their rows, the map keeps
its exchanges (but is only drawn while it is shown).

A switch redraws the whole screen: ~80 ms to the map, ~155 ms to the
color view on the Fruit Jam, longer than the USB ring holds. So it is
done in paused_step(), which the receiver calls with the stream stopped:
at once after the m / l key while switching is true (the slot being received
is lost unless its transmissions are over), and late in each slot for
the map's own slow work. In a log replay (no radio) it is at once too.

? shows the help page of the view on the screen (each view has its own,
which lists m / l: ft8_help). While it shows, m and l do nothing.
"""


class Views:
    NAME = 'views'

    def __init__(self, views):
        self.views = views
        self.shown = 0               # index of the view on the screen
        self.wanted = 0              # ... and of the one to show at the next paused_step()
        self.status = None           # the receiver's status, from show()
        self.fb, self.display = views[0].fb, views[0].display
        self.display.root_group = views[0].group
        self.display.refresh(minimum_frames_per_second=0)

    @property
    def view(self):
        return self.views[self.shown]

    def _all(self, method, *args):
        for v in self.views:
            f = getattr(v, method, None)
            if f:
                f(*args)

    def message(self, text):
        self._all('message', text)

    def connecting(self):
        self._all('connecting')

    def ready(self):
        self._all('ready')

    def prepare(self):
        # (not through _all(): the map downloads tiles in prepare(), a deep
        # call chain under run(), and every frame counts on the 2 KB pystack)
        for v in self.views:
            if hasattr(v, 'prepare'):
                v.prepare()

    def add_decode(self, d, my_call=''):
        self._all('add_decode', d, my_call)

    def entry(self, text):
        self._all('entry', text)

    def learn(self, d, my_call=''):
        self._all('learn', d, my_call)

    def show(self, st):
        """The status, on the view shown (the others get it when they are
        shown)."""
        self.status = st
        if self.wanted == self.shown:
            self.view.show(st)
            return
        note = st.note
        st.note = ((note + ' ') if note else '') + '%s next' % self.views[self.wanted].NAME.upper()
        self.view.show(st)
        st.note = note

    @property
    def switching(self):
        """True from the m / l key until paused_step() shows the next view."""
        return self.wanted != self.shown

    @property
    def needs_pause(self):
        return self.wanted != self.shown or getattr(self.view, 'needs_pause', False)

    def paused_step(self):
        if self.wanted == self.shown:
            if getattr(self.view, 'needs_pause', False):
                self.view.paused_step()
            return
        v = self.views[self.wanted]
        if self.status is not None:
            v.show(self.status)
        if getattr(v, 'needs_pause', False):
            v.paused_step()              # (the map: drawn now)
        self.shown = self.wanted
        self.display.root_group = v.group
        self.display.refresh(minimum_frames_per_second=0)

    def command(self, action):
        """m or l: the next view; other keys go to the view shown (all of
        them while it asks a question: the map's z; m and l do nothing
        while its help page shows)."""
        if action in ('m', 'l') and not getattr(self.view, 'asking', False):
            page = getattr(self.view, 'help', None)
            if not (page and page.shown):
                self.wanted = (self.wanted + 1) % len(self.views)
                if self.status is not None:
                    self.show(self.status)
            return True
        f = getattr(self.view, 'command', None)
        return bool(f and f(action))

    def step(self):
        """Idle time: one view's step() (a strip of a help page)."""
        for v in self.views:
            if hasattr(v, 'step') and v.step():
                return True
        return False

    def screen(self):
        return self.view.screen()

    def close(self):
        self._all('close')
