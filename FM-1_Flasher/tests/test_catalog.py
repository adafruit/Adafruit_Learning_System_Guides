# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""fm1catalog (the hub catalogue and the card's folders) and fm1pic (hub
pictures as thumb.bmp), as the Metro's Update firmwares uses them."""
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "FM-1_Flasher_Code", "lib"))
sys.path.insert(0, HERE)

import fm1catalog as K  # noqa: E402
import fm1pic  # noqa: E402
from test_fm1 import STOCK, needs_stock, renamed, stock_bytes  # noqa: E402


def entry(cid, data, product="FM-1_900", **kw):
    e = {"id": cid, "name": cid.upper(), "pkg": "fw/%s.fwsc" % cid, "product": product, "size": len(data),
         "sha256": hashlib.sha256(data).hexdigest(), "version": "1.0", "kind": "groove", "install": None}
    e.update(kw)
    return e


def put(root, slug, meta, data=b"x"):
    d = os.path.join(root, slug)
    os.makedirs(d, exist_ok=True)
    meta = dict(meta)
    meta.setdefault("file", meta.get("product", "FM-1_900") + ".fwsc")
    with open(os.path.join(d, meta["file"]), "wb") as f:
        f.write(data)
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f)


class Plan(unittest.TestCase):
    def test_new_changed_same_and_nothing_removed(self):
        with tempfile.TemporaryDirectory() as root:
            same, newer = b"same", b"newer"
            cat = {"updated": "2026-11-03 03:00 UTC", "firmwares": [
                entry("keep", same), entry("bump", newer), entry("fresh", b"fresh"),
                entry("fizz", b"f", install="https://example.com/fizz/")]}
            put(root, "keep", {"catalog_id": "keep", "sha256": cat["firmwares"][0]["sha256"]}, same)
            put(root, "bump", {"catalog_id": "bump", "sha256": "0" * 64})
            put(root, "gone", {"catalog_id": "gone", "sha256": "1" * 64})  # the hub dropped it
            put(root, "fizz", {"catalog_id": "fizz", "sha256": "2" * 64})  # now its own installer
            put(root, "mine", {"sha256": "3" * 64})  # added by hand: never touched
            p = K.Plan(cat, root)
            self.assertEqual([e["id"] for e in p.new], ["fresh"])
            self.assertEqual([e["id"] for e in p.changed], ["bump"])
            self.assertEqual([e["id"] for e in p.same], ["keep"])
            self.assertFalse(hasattr(p, "removed"))  # dropped firmwares stay on the card
            self.assertEqual(p.bytes, len(newer) + len(b"fresh"))
            self.assertEqual(p.summary(), "1 new, 1 updated, 0.0 MB")

    def test_unticked_are_not_downloaded(self):
        with tempfile.TemporaryDirectory() as root:
            cat = {"firmwares": [entry("a", b"aa"), entry("b", b"bbb"), entry("c", b"c")]}
            put(root, "c", {"catalog_id": "c", "sha256": "0" * 64})
            p = K.Plan(cat, root)
            p.skip = {"b", "c"}
            self.assertEqual([e["id"] for e in p.offered], ["a", "b", "c"])
            self.assertEqual([e["id"] for e in p.downloads], ["a"])
            self.assertEqual((p.picked(p.new), p.picked(p.changed), p.bytes), (1, 0, 2))
            self.assertEqual(p.summary(), "1 new, 0.0 MB")
            p.skip = {"a", "b", "c"}
            self.assertEqual(p.summary(), "Nothing picked")

    def test_up_to_date(self):
        with tempfile.TemporaryDirectory() as root:
            data = b"pkg"
            cat = {"firmwares": [entry("a", data)]}
            put(root, "a", {"catalog_id": "a", "sha256": cat["firmwares"][0]["sha256"]}, data)
            self.assertEqual(K.Plan(cat, root).summary(), "Up to date")

    def test_dates_for_older_cards(self):
        """A card made before the lists sorted by date gets the catalogue's
        dates copied into unchanged firmwares' meta.json, and index.txt."""
        with tempfile.TemporaryDirectory() as root:
            data = b"pkg"
            e = entry("a", data, added="2026-10-08", date="2026-10-24")
            cat = {"firmwares": [e]}
            put(root, "a", {"catalog_id": "a", "sha256": e["sha256"], "name": "A", "product": "FM-1_900",
                            "date": "2026-10-24"}, data)
            p = K.Plan(cat, root)
            self.assertEqual(p.summary(), "Up to date")
            self.assertEqual([x["id"] for x in p.dated], ["a"])
            K.set_dates(root, e)
            self.assertEqual(K.Plan(cat, root).dated, [])
            self.assertEqual(K.read_meta(os.path.join(root, "a"))["added"], "2026-10-08")
            K.write_index(root)
            with open(os.path.join(root, "index.txt")) as f:
                self.assertTrue(f.read().endswith("\tFM-1_900\t2026-10-08\t2026-10-24\n"))

    def test_meta_keeps_the_dates(self):
        meta = K.meta_for(entry("a", b"x", added="2026-10-08", date="2026-10-24"))
        self.assertEqual((meta["added"], meta["date"]), ("2026-10-08", "2026-10-24"))


class Card(unittest.TestCase):
    def test_index_skips_folders_without_meta(self):
        with tempfile.TemporaryDirectory() as root:
            put(root, "b", {"name": "Beta", "version": "2", "genre": "synth", "product": "FM-1_900"})
            put(root, "s", {"name": "Zed V15", "kind": "stock", "product": "FM-1_015"})
            os.makedirs(os.path.join(root, "half"))  # an interrupted download
            self.assertEqual(K.write_index(root, "today"), 2)
            with open(os.path.join(root, "index.txt")) as f:
                lines = f.read().splitlines()
            self.assertEqual(lines, ["updated\ttoday", "s\tZed V15\t\tstock\t0\tFM-1_015\t\t",
                                     "b\tBeta\t2\tsynth\t0\tFM-1_900\t\t"])
            K.write_index(root)  # keeps the date
            with open(os.path.join(root, "index.txt")) as f:
                self.assertEqual(f.readline(), "updated\ttoday\n")
            self.assertFalse(os.path.exists(os.path.join(root, "index.txt.part")))

    def test_remove_on_request(self):
        with tempfile.TemporaryDirectory() as root:
            put(root, "a", {"name": "A", "product": "FM-1_900", "catalog_id": "a"})
            put(root, "b", {"name": "B", "product": "FM-1_901"})
            with open(os.path.join(root, "a", "thumb.bmp"), "wb") as f:
                f.write(b"bmp")
            K.write_index(root, "today")
            K.remove(root, "a")
            self.assertFalse(os.path.exists(os.path.join(root, "a")))
            with open(os.path.join(root, "index.txt")) as f:
                lines = f.read().splitlines()
            self.assertEqual(lines[0], "updated\ttoday")
            self.assertEqual([x.split("\t")[0] for x in lines[1:]], ["b"])

    def test_clean_parts(self):
        with tempfile.TemporaryDirectory() as root:
            put(root, "a", {"catalog_id": "a"})
            for p in ("a/FM-1_900.fwsc.part", "a/meta.json.part", "index.txt.part"):
                open(os.path.join(root, p), "w").close()
            K.clean_parts(root)
            self.assertEqual(sorted(os.listdir(os.path.join(root, "a"))), ["FM-1_900.fwsc", "meta.json"])
            self.assertEqual(os.listdir(root), ["a"])


class Download(unittest.TestCase):
    @staticmethod
    def chunks(data, size=1000):
        def stream(url):
            for i in range(0, len(data), size):
                yield data[i:i + size]
        return stream

    def test_mismatch_leaves_the_card_as_it_was(self):
        with tempfile.TemporaryDirectory() as root:
            e = entry("a", b"real package")
            with self.assertRaises(ValueError):
                list(K.download(root, e, self.chunks(b"something else")))
            self.assertEqual(os.listdir(os.path.join(root, "a")), [])

    def test_rejected_package_is_not_stored(self):
        with tempfile.TemporaryDirectory() as root:
            data = b"not a package" * 100
            with self.assertRaises(Exception):
                list(K.download(root, entry("a", data), self.chunks(data)))
            self.assertEqual(os.listdir(os.path.join(root, "a")), [])

    @needs_stock
    def test_download_checks_and_stores(self):
        data = renamed(stock_bytes(), "FM-1_900")
        with tempfile.TemporaryDirectory() as root:
            put(root, "a", {"catalog_id": "a", "sha256": "0" * 64, "file": "FM-1_901.fwsc"})  # the old version
            e = entry("a", data)
            done = list(K.download(root, e, self.chunks(data, 8192)))
            self.assertEqual(done[-1], len(data))
            self.assertEqual(sorted(os.listdir(os.path.join(root, "a"))), ["FM-1_900.fwsc", "meta.json"])
            meta = K.read_meta(os.path.join(root, "a"))
            self.assertEqual((meta["catalog_id"], meta["kind"], meta["file"]), ("a", "community", "FM-1_900.fwsc"))
            self.assertTrue(K.matches(root, e))
            self.assertTrue(STOCK)

    @needs_stock
    def test_stop_mid_download(self):
        data = renamed(stock_bytes(), "FM-1_900")
        closed = []

        def stream(url):
            try:
                for i in range(0, len(data), 8192):
                    yield data[i:i + 8192]
            finally:
                closed.append(True)
        with tempfile.TemporaryDirectory() as root:
            dl = K.download(root, entry("a", data), stream)
            next(dl)
            next(dl)
            dl.close()  # Stop
            self.assertEqual(closed, [True])
            K.clean_parts(root)
            self.assertEqual(os.listdir(os.path.join(root, "a")), [])


def png(width, height, rows, ctype=2, palette=None):
    """A PNG of `rows` (bytes, without filter bytes), each row filtered with
    every filter type in turn, so the decoder sees all five."""
    ch = fm1pic._CHANNELS[ctype]
    bpp = ch
    out = bytearray()
    prev = bytes(width * ch)
    for y, row in enumerate(rows):
        f = y % 5
        enc = bytearray(len(row))
        for i in range(len(row)):
            a = row[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 0:
                pred = 0
            elif f == 1:
                pred = a
            elif f == 2:
                pred = b
            elif f == 3:
                pred = (a + b) >> 1
            else:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
            enc[i] = (row[i] - pred) & 0xFF
        out += bytes((f,)) + enc
        prev = row

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, ctype, 0, 0, 0))
    if palette:
        data += chunk(b"PLTE", bytes(palette))
    return data + chunk(b"IDAT", zlib.compress(bytes(out))) + chunk(b"IEND", b"")


class Pictures(unittest.TestCase):
    def test_decode_every_filter(self):
        import random
        rnd = random.Random(1)
        w, h = 37, 23
        rows = [bytes(rnd.randrange(256) for _ in range(w * 3)) for _ in range(h)]
        width, height, ct, pal, z = fm1pic.read_png(png(w, h, rows))
        r = fm1pic._Rows(zlib.decompress(z), width, 3)
        self.assertEqual([r.next_row() for _ in range(h)], rows)

    def test_flat_rows_take_the_quick_paeth(self):
        # pixel art: runs of one colour, so most Paeth bytes are Sub
        rows = []
        for y in range(30):
            rows.append(b"".join(bytes((((x // 6) * 40 + y // 6) & 0xFF, 7, x // 6)) for x in range(60)))
        width, height, ct, pal, z = fm1pic.read_png(png(60, 30, rows))
        r = fm1pic._Rows(zlib.decompress(z), width, 3)
        self.assertEqual([r.next_row() for _ in range(30)], rows)

    def test_thumbnail(self):
        # 160x80 palette picture, letterboxed onto a square, 3 colours
        rows = [bytes((x // 60) % 3 for x in range(160)) for _ in range(80)]
        data = png(160, 80, rows, ctype=3, palette=(255, 0, 0, 0, 255, 0, 0, 0, 255))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "thumb.bmp")
            list(fm1pic.convert(data, path))
            with open(path, "rb") as f:
                bmp = f.read()
        self.assertEqual(bmp[:2], b"BM")
        w, h, planes, bpp = struct.unpack("<iiHH", bmp[18:30])
        colours = struct.unpack("<I", bmp[46:50])[0]
        self.assertEqual((w, h, bpp), (80, 80, 8))
        self.assertEqual(colours, 4)  # red, green, blue and the padding
        self.assertEqual(len(bmp), struct.unpack("<I", bmp[10:14])[0] + 80 * 80)

    def test_quantize_to_16(self):
        pixels = [(i * 2654435761) & 0xFFFFFF for i in range(6400)]
        pal, idx = fm1pic.quantize(pixels)
        self.assertLessEqual(len(pal), 16)
        self.assertEqual(len(idx), 6400)
        self.assertLess(max(idx), len(pal))


if __name__ == "__main__":
    unittest.main()
