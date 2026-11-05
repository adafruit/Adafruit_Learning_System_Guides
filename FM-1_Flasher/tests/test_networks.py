# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for Settings > WiFi's saved networks (fm1ui.networks)."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "FM-1_Flasher_Code", "lib")]

from fm1ui import networks as N  # noqa: E402


class Store:
    def __init__(self, text=None, ok=True):
        self.text, self.ok, self.writes = text, ok, 0

    def load(self):
        return self.text

    def store(self, s):
        self.writes += 1
        self.text = s
        return self.ok


def saved(text=None):
    st = Store(text)
    return N.Saved(st.load, st.store), st


class TestSaved(unittest.TestCase):
    def test_empty_and_bad_data(self):
        for text in (None, "", "not json", '{"a": 1}', "[1, 2]"):
            s, _ = saved(text)
            self.assertEqual(s.items, [], text)

    def test_add_is_most_recent_and_round_trips(self):
        s, st = saved()
        s.add("Home", "pw-home-1")
        s.add("Studio", "pw-studio")
        s.add("Home", "pw-home-2")  # updates and moves to the front
        self.assertEqual(s.items, [["Home", "pw-home-2"], ["Studio", "pw-studio"]])
        again, _ = saved(st.text)
        self.assertEqual(again.items, s.items)
        self.assertEqual(again.password("Studio"), "pw-studio")
        self.assertIsNone(again.password("Nope"))

    def test_oldest_drops_past_max(self):
        s, _ = saved()
        for i in range(N.MAX + 2):
            s.add("net%d" % i, "password")
        self.assertEqual(len(s.items), N.MAX)
        self.assertEqual(s.ssids()[0], "net%d" % (N.MAX + 1))
        self.assertNotIn("net0", s.ssids())

    def test_used_writes_only_when_it_moves(self):
        s, st = saved('[["A", "aaaaaaaa"], ["B", "bbbbbbbb"]]')
        s.used("A")
        self.assertEqual(st.writes, 0)
        s.used("B")
        self.assertEqual(s.ssids(), ["B", "A"])
        self.assertEqual(st.writes, 1)
        s.used("settings.toml's")  # not saved: nothing to move
        self.assertEqual(st.writes, 1)

    def test_forget(self):
        s, _ = saved('[["A", "aaaaaaaa"], ["B", "bbbbbbbb"]]')
        s.forget("A")
        self.assertEqual(s.ssids(), ["B"])

    def test_candidates(self):
        s, _ = saved('[["A", "aaaaaaaa"], ["B", "bbbbbbbb"]]')
        self.assertEqual(N.candidates(s, ("T", "tttttttt")), [("A", "aaaaaaaa"), ("B", "bbbbbbbb"), ("T", "tttttttt")])
        self.assertEqual(N.candidates(s, ("B", "old")), [("A", "aaaaaaaa"), ("B", "bbbbbbbb")])  # saved wins
        self.assertEqual(N.candidates(s, None), [("A", "aaaaaaaa"), ("B", "bbbbbbbb")])

    def test_strongest_and_bars(self):
        found = [("A", -80, False), ("", -40, True), ("A", -50, False), ("B", -60, True)]
        self.assertEqual(N.strongest(found), [("A", -50, False), ("B", -60, True)])
        self.assertEqual([N.bars(r) for r in (-40, -60, -70, -90)], [4, 3, 2, 1])


if __name__ == "__main__":
    unittest.main()
