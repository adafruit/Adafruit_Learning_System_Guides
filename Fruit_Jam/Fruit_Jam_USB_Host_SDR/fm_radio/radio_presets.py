# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Station presets: the ones built into the code, changed by a JSON file.

The file lives in /saves, which CircuitPython code can write even while
CIRCUITPY is mounted on a computer. It looks like this (frequencies in Hz):

    {"presets": {"FM": [99500000], "AM": [1190000], "WX": []},
     "remove": [93100000, 162525000]}

"presets" holds the stations saved on each band, "remove" the built-in
presets taken out. Hand-written entries may also be typed frequencies such as
"99.5" or "1190"; they are stored in Hz the next time the radio saves.
"""

import json
import os

SAVE_PATH = "/saves/am_fm_radio.json"


def _list(value):
    return value if isinstance(value, list) else ()


class Presets:
    """defaults maps each band to its built-in presets (Hz). band_of(value)
    returns (band, Hz) for a saved value, or raises ValueError."""

    def __init__(self, defaults, band_of, path=SAVE_PATH):
        self.defaults = defaults
        self.path = path
        self.saved = {band: [] for band in defaults}
        self.removed = []
        if path:
            self._load(band_of)

    def _load(self, band_of):
        try:
            with open(self.path) as f:
                data = json.load(f)
        except OSError:
            return  # no file yet
        except ValueError as error:
            print("PRESETS_BAD_FILE", self.path, error)
            return
        if not isinstance(data, dict):
            print("PRESETS_BAD_FILE", self.path)
            return
        saved = data.get("presets")
        if not isinstance(saved, dict):
            saved = {}
        for key in self.defaults:
            for value in _list(saved.get(key)):
                station = self._check(band_of, value, key)
                if station:
                    self.add(*station)
        for value in _list(data.get("remove")):
            station = self._check(band_of, value)
            if station:
                self.remove(*station)

    def _check(self, band_of, value, band=None):
        # (band, Hz) for a value read from the file, or None (and a warning)
        # if it is not a frequency on one of the bands (or on band, if given).
        try:
            if isinstance(value, bool):
                raise ValueError
            station = band_of(str(value))
            if station[0] == band or (band is None and station[0] in self.defaults):
                return station
        except ValueError:
            pass
        print("PRESETS_BAD_ENTRY", band or "remove", value)
        return None

    def stations(self, band):
        """The presets on band, built-in ones first, then the saved ones."""
        removed = self.removed
        stations = [hz for hz in self.defaults[band] if hz not in removed]
        return stations + self.saved[band]

    def add(self, band, hz):
        """Make hz a preset on band. Returns False if it already was."""
        if hz in self.defaults[band]:
            if hz not in self.removed:
                return False
            self.removed.remove(hz)
        elif hz in self.saved[band]:
            return False
        else:
            self.saved[band].append(hz)
        return True

    def remove(self, band, hz):
        """Take hz out of the presets on band. Returns False if it was not one."""
        if hz in self.saved[band]:
            self.saved[band].remove(hz)
        elif hz in self.defaults[band] and hz not in self.removed:
            self.removed.append(hz)
        else:
            return False
        return True

    def save(self):
        """Write the file. Raises OSError if /saves can't be written."""
        # Write a new file and rename it over the old one, so a reset part
        # way through leaves the old file intact. Then flush the flash cache
        # now, while the caller has the radio stopped, rather than at the
        # next background flush.
        temp = self.path + ".tmp"
        with open(temp, "w") as f:
            json.dump({"presets": self.saved, "remove": self.removed}, f)
        os.rename(temp, self.path)
        os.sync()
