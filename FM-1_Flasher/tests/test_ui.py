# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the UI's data layer (fm1ui.catalog) and touch gestures.
Plain CPython: python3 -m unittest discover tests"""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "FM-1_Flasher_Code", "lib"), os.path.join(ROOT, "tools")]

from fm1ui import catalog as C  # noqa: E402

INDEX = (
    "updated\t2026-10-28 03:02 UTC\n"
    "stock-v15\tM-VAVE V15\tV15\tofficial\t0\tFM-1_015\n"
    "hortator\tHortator\t0.25.0\tdrums\t1\tFM-1_900\n"
    "sloop\tSLOOP\t2.8.3\tgroove,dev\t0\tFM-1_900\n"
    "zp12\tzp12\t2.5\tdrums\t0\tFM-1_975\n"
    "broken line\n"
)


class Catalog(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.index = os.path.join(self.dir.name, "index.txt")
        with open(self.index, "w") as f:
            f.write(INDEX)
        self.state_path = os.path.join(self.dir.name, "state.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_load_index(self):
        updated, entries = C.load_index(self.index)
        self.assertEqual(updated, "2026-10-28 03:02 UTC")
        self.assertEqual([e.slug for e in entries], ["stock-v15", "hortator", "sloop", "zp12"])
        self.assertTrue(entries[1].beta)
        self.assertEqual(entries[2].kind, "groove")

    def test_dates_and_labels(self):
        self.assertEqual(C.nice_date("2026-10-28 03:02 UTC"), "28 Oct 2026")
        self.assertEqual(C.nice_date("soon"), "soon")
        self.assertEqual(C.version_label("2.8"), "v2.8")
        self.assertEqual(C.version_label("V15"), "V15")
        _, entries = C.load_index(self.index)
        self.assertEqual(C.display_name(entries[0]), "M-VAVE V15")
        self.assertEqual(C.display_name(entries[2]), "SLOOP 2.8.3")

    def test_plain(self):
        self.assertEqual(C.plain("its **visualiser** paints"), "its visualiser paints")

    def test_paging(self):
        items = list(range(17))
        self.assertEqual(C.page_count(17, 8), 3)
        self.assertEqual(C.page_count(0, 8), 1)
        self.assertEqual(C.page_slice(items, 2, 8), [16])

    def test_favorites_persist(self):
        s = C.State(self.state_path)
        self.assertTrue(s.toggle_favorite("zp12"))
        self.assertTrue(s.toggle_favorite("sloop"))
        self.assertFalse(s.toggle_favorite("zp12"))
        self.assertEqual(C.State(self.state_path).favorites, {"sloop"})

    def test_sorts(self):
        with open(self.index, "w") as f:
            f.write("updated\tnow\n"
                    "stock-v15\tM-VAVE V15\tV15\tofficial\t0\tFM-1_015\t\t\n"
                    "amb\tAmb\t1\tambient\t0\tFM-1_901\t2026-10-08\t2026-11-01\n"
                    "bub\tBub\t1\tdrums\t0\tFM-1_902\t2026-10-30\t2026-10-30\n"
                    "cor\tCor\t1\tdrums\t0\tFM-1_903\t2026-10-08\t2026-10-05\n"
                    "old\tOld card line\t1\tdrums\t0\tFM-1_904\n")
        index = C.Index(self.index)
        self.assertEqual(len(index), 5)  # lines without dates still count
        names = lambda items: [index.entry(i).slug for i in items]  # noqa: E731
        self.assertEqual(names(index.select()), ["stock-v15", "amb", "bub", "cor", "old"])
        # newest on the hub first, ties by name, undated last
        self.assertEqual(names(index.select(sort="new")), ["bub", "amb", "cor", "stock-v15", "old"])
        self.assertEqual(names(index.select(sort="updated")), ["amb", "bub", "cor", "stock-v15", "old"])
        self.assertEqual(names(index.select(tag="drums", sort="updated")), ["bub", "cor", "old"])
        self.assertEqual(index.entry(1).added, "2026-10-08")
        self.assertEqual(index.entry(4).date, "")
        self.assertEqual(index.with_product("FM-1_904"), ["old"])
        self.assertEqual([C.next_sort(s) for s in C.SORTS + ("bogus",)], ["new", "updated", "az", "az"])

    def test_sort_persists(self):
        s = C.State(self.state_path)
        self.assertEqual(s.sort, "az")
        s.sort = "new"
        s.save()
        self.assertEqual(C.State(self.state_path).sort, "new")

    def test_removed_persists(self):
        s = C.State(self.state_path)
        self.assertEqual(s.removed, set())
        s.removed.add("zp12")
        s.save()
        self.assertEqual(C.State(self.state_path).removed, {"zp12"})

    def test_view_persists(self):
        s = C.State(self.state_path)
        self.assertEqual(s.view, "grid")
        s.view = "list"
        s.save()
        self.assertEqual(C.State(self.state_path).view, "list")

    def test_unwritable_state_is_not_fatal(self):
        s = C.State(os.path.join(self.dir.name, "missing", "state.json"))
        self.assertTrue(s.toggle_favorite("zp12"))
        self.assertFalse(s.save())

    def test_index_lookups(self):
        index = C.Index(self.index)
        self.assertEqual(len(index), 4)
        self.assertEqual(index.find("sloop").version, "2.8.3")
        self.assertIsNone(index.find("slo"))
        self.assertEqual(index.select({"zp12", "sloop", "gone"}), [2, 3])
        self.assertEqual(index.with_product("FM-1_900"), ["hortator", "sloop"])

    def test_tags(self):
        index = C.Index(self.index)
        self.assertEqual(index.tags(), ["drums", "dev", "groove", "official"])
        self.assertEqual(index.select(tag="drums"), [1, 3])
        self.assertEqual(index.select(tag="dev"), [2])  # second genre counts too
        self.assertEqual(index.select({"zp12", "sloop"}, tag="drums"), [3])
        self.assertEqual(index.select(tag="ambient"), [])

    def test_installed_badge(self):
        entries = C.Index(self.index)
        s = C.State(self.state_path)
        self.assertIsNone(s.installed_slug(None, entries))
        # unique identity
        self.assertEqual(s.installed_slug("FM-1_975", entries), "zp12")
        self.assertEqual(s.installed_slug("FM-1_015", entries), "stock-v15")
        # shared identity: unknown until we installed it ourselves
        self.assertIsNone(s.installed_slug("FM-1_900", entries))
        s.record_install("hortator", "FM-1_900")
        self.assertEqual(C.State(self.state_path).installed_slug("FM-1_900", entries), "hortator")
        # a different firmware is on it now
        self.assertEqual(s.installed_slug("FM-1_975", entries), "zp12")
        with open(self.state_path) as f:
            self.assertNotIn("pending", json.load(f))

    def test_wrap_and_ellipsize(self):
        width = len
        self.assertEqual(C.wrap("one two three four", width, 9), ["one two", "three", "four"])
        self.assertEqual(C.ellipsize("Bubba Machine", width, 8), "Bubba...")
        self.assertEqual(C.ellipsize("short", width, 8), "short")


class Gestures(unittest.TestCase):
    def setUp(self):
        try:
            from fm1ui.app import Gestures
        except ImportError as e:  # needs displayio (Blinka) on CPython
            self.skipTest("no displayio: %s" % e)
        self.g = Gestures()
        self.g.sample(None)  # no touch at the start: ready

    def feed(self, *points):
        for p in points:
            self.g.sample(p)
        self.g.sample(None)
        events = []
        while True:
            ev = self.g.event()
            if ev is None:
                return events
            events.append(ev)

    def test_tap(self):
        self.assertEqual(self.feed((100, 50), (104, 52)), [("down", 100, 50), ("tap", 100, 50)])

    def test_swipe(self):
        # A sideways move is a drag as it goes (only the latest position is
        # queued), and a swipe when it lets go.
        self.assertEqual(self.feed((300, 150), (250, 152), (200, 160)),
                         [("down", 300, 150), ("drag", -100, 300, 150), ("swipe", -100)])

    def test_no_drag_for_a_roll_or_an_up_down_move(self):
        self.assertEqual(self.feed((100, 50), (108, 52)), [("down", 100, 50), ("tap", 100, 50)])
        self.assertEqual(self.feed((100, 50), (130, 95)), [("down", 100, 50), ("up",)])

    def test_vertical_drag(self):
        # Mostly up or down: a vertical drag, which stays one even if the
        # finger then goes sideways.
        self.assertEqual(self.feed((100, 150), (104, 120), (180, 100)),
                         [("down", 100, 150), ("vdrag", -50, 100, 150), ("up",)])

    def test_drag_events_as_it_moves(self):
        g = self.g
        g.sample((100, 50))
        g.sample((120, 52))
        self.assertEqual([g.event(), g.event()], [("down", 100, 50), ("drag", 20, 100, 50)])
        g.sample((90, 51))  # back past the start: still a drag
        self.assertEqual(g.event(), ("drag", -10, 100, 50))

    def test_touch_down_at_start_is_ignored_until_it_lifts(self):
        # After an install's reload, the finger that tapped OK mustn't tap
        # the list that comes up under it.
        from fm1ui.app import Gestures
        self.g = Gestures()
        self.assertEqual(self.feed((150, 220), (151, 221)), [])
        self.assertEqual(self.feed((100, 50)), [("down", 100, 50), ("tap", 100, 50)])

    def test_drag_only_lets_go(self):
        self.assertEqual(self.feed((100, 50), (140, 90)), [("down", 100, 50), ("up",)])


if __name__ == "__main__":
    unittest.main()
