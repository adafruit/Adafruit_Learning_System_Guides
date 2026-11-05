# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""CPython tests for FM-1_Flasher_Code/lib/fm1proto.py and fm1update.py.

Run from the repo root:  python3 -m unittest discover -s tests
Package tests need the M-VAVE SDK clone in ref/fm1_open (see README).
golden.json is produced by running the reference WebUpdate.js
(tests/make_golden.mjs).
"""

import hashlib
import io
import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "FM-1_Flasher_Code", "lib"), os.path.join(ROOT, "tools")]

import fm1proto as P  # noqa: E402
import fm1update as U  # noqa: E402
from fake_fm1 import FakeClock, FakeFM1, finder_for  # noqa: E402
import make_sd  # noqa: E402

STOCK = os.path.join(ROOT, "ref", "fm1_open", "sdk", "firmware", "FM-1_015.fwsc")
with open(os.path.join(ROOT, "tests", "golden.json")) as _f:
    GOLDEN = json.load(_f)
needs_stock = unittest.skipUnless(os.path.exists(STOCK), "ref/fm1_open not cloned")


def crc16_nibble(data):
    """WebUpdate.js crc16, verbatim."""
    t = [0, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
         0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef]
    c = 0
    for b in data:
        c ^= b << 8
        c = ((c << 4) ^ t[c >> 12]) & 0xFFFF
        c = ((c << 4) ^ t[c >> 12]) & 0xFFFF
    return c


def stock_bytes():
    with open(STOCK, "rb") as f:
        return f.read()


def renamed(data, product):
    """A copy of a package with a different identity. The identity lives in
    the row marker bytes, outside the image, so every CRC still holds."""
    b = bytearray(data)
    for i in range(20):
        b[i * 48 + 47] = (ord(product[i]) + i + 1) & 0xFF if i < len(product) else 125
    return bytes(b)


class Helpers(unittest.TestCase):
    def test_crc16_matches_reference(self):
        rng = random.Random(1)
        for n in (0, 1, 2, 3, 100, 4096):
            d = bytes(rng.getrandbits(8) for _ in range(n))
            self.assertEqual(P.crc16(d), crc16_nibble(d))
        for hexdata, want in GOLDEN["crc16"]:
            self.assertEqual(P.crc16(bytes.fromhex(hexdata)), want)

    def test_crc16_table_path_and_chaining(self):
        saved = P._crc_hqx
        try:
            P._crc_hqx = None  # what CircuitPython uses
            d = bytes(range(256)) * 3
            self.assertEqual(P.crc16(d), crc16_nibble(d))
            self.assertEqual(P.crc16(d[300:], P.crc16(d[:300])), crc16_nibble(d))
        finally:
            P._crc_hqx = saved

    def test_decode_header_is_an_involution(self):
        d = bytes(range(80))
        self.assertEqual(bytes(P.decode_header(P.decode_header(d))), d)

    def test_open_identity(self):
        for s in ("FM1_OFFICIAL_OPEN", "FM1_COMMUNITY_1", "FM1_COMMUNITY_42", "FM-1_8123456"):
            self.assertTrue(P.open_identity(s), s)
        for s in ("FM-1_015", "FM1_COMMUNITY_", "FM1_COMMUNITY_x", "FM-1_812345", "FM-1_81234567",
                  "ota-FM-1_015", "FM1_OFFICIAL_OPENX", ""):
            self.assertFalse(P.open_identity(s), s)

    def test_file_offset(self):
        self.assertEqual(P.file_offset(0), 0)
        self.assertEqual(P.file_offset(46), 46)
        self.assertEqual(P.file_offset(47), 48)
        self.assertEqual(P.file_offset(939), 19 * 48 + 46)
        self.assertEqual(P.file_offset(940), 960)


class Framing(unittest.TestCase):
    def test_frames_match_reference(self):
        for v in GOLDEN["frame"]:
            sysex = bytes(P.frame(v["cmd"], bytes.fromhex(v["payload"])))
            self.assertEqual(sysex.hex(), v["sysex"])
            self.assertEqual(P.parse(sysex), (v["parsed"]["cmd"], bytes.fromhex(v["parsed"]["data"])))

    def test_parse_rejects(self):
        for h in GOLDEN["parse_reject"]:
            self.assertIsNone(P.parse(bytes.fromhex(h)))
        good = bytes(P.frame(17, b"x" * 27))
        self.assertIsNone(P.parse(good[:-1]))
        self.assertIsNone(P.parse(b"\xf0" + good[1:-1] + b"\x00"))
        self.assertIsNone(P.parse(P.KICK))
        self.assertIsNone(P.parse(b""))

    def test_payload_limit(self):
        P.frame(48, bytes(520))
        with self.assertRaises(P.FM1Error):
            P.frame(48, bytes(521))

    def test_identity_and_capability(self):
        self.assertEqual(P.identity(b"FM-1_015".ljust(27, b"\0")), "FM-1_015")
        with self.assertRaises(P.FM1Error):
            P.identity(b"FM-1_015")
        with self.assertRaises(P.FM1Error):
            P.identity(b"\x01bad".ljust(27, b"\0"))
        d = bytearray(47)
        d[0:8] = b"FMC1\x01\x07\x00\x01"
        d[8:10] = (512).to_bytes(2, "little")
        d[10:14] = (1048576).to_bytes(4, "little")
        d[14:46] = bytes(range(32))
        cap = P.capability(bytes(d))
        self.assertEqual((cap["family"], cap["state"], cap["build"]), (7, 0, bytes(range(32)).hex()))
        d[7] = 2
        with self.assertRaises(P.FM1Error):
            P.capability(bytes(d))

    def test_arm_payload(self):
        p = P.arm_payload(7, 0x0A0B0C, "ab" * 32)
        self.assertEqual(p[:6], bytes((1, 7, 0x0C, 0x0B, 0x0A, 0)))
        self.assertEqual(p[6:], b"\xab" * 32)


@needs_stock
class Packages(unittest.TestCase):
    def test_stock_matches_reference(self):
        data = stock_bytes()
        pkg = P.Package(io.BytesIO(data))
        g = GOLDEN["stock"]
        self.assertEqual(pkg.product, g["product"])
        self.assertEqual(pkg.image_len, g["image_len"])
        self.assertEqual(hashlib.sha256(pkg.read(0, pkg.image_len)).hexdigest(), g["image_sha256"])
        pkg.inspect()
        self.assertEqual(pkg.loader_sha256(), g["loader_sha256"])
        self.assertEqual(hashlib.sha256(pkg.factory_bank()).hexdigest(), g["factory_sha256"])

    def test_reads_across_row_boundaries(self):
        data = stock_bytes()
        pkg = P.Package(io.BytesIO(data))
        image = pkg.read(0, pkg.image_len)
        for a, n in ((0, 512), (40, 10), (900, 100), (939, 2), (940, 512), (pkg.image_len - 5, 5)):
            self.assertEqual(pkg.read(a, n), image[a:a + n])
            self.assertEqual(image[a], data[P.file_offset(a)])

    def test_prepare_stock(self):
        meta = stock_meta()
        pkg, m = P.prepare(meta, io.BytesIO(stock_bytes()))
        self.assertEqual(m["loader_identity"], "ota-FM-1_015")

    def test_tampering_is_caught(self):
        data = stock_bytes()
        pkg = P.Package(io.BytesIO(data))
        pkg.inspect()
        for addr in (5, 100, pkg.flash["offset"] + 1000, pkg.loader["offset"] + 7):
            bad = bytearray(data)
            bad[P.file_offset(addr)] ^= 0x40
            with self.assertRaises(P.FM1Error):
                P.Package(io.BytesIO(bytes(bad))).inspect()

    def test_prepare_checked_trusts_the_sha256(self):
        pkg, m = P.prepare(stock_meta(), io.BytesIO(stock_bytes()), checked=True)
        self.assertEqual(m["loader_identity"], "ota-FM-1_015")
        data = bytearray(stock_bytes())
        data[P.file_offset(pkg.flash["offset"] + 1000)] ^= 0x40
        with self.assertRaises(P.FM1Error):  # the SHA-256 still runs
            P.prepare(stock_meta(), io.BytesIO(bytes(data)), checked=True)

    def test_prepare_rejects_bad_meta(self):
        data = stock_bytes()
        for change in ({"family": 6}, {"bytes": 1}, {"sha256": "0" * 64}, {"loader_sha256": "1" * 64},
                       {"schema": 2}, {"product": "FM1_OFFICIAL_OPEN", "kind": "open"}):
            meta = stock_meta()
            meta.update(change)
            with self.assertRaises(P.FM1Error, msg=str(change)):
                P.prepare(meta, io.BytesIO(data))

    def test_identity_rename_keeps_crcs(self):
        pkg = P.Package(io.BytesIO(renamed(stock_bytes(), "FM1_OFFICIAL_OPEN")))
        self.assertEqual(pkg.product, "FM1_OFFICIAL_OPEN")
        pkg.inspect()


def with_new_loader(data, product, loader_name=None):
    """A renamed package whose loader differs from the vendor's, with entry,
    table, and header CRCs re-sealed: a stand-in for a Felucca-family package.
    loader_name is written into the loader, across a 1 KB boundary, as
    Skiff 2.2's loader spells "ota-FM-1_722"."""
    pkg = P.Package(io.BytesIO(data))
    pkg.inspect()
    image = bytearray(pkg.read(0, pkg.image_len))
    ld = pkg.loader
    image[ld["offset"] + 100] ^= 0x55
    if loader_name:
        name = loader_name.encode() + b"\0"
        image[ld["offset"] + 1018:ld["offset"] + 1018 + len(name)] = name
    count = len(pkg.entries)
    table = bytearray(image[64:64 + count * 80])
    for i in range(count):
        e = P.decode_header(table[i * 80:i * 80 + 80])
        if P.le(e, 0, 2) == 100:
            e[4:6] = P.crc16(image[ld["offset"]:ld["offset"] + ld["size"]]).to_bytes(2, "little")
            table[i * 80:i * 80 + 80] = P.decode_header(e)
    image[64:64 + count * 80] = table
    head = P.decode_header(image[0:64])
    head[2:4] = P.crc16(table).to_bytes(2, "little")
    head[0:2] = P.crc16(head[2:]).to_bytes(2, "little")
    image[0:64] = P.decode_header(head)
    out = bytearray()
    for i in range(20):
        out += image[i * 47:i * 47 + 47] + b"\0"
    out += image[940:]
    return renamed(bytes(out), product)


def community_fixture(product="FM-1_900", vendor_loader=False, loader_name=None):
    data = (renamed(stock_bytes(), product) if vendor_loader
            else with_new_loader(stock_bytes(), product, loader_name))
    meta = {"schema": 1, "kind": "community", "product": product, "family": 7, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "loader_sha256": P.Package(io.BytesIO(data)).inspect() and _loader_sha(data)}
    return P.prepare(meta, io.BytesIO(data))


def _loader_sha(data):
    pkg = P.Package(io.BytesIO(data))
    pkg.inspect()
    return pkg.loader_sha256()


def stock_meta():
    return {"schema": 1, "kind": "stock", "product": "FM-1_015", "family": 7, "bytes": 699956,
            "sha256": P.STOCK_SHA256, "build_id": P.STOCK_SHA256, "loader_sha256": P.VENDOR_LOADER_SHA256}


def open_fixture(product="FM1_OFFICIAL_OPEN", build="cd" * 32):
    data = renamed(stock_bytes(), product)
    meta = {"schema": 1, "kind": "open", "product": product, "family": 7, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "build_id": build,
            "loader_sha256": P.VENDOR_LOADER_SHA256}
    return P.prepare(meta, io.BytesIO(data))


@needs_stock
class Install(unittest.TestCase):
    def run_install(self, pkg, meta, dev, clock, force=False, connect_force=None):
        events = []
        up = U.Updater(finder_for(dev), pkg, meta, status=lambda ph, pct: events.append((ph, pct)), clock=clock)
        info = up.connect(force=force if connect_force is None else connect_force)
        up.install(force=force)
        return info, events

    def test_tagged_open_to_open(self):
        pkg, meta = open_fixture()
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM1_OFFICIAL_OPEN", build="ab" * 32, new_build=meta["build_id"],
                      noise=True)
        info, events = self.run_install(pkg, meta, dev, clock)
        self.assertTrue(info["tagged"])
        self.assertEqual(dev.armed, bytes(P.arm_payload(7, pkg.image_len, meta["build_id"])))
        self.assertEqual([m for _, m in [x for x in dev.log if x[0] == "reset"]], ["loader", "app"])
        self.assertEqual(dev.identity, "FM1_OFFICIAL_OPEN")
        self.assertEqual(events[-1], ("Done", 100))
        self.assertGreater(max(p for ph, p in events if ph == "Writing firmware"), 90)
        self.assertGreaterEqual(dev.served, pkg.flash["size"])

    def test_same_build_is_refused(self):
        pkg, meta = open_fixture()
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, build=meta["build_id"])
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        self.assertTrue(up.connect()["same"])
        with self.assertRaises(P.FM1Error):
            up.install()

    def test_third_party_needs_force(self):
        pkg, meta = open_fixture()
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="SLOOP_FM1", capability=False, new_build=meta["build_id"])
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        self.assertTrue(up.connect()["migration"])
        with self.assertRaises(P.FM1Error):
            up.install()
        self.assertTrue(up.connect(force=True)["legacy"])
        up.install(force=True)
        self.assertEqual(dev.identity, "FM1_OFFICIAL_OPEN")

    def test_stock_to_open_is_legacy(self):
        pkg, meta = open_fixture()
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_015", capability=False, new_build=meta["build_id"])
        info, _ = self.run_install(pkg, meta, dev, clock, force=True)
        self.assertTrue(info["legacy"])
        self.assertIsNone(dev.armed)

    def test_resume_from_loader(self):
        pkg, meta = open_fixture()
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, new_build=meta["build_id"])
        dev.mode = "loader"
        info, _ = self.run_install(pkg, meta, dev, clock)
        self.assertTrue(info["resume"])
        self.assertEqual([x for x in dev.log if x[0] == "reset"], [("reset", "app")])

    def test_back_to_stock_restores_voices(self):
        data = stock_bytes()
        pkg, meta = P.prepare(stock_meta(), io.BytesIO(data))
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM1_OFFICIAL_OPEN", capability=False)
        info, _ = self.run_install(pkg, meta, dev, clock, force=True)
        self.assertEqual(dev.identity, "FM-1_015")
        self.assertEqual(len(dev.bank_writes), 4 * 9)
        written = b"".join(d[8:] for c, d in dev.bank_writes if c == P.CMD_BANK_WRITE)
        self.assertEqual(written, pkg.factory_bank())

    def test_restore_survives_reenumeration_after_boot(self):
        # V15 dropped off the bus ~4 s after its first boot, on the restore's
        # first query (seen on both the PIO port and the pigtail, Oct 27).
        pkg, meta = P.prepare(stock_meta(), io.BytesIO(stock_bytes()))
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM1_OFFICIAL_OPEN", capability=False, reenum_after_boot=3)
        self.run_install(pkg, meta, dev, clock, force=True)
        self.assertIn(("reenumerate",), dev.log)
        self.assertEqual(dev.identity, "FM-1_015")
        written = b"".join(d[8:] for c, d in dev.bank_writes if c == P.CMD_BANK_WRITE)
        self.assertEqual(written, pkg.factory_bank())

    def test_community_back_to_stock(self):
        pkg, meta = P.prepare(stock_meta(), io.BytesIO(stock_bytes()))
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_900", capability=False)
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        self.assertTrue(up.connect()["migration"])
        self.assertTrue(up.connect(force=True)["legacy"])
        self.assertTrue(up.hub_timing)
        up.install(force=True)
        self.assertEqual(dev.identity, "FM-1_015")
        self.assertEqual(len(dev.bank_writes), 36)

    def test_identity_check_retries_an_unanswered_query(self):
        # Once, Aisling didn't answer the identity check that install() makes
        # after connect(); the install then failed at once.
        pkg, meta = P.prepare(stock_meta(), io.BytesIO(stock_bytes()))
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_353000400", capability=False)
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        self.assertTrue(up.connect(force=True)["legacy"])
        dev.ignore_identity = 1
        up.install(force=True)
        self.assertEqual(dev.identity, "FM-1_015")

    def test_stock_on_stock_only_restores(self):
        pkg, meta = P.prepare(stock_meta(), io.BytesIO(stock_bytes()))
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_015", capability=False)
        self.run_install(pkg, meta, dev, clock, force=True)
        self.assertEqual(dev.log, [])
        self.assertEqual(len(dev.bank_writes), 36)

    def test_device_vanishing_mid_transfer_fails(self):
        pkg, meta = open_fixture()
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, build="ab" * 32)
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        up.connect()
        real = dev.receive
        count = [0]

        def flaky(msg, out):
            count[0] += 1
            if count[0] == 30:
                dev.generation += 1  # unplugged
                return
            real(msg, out)
        dev.receive = flaky
        with self.assertRaises(P.FM1Error):
            up.install()

    def test_community_to_community(self):
        pkg, meta = community_fixture("FM-1_900")
        self.assertEqual(meta["loader_identity"], P.COMMUNITY_LOADER)
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_916", capability=False, loader_identity="ota-FM-1_900")
        info, events = self.run_install(pkg, meta, dev, clock)
        self.assertTrue(info["community"])
        self.assertIsNone(dev.armed)
        self.assertEqual([x for x in dev.log if x[0] == "reset"], [("reset", "loader"), ("reset", "app")])
        self.assertEqual(dev.identity, "FM-1_900")
        self.assertEqual(events[-1], ("Done", 100))
        # 10 ms pacing per block is part of the hub's route.
        blocks = (pkg.flash["size"] + pkg.loader["size"]) // 512
        self.assertGreater(clock.t, blocks * 10)

    def test_community_own_loader_name(self):
        # Skiff 2.2's loader answers as ota-FM-1_722, not ota-FM-1_9<nn>.
        pkg, meta = community_fixture("FM-1_722", loader_name="ota-FM-1_722")
        self.assertEqual(meta["loader_identity"], "ota-FM-1_722")
        self.assertTrue(P.loader_matches(meta, "ota-FM-1_722"))
        self.assertTrue(P.loader_matches(meta, "ota-FM-1_900"))  # the Felucca rule still holds
        self.assertFalse(P.loader_matches(meta, "ota-FM-1_015"))
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_900", capability=False, loader_identity="ota-FM-1_722")
        self.run_install(pkg, meta, dev, clock)
        self.assertEqual(dev.identity, "FM-1_722")

    def test_community_vendor_loader(self):
        pkg, meta = community_fixture("FM-1_003", vendor_loader=True)
        self.assertEqual(meta["loader_identity"], "ota-FM-1_015")
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_900", capability=False, loader_identity="ota-FM-1_015")
        self.run_install(pkg, meta, dev, clock)
        self.assertEqual(dev.identity, "FM-1_003")

    def test_community_resume_and_foreign_loader(self):
        pkg, meta = community_fixture("FM-1_900")
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, loader_identity="ota-FM-1_916", capability=False)
        dev.mode = "loader"
        info, _ = self.run_install(pkg, meta, dev, clock)
        self.assertTrue(info["resume"])
        dev = FakeFM1(pkg, clock, loader_identity="ota-FM-1_015", capability=False)
        dev.mode = "loader"
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        with self.assertRaises(P.FM1Error):
            up.connect(force=True)

    def test_community_from_stock_needs_force(self):
        pkg, meta = community_fixture("FM-1_900")
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_015", capability=False, loader_identity="ota-FM-1_900")
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        self.assertTrue(up.connect()["migration"])
        with self.assertRaises(P.FM1Error):
            up.install()
        self.assertTrue(up.connect(force=True)["legacy"])
        up.install(force=True)
        self.assertEqual(dev.identity, "FM-1_900")

    def lossy_install(self, **kw):
        pkg, meta = community_fixture("FM-1_900")
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_916", capability=False, loader_identity="ota-FM-1_900",
                      lossy_over=100, **kw)
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        resends = []
        up.trace = lambda event, *v: resends.append(v) if event == "resend" else None
        up.connect()
        return up, dev, resends

    def test_lost_replies_slow_the_transport(self):
        # Replies are lost until the transport slows down. One slow repeat is
        # enough, and the slower setting carries over into the loader.
        up, dev, resends = self.lossy_install()
        up.install()
        self.assertEqual(dev.identity, "FM-1_900")
        self.assertEqual(len(resends), 1)
        self.assertEqual(resends[0][2], 1)
        self.assertEqual(up.slow_level, 1)
        self.assertIn(("repeat", 0), dev.log)

    def test_lost_replies_in_the_loader_only(self):
        up, dev, resends = self.lossy_install(lossy_modes=("loader",))
        up.install()
        self.assertEqual(dev.identity, "FM-1_900")
        self.assertEqual(len(resends), 1)

    def test_lost_replies_without_slowdown_fail(self):
        pkg, meta = community_fixture("FM-1_900")
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_916", capability=False, loader_identity="ota-FM-1_900",
                      lossy_over=100)

        def finder():
            found = finder_for(dev)()
            for t in found:
                t.slow_down = lambda: False
            return found
        up = U.Updater(finder, pkg, meta, clock=clock)
        up.connect()
        with self.assertRaises(P.FM1Error) as cm:
            up.install()
        self.assertIn("stopped requesting", str(cm.exception))

    def test_quick_repeat_is_not_a_loss(self):
        pkg, meta = community_fixture("FM-1_900")
        clock = FakeClock()
        dev = FakeFM1(pkg, clock, identity="FM-1_916", capability=False, loader_identity="ota-FM-1_900")
        real = dev.receive
        replies = [0]

        def asks_again(msg, out):
            p = P.parse(msg)
            if p and p[0] == P.CMD_READ and dev.requests:
                replies[0] += 1
                if replies[0] == 5:  # ask for the same block again straight away
                    out.append(bytes(P.frame(P.CMD_READ, dev.current)))
                    return
            real(msg, out)
        dev.receive = asks_again
        up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
        resends = []
        up.trace = lambda event, *v: resends.append(v) if event == "resend" else None
        up.connect()
        up.install()
        self.assertEqual(dev.identity, "FM-1_900")
        self.assertEqual(resends, [])
        self.assertEqual(up.slow_level, 0)

    def test_no_device(self):
        pkg, meta = open_fixture()
        up = U.Updater(lambda: [], pkg, meta, clock=FakeClock())
        with self.assertRaises(P.FM1Error):
            up.connect()


if __name__ == "__main__":
    unittest.main()


PKGS = os.environ.get("FM1_TEST_PKGS")


class Catalog(unittest.TestCase):
    CAT = {"stock": {"pkg": "fw/mvave/FM-1_015.fwsc"},
           "firmwares": [{"id": "sloop", "pkg": "fw/sloop.fwsc", "install": None},
                         {"id": "fizz", "pkg": "fw/fizz.fwsc", "install": "https://example.com/fizz/install/"},
                         {"id": "nopkg", "pkg": None}]}

    def test_own_installers_are_left_out(self):
        ids = [e["id"] for e in make_sd.catalog_entries(self.CAT, [])]
        self.assertEqual(ids, ["stock-v15", "sloop"])
        with self.assertRaises(SystemExit):
            make_sd.catalog_entries(self.CAT, ["fizz"])

    def test_nothing_is_removed_from_the_card(self):
        # A firmware the hub moves to its own installer stays on the card.
        self.assertFalse(hasattr(make_sd, "remove_own_installers"))


@unittest.skipUnless(PKGS, "set FM1_TEST_PKGS to a folder of community .fwsc files")
class RealCommunityPackages(unittest.TestCase):
    def test_parse_and_install(self):
        names = [n for n in sorted(os.listdir(PKGS)) if n.endswith(".fwsc")]
        self.assertTrue(names)
        for n in names:
            with self.subTest(n):
                data = open(os.path.join(PKGS, n), "rb").read()
                pkg = P.Package(io.BytesIO(data))
                pkg.inspect(strict=False)
                if not P.community_identity(pkg.product):
                    continue
                meta = {"schema": 1, "kind": "community", "product": pkg.product, "family": 7,
                        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                        "loader_sha256": pkg.loader_sha256()}
                pkg, meta = P.prepare(meta, io.BytesIO(data))
                ld = "ota-FM-1_015" if meta["loader_identity"] == "ota-FM-1_015" else "ota-FM-1_950"
                clock = FakeClock()
                dev = FakeFM1(pkg, clock, identity="FM-1_999", capability=False, loader_identity=ld)
                up = U.Updater(finder_for(dev), pkg, meta, clock=clock)
                up.connect()
                up.install()
                self.assertEqual(dev.identity, pkg.product)
