# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Saved WiFi networks and scan results, for Settings > WiFi (boards with
WiFi, the Metro ESP32-P4). Plain Python, so it runs in the tests and the
simulator; the board keeps the list in NVM (fm1ui.metro_p4), not on the card,
so it stays with the flasher when the card changes.
"""
import json

MAX = 8  # saved networks, most recently used first


class Saved:
    """The saved networks as [ssid, password] pairs, most recent first.
    load() returns the stored text or None; store(text) returns False when
    it couldn't be written."""

    def __init__(self, load, store):
        self._store = store
        self.items = []
        try:
            data = json.loads(load() or "[]")
            self.items = [[str(s), str(p)] for s, p in data][:MAX]
        except (ValueError, TypeError):
            pass

    def save(self):
        return self._store(json.dumps(self.items))

    def ssids(self):
        return [s for s, _ in self.items]

    def password(self, ssid):
        for s, p in self.items:
            if s == ssid:
                return p
        return None

    def add(self, ssid, password):
        """Save or update one, as the most recent; the oldest drops past MAX."""
        self.items = [[ssid, password]] + [i for i in self.items if i[0] != ssid]
        del self.items[MAX:]
        return self.save()

    def used(self, ssid):
        """Joined it: move it to the front (written only when it moves)."""
        if self.items and self.items[0][0] != ssid:
            for i in self.items:
                if i[0] == ssid:
                    self.items.remove(i)
                    self.items.insert(0, i)
                    return self.save()
        return True

    def forget(self, ssid):
        self.items = [i for i in self.items if i[0] != ssid]
        return self.save()


def candidates(saved, toml):
    """Networks to try, in order: the saved ones, then settings.toml's
    (ssid, password) unless it's saved too. Each is (ssid, password)."""
    out = [tuple(item) for item in saved.items]  # (ssid, password)
    if toml and toml[0] and toml[0] not in saved.ssids():
        out.append(toml)
    return out


def strongest(found):
    """Scan results (ssid, rssi, open) with one entry per name, the
    strongest, strongest first; hidden networks (no name) left out."""
    best = {}
    for ssid, rssi, is_open in found:
        if ssid and (ssid not in best or rssi > best[ssid][1]):
            best[ssid] = (ssid, rssi, is_open)
    return sorted(best.values(), key=lambda n: -n[1])


def bars(rssi):
    """Signal strength as 1 to 4 bars."""
    return 4 if rssi >= -55 else 3 if rssi >= -67 else 2 if rssi >= -78 else 1
