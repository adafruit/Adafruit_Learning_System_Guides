# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""FM-1 update protocol and .fwsc package parsing.

Ported from M-VAVE's sdk/WebUpdate.js (fm1_open @ 4c7496d). Runs on CPython
and CircuitPython: no dataclasses, typing, or re. Packages are streamed from
a file object; only image[0:940] and small tables are held in RAM.
"""

# Disabled for the Learn Guides lint check: some drawing and protocol functions are long by
# nature.
# pylint: disable=too-many-locals
import binascii

try:
    import hashlib
except ImportError:
    try:
        import adafruit_hashlib as hashlib
    except ImportError:
        hashlib = None


class FM1Error(Exception):
    pass


def check(ok, text):
    if not ok:
        raise FM1Error(text)


# --- Constants ---------------------------------------------------------------

CMD_ACK = 0
CMD_IDENTITY = 17
CMD_BANK_BEGIN = 33
CMD_BANK_WRITE = 34
CMD_READ = 48
CMD_CAPABILITY = 49
CMD_ARM = 50

KICK = b"\xf0\x22\x24\x35\x7f\xf7"
FINISH_STAGE1 = 0xE0000000
FINISH_STAGE2 = 0xF0000000
SUCCESS = b"success\x00"

FAMILY = 7
STOCK_PRODUCT = "FM-1_015"
STOCK_SHA256 = "db1642b2b6fa5c2cccb11ffd13878068bb28601678d3644049f99dc40e7edb8a"
VENDOR_LOADER_SHA256 = "ef1f2db89b011fa53e71df363f0122de0ea896618c53fb53e8da676322004541"
FACTORY_SHA256 = "ecad0b8620f9d784d46c8da1e3c5de02c40214649ed8dec218026431046aad25"

PKG_MIN = 1024
PKG_MAX = 2097152
ROWS = 20
ROW_DATA = 47
ROW_SIZE = 48
HEAD_IMAGE = ROWS * ROW_DATA  # 940
HEAD_FILE = ROWS * ROW_SIZE  # 960


# --- Helpers -----------------------------------------------------------------

def le(p, at, n):
    v = 0
    for i in range(n):
        v |= p[at + i] << (8 * i)
    return v


def ascii_z(p):
    """ASCII up to the first NUL, like WebUpdate.js ascii()."""
    p = bytes(p)
    end = p.find(b"\x00")
    if end >= 0:
        p = p[:end]
    return "".join(chr(b) for b in p)


def hexstr(p):
    return binascii.hexlify(bytes(p)).decode()


def is_hex64(s):
    if not isinstance(s, str) or len(s) != 64:
        return False
    for c in s:
        if c not in "0123456789abcdef":
            return False
    return True


def open_identity(s):
    """^(FM1_OFFICIAL_OPEN|FM1_COMMUNITY_\\d+|FM-1_8\\d{6})$"""
    if s == "FM1_OFFICIAL_OPEN":
        return True
    if s.startswith("FM1_COMMUNITY_"):
        tail = s[14:]
        return len(tail) > 0 and tail.isdigit()
    if s.startswith("FM-1_8"):
        tail = s[6:]
        return len(tail) == 6 and tail.isdigit()
    return False


def community_identity(s):
    """FM-1_<digits>: the identities the Felucca/SLOOP family and the hub use."""
    return s.startswith("FM-1_") and len(s) > 5 and s[5:].isdigit()


def is_loader(s):
    return s.lower().startswith("ota-")


def sha256():
    """A new sha256 object, or None when no hashlib is available."""
    if hashlib is None:
        return None
    try:
        return hashlib.sha256()
    except (AttributeError, ValueError):
        pass
    try:
        return hashlib.new("sha256")  # CircuitPython's hashlib has only new()
    except (AttributeError, ValueError):
        return None


# CRC-16/XMODEM (poly 0x1021, init 0). WebUpdate.js computes it a nibble at
# a time; a byte table gives identical results and is twice as fast.
def _crc_table():
    t = []
    for i in range(256):
        c = i << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) if c & 0x8000 else (c << 1)
        t.append(c & 0xFFFF)
    return tuple(t)


_CRC_T = _crc_table()
_crc_hqx = getattr(binascii, "crc_hqx", None)


def crc16(data, c=0):
    if _crc_hqx is not None:
        return _crc_hqx(data, c)
    t = _CRC_T
    for b in data:
        c = ((c << 8) & 0xFFFF) ^ t[(c >> 8) ^ b]
    return c


def decode_header(data, key=0xFFFF):
    """XOR with the LFSR key stream. Returns a new bytearray."""
    p = bytearray(data)
    _decode_into(p, 0, len(p), key)
    return p


def _decode_into(p, start, end, key):
    """decode_header() on p[start:end] in place."""
    k = key
    for i in range(start, end):
        p[i] ^= k & 0xFF
        k = ((k << 1) ^ (0x1021 if k & 0x8000 else 0)) & 0xFFFF


# --- SysEx framing -----------------------------------------------------------

def _pack7_into(raw, out, o):
    """7-bit pack raw into out at o (LSB-first bit stream); returns the end.
    Whole 7-byte groups become 8 bytes with fixed shifts, which is several
    times faster on CircuitPython than a per-bit loop."""
    n = len(raw)
    full = n - n % 7
    i = 0
    while i < full:
        b0 = raw[i]
        b1 = raw[i + 1]
        b2 = raw[i + 2]
        b3 = raw[i + 3]
        b4 = raw[i + 4]
        b5 = raw[i + 5]
        b6 = raw[i + 6]
        out[o] = b0 & 0x7F
        out[o + 1] = ((b0 >> 7) | (b1 << 1)) & 0x7F
        out[o + 2] = ((b1 >> 6) | (b2 << 2)) & 0x7F
        out[o + 3] = ((b2 >> 5) | (b3 << 3)) & 0x7F
        out[o + 4] = ((b3 >> 4) | (b4 << 4)) & 0x7F
        out[o + 5] = ((b4 >> 3) | (b5 << 5)) & 0x7F
        out[o + 6] = ((b5 >> 2) | (b6 << 6)) & 0x7F
        out[o + 7] = b6 >> 1
        i += 7
        o += 8
    bits = 0
    value = 0
    while i < n:
        value |= raw[i] << bits
        bits += 8
        i += 1
        while bits >= 7:
            out[o] = value & 0x7F
            o += 1
            value >>= 7
            bits -= 7
    if bits:
        out[o] = value & 0x7F
        o += 1
    return o


def _packed_len(n):
    return (n * 8 + 6) // 7


def pack7(data):
    out = bytearray(_packed_len(len(data)))
    _pack7_into(data, out, 0)
    return out


def frame(command, payload=b""):
    n = len(payload)
    check(n <= 520, "payload too long")
    raw = bytearray(n + 7)
    raw[0:6] = bytes((0x00, 0x59, command, n & 0xFF, n >> 8, 0))
    raw[6:6 + n] = payload
    raw[6 + n] = ~sum(payload) & 0xFF
    out = bytearray(_packed_len(n + 7) + 2)
    out[0] = 0xF0
    out[-1] = 0xF7
    _pack7_into(raw, out, 1)
    return out


def parse(sysex):
    """Returns (command, data) or None for anything that isn't a valid reply."""
    n = len(sysex) if sysex else 0
    if n < 10 or n > 608 or sysex[0] != 0xF0 or sysex[n - 1] != 0xF7:
        return None
    raw = bytearray()
    bits = 0
    value = 0
    for i in range(1, n - 1):
        b = sysex[i]
        if b > 127:
            return None
        value |= b << bits
        bits += 7
        if bits >= 8:
            raw.append(value & 0xFF)
            value >>= 8
            bits -= 8
    if bits >= 7 or value != 0 or len(raw) < 7 or raw[0] != 0 or raw[1] != 0x59:
        return None
    if le(raw, 3, 3) != len(raw) - 7:
        return None
    s = 0
    for i in range(6, len(raw)):
        s += raw[i]
    if s & 0xFF != 0xFF:
        return None
    return raw[2], bytes(raw[6:-1])


# --- Message payloads --------------------------------------------------------

def identity(data):
    s = ascii_z(data)
    ok = len(data) == 27 and 1 <= len(s) <= 27
    for c in s:
        ok = ok and 0x20 <= ord(c) <= 0x7E
    check(ok, "invalid identity reply")
    return s


def capability(data):
    check(len(data) == 47 and data[0:4] == b"FMC1" and data[4] == 1 and data[5] <= 7
          and le(data, 8, 2) == 512 and le(data, 10, 4) == 1048576,
          "update protocol mismatch")
    check(data[7] == 1, "device uses an unknown update loader")
    return {"family": data[5], "state": data[6], "build": hexstr(data[14:46]), "error": data[46]}


def arm_payload(family, image_len, build_id):
    n = image_len
    p = bytearray((1, family, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF, (n >> 24) & 0xFF))
    p.extend(binascii.unhexlify(build_id))
    return p


def read_request(data):
    """(seq, address, nbytes) from an 8-byte cmd 48 request, else None."""
    if len(data) != 8:
        return None
    return data[0], le(data, 1, 4), le(data, 5, 3)


def read_reply(req, chunk):
    p = bytearray(req[0:8])
    p.extend(chunk)
    return frame(CMD_READ, p)


def bank_begin_payload(bank):
    return bytes((5, 0, bank >> 8, 0, 0))


def bank_write_payload(offset, chunk):
    p = bytearray((5, offset & 0xFF, offset >> 8, 0, 0, 0, 2, 0))
    p.extend(chunk)
    return p


COMMUNITY_LOADER = "ota-FM-1_9xx"
_OTA = b"ota-FM-1_"


def package_loader_identity(pkg):
    """The identity a community package's own loader answers with, as its
    loader entry spells it ("ota-FM-1_<digits>"), or None when it has none
    or several. Most say ota-FM-1_900, but Skiff 2.2 says ota-FM-1_722 and
    Matryoshka ota-FM-1_700. Read in chunks (the loader is up to 32 KB)."""
    found = set()
    tail = b""
    for chunk in pkg.chunks(pkg.loader["offset"], pkg.loader["size"], 1024):
        data = tail + bytes(chunk)
        i = data.find(_OTA)
        while i >= 0:
            j = i + len(_OTA)
            while j < len(data) and 48 <= data[j] <= 57:
                j += 1
            if i + len(_OTA) < j < len(data):  # digits, and the end of them is in view
                found.add(data[i:j].decode())
            i = data.find(_OTA, i + 1)
        tail = data[-16:]  # a name split across chunks is found whole in the next
    return found.pop() if len(found) == 1 else None


def loader_identity(meta, pkg=None):
    if meta["loader_sha256"] == VENDOR_LOADER_SHA256:
        return "ota-FM-1_015"
    if meta.get("kind") == "stock":
        return "ota-" + meta["product"]
    if meta.get("kind") == "community":
        # The package's own loader's name when it has one; else the rule
        # Felucca-derived loaders follow, ota-FM-1_9<nn>.
        if pkg is not None:
            return package_loader_identity(pkg) or COMMUNITY_LOADER
        return COMMUNITY_LOADER
    return "ota-FM1C_" + meta["build_id"][:16]


def loader_matches(meta, ident):
    """Is `ident` the loader this package's install waits for? A community
    package's loader may answer as ota-FM-1_9<nn> (the Felucca rule, which
    every one used until Skiff 2.2) or as its own loader spells itself."""
    want = meta["loader_identity"]
    if ident == want:
        return True
    if want == COMMUNITY_LOADER or (meta.get("kind") == "community" and want != "ota-FM-1_015"):
        return (len(ident) == 12 and ident.lower().startswith("ota-fm-1_9")
                and ident[10:].isdigit())
    return False


# --- Packages ----------------------------------------------------------------

def file_offset(x):
    """File offset of image address x."""
    if x < HEAD_IMAGE:
        return (x // ROW_DATA) * ROW_SIZE + (x % ROW_DATA)
    return x + ROWS


class Package:
    """A .fwsc package streamed from a binary file object.

    `image` addresses are what the FM-1 requests; the file interleaves the
    first 940 image bytes with 20 identity marker bytes.
    """

    def __init__(self, f, size=None):
        self.f = f
        if size is None:
            f.seek(0, 2)
            size = f.tell()
        self.file_size = size
        check(PKG_MIN <= size <= PKG_MAX, "invalid package length")
        self.image_len = size - ROWS
        f.seek(0)
        rows = f.read(HEAD_FILE)
        check(len(rows) == HEAD_FILE, "short read")
        head = bytearray()
        product = ""
        ended = False
        for i in range(ROWS):
            head.extend(rows[i * ROW_SIZE:i * ROW_SIZE + ROW_DATA])
            marker = rows[i * ROW_SIZE + ROW_DATA]
            if marker == 125:
                ended = True
            else:
                c = (marker - i - 1) & 0xFF
                check(not ended and 32 <= c <= 126, "invalid package identity")
                product += chr(c)
        self.product = product
        self.head = bytes(head)
        self.entries = None
        self.flash = self.loader = None  # set by the entries' check

    def read_into(self, address, buf, n=None):
        """Fill buf[0:n] with image[address:address+n]."""
        if n is None:
            n = len(buf)
        check(address + n <= self.image_len, "read past end of image")
        done = 0
        if address < HEAD_IMAGE:
            k = min(n, HEAD_IMAGE - address)
            buf[0:k] = self.head[address:address + k]
            done = k
        if done < n:
            self.f.seek(address + done + ROWS)
            mv = memoryview(buf)
            while done < n:
                got = self.f.readinto(mv[done:n])
                check(got, "short read")
                done += got
        return buf

    def read(self, address, n):
        return bytes(self.read_into(address, bytearray(n)))

    def chunks(self, offset, size, step=2048):
        buf = bytearray(step)
        end = offset + size
        while offset < end:
            n = min(step, end - offset)
            self.read_into(offset, buf, n)
            yield memoryview(buf)[:n]
            offset += n

    def inspect(self, verify=True, strict=True):
        """Port of inspectPackage(). With verify=False the entry CRCs (a pass
        over the whole image) are skipped; header and table checks still run.

        strict=False accepts an entry whose stored length runs past the end of
        the file when only its 32-byte alignment padding is missing (size
        still fits, stored - size < 32). Felucca-family packages trim that
        padding from the trailing ota.bin; WebUpdate.js rejects them."""
        head = decode_header(self.read(0, 64))
        count = le(head, 8, 2)
        check(le(head, 0, 2) == crc16(head[2:]) and le(head, 4, 4) == self.image_len,
              "package header check failed")
        check(ascii_z(head[16:32]) == "AC791N" and 0 < count <= 12, "bad chip type or entry count")
        table = self.read(64, count * 80)
        check(crc16(table) == le(head, 2, 2), "entry table check failed")
        entries = []
        for i in range(count):
            e = decode_header(table[i * 80:i * 80 + 80])
            ent = {
                "type": le(e, 0, 2), "crc": le(e, 4, 2), "offset": le(e, 8, 4),
                "size": le(e, 12, 4), "stored": le(e, 16, 4), "encrypted": le(e, 24, 4),
                "name": ascii_z(e[64:]),
            }
            off, size, stored, enc = ent["offset"], ent["size"], ent["stored"], ent["encrypted"]
            check(64 + count * 80 <= off <= self.image_len and size <= self.image_len - off,
                  "entry out of bounds")
            fits = stored <= self.image_len - off
            if not fits and not strict:
                fits = stored - size < 32
            check(stored >= size and fits and (not enc or enc == stored), "invalid stored length")
            for p in entries:
                check(not (stored and p["stored"] and off < p["offset"] + p["stored"]
                           and p["offset"] < off + stored), "entries overlap")
            if verify and not enc:
                c = 0
                for chunk in self.chunks(off, size):
                    c = crc16(chunk, c)
                check(c == ent["crc"], "entry CRC failed: " + ent["name"])
            check(
                not enc or (ent["type"] != 0 and ent["type"] != 100),
                "flash or loader entry is encrypted",
            )
            entries.append(ent)
        flash = [e for e in entries if e["type"] == 0]
        loader = [e for e in entries if e["type"] == 100]
        check(
            len(flash) == 1
            and 16384 <= flash[0]["size"] <= 1044480
            and flash[0]["size"] % 4096 == 0,
            "invalid flash image",
        )
        check(len(loader) == 1 and 0 < loader[0]["size"] < 32768, "missing or invalid loader")
        self.entries = entries
        self.flash = flash[0]
        self.loader = loader[0]
        return entries

    def loader_sha256(self):
        h = sha256()
        if h is None:
            return None
        for chunk in self.chunks(self.loader["offset"], self.loader["size"]):
            h.update(chunk)
        return hexstr(h.digest())

    def factory_bank(self):
        """The 16 KB of factory voice banks from the stock package's USR entry."""
        banks = [e for e in self.entries if e["type"] == 50 and e["name"] == "USR"]
        check(len(banks) == 1 and banks[0]["size"] == 73226 and banks[0]["encrypted"] == 73248,
              "invalid factory voice data (layout)")
        e = banks[0]
        # One up-front allocation: growing and copying 16 KB fails on a fragmented
        # CircuitPython heap after a long install.
        out = bytearray(16384)
        buf = bytearray(1024)
        mv = memoryview(buf)
        pos = 0
        c = 0
        # Read 1 KB at a time and decode its 32-byte blocks in place: one read
        # per block took 3.9 s on the RP2040, mostly seeks and allocations.
        for i in range(0, e["stored"], 1024):
            n = min(1024, e["stored"] - i)
            self.read_into(e["offset"] + i, buf, n)
            for b in range(0, n, 32):
                _decode_into(buf, b, b + 32, 0x980F ^ ((e["offset"] + i + b) >> 2))
            k = min(n, e["size"] - i)
            if k > 0:
                c = crc16(mv[:k], c)
            if pos < 16384:
                k = min(n, 16384 - pos)
                out[pos:pos + k] = mv[:k]
                pos += k
        check(c == e["crc"] and pos == 16384, "invalid factory voice data (CRC)")
        return out


def check_sha256(compute, expected, text, tries=3):
    """check() that compute() gives `expected`, recomputing after a mismatch.
    CircuitPython 11's hashlib can return a wrong digest with no error
    (DEVNOTES 6.7, 6.9). A wrong digest never matches by chance, so any
    match can be trusted, and only a repeated mismatch fails. compute()
    returns None when there is no hashlib."""
    for attempt in range(tries):
        digest = compute()
        if digest is None or digest == expected:
            return
        # All zeros: the hash failed outright, and hashlib didn't say so
        print("SHA-256 %s, try %d of %d (%s): %s" % ("failed" if digest == "0" * 64 else "mismatch",
                                                     attempt + 1, tries, text, digest))
    check(False, text)


def file_sha256(f, step=4096):
    h = sha256()
    if h is None:
        return None
    f.seek(0)
    buf = bytearray(step)
    mv = memoryview(buf)
    while True:
        n = f.readinto(buf)
        if not n:
            break
        h.update(mv[:n])
    return hexstr(h.digest())


def prepare(meta, f, verify=True, checked=False):
    """Port of prepare(): validate meta.json against the package in f.

    kind is "open" (FM1 Open, WebUpdate.js rules), "stock" (M-VAVE V15), or
    "community" (FM-1_<n> firmwares installed the way the Firmware Hub does:
    no build_id, no capability or arm commands, their own loader).

    verify=False skips whole-file SHA-256 and entry CRCs (slow on RP2040);
    use it only when the SD card was prepared and checked by tools/make_sd.py.
    checked=True keeps the whole-file SHA-256 but, once it matches, skips the
    entry CRCs and the factory voice checks: make_sd.py ran them on the same
    bytes, and on the RP2040 they take 12 of the 14 seconds (DEVNOTES 6.10).
    Returns (Package, meta with loader_identity added).
    """
    kind = meta.get("kind")
    stock = kind == "stock"
    community = kind == "community"
    product = meta.get("product", "")
    if stock:
        ok = product == STOCK_PRODUCT
    elif community:
        ok = community_identity(product)
    else:
        ok = kind in (None, "open") and open_identity(product)
    check(meta.get("schema") == 1 and ok and (community or is_hex64(meta.get("build_id"))),
          "invalid firmware metadata")
    check(
        is_hex64(meta.get("sha256")) and is_hex64(meta.get("loader_sha256")),
        "invalid firmware metadata",
    )
    if stock:
        check(
            meta["sha256"] == STOCK_SHA256 and meta["build_id"] == meta["sha256"],
            "stock firmware check failed",
        )
    check(
        meta.get("family") == FAMILY and PKG_MIN <= meta.get("bytes", 0) <= PKG_MAX,
        "invalid firmware configuration",
    )
    pkg = Package(f)
    check(pkg.file_size == meta["bytes"], "package size does not match metadata")
    if verify:
        check_sha256(lambda: file_sha256(f), meta["sha256"], "package SHA-256 check failed")
        if checked and sha256() is not None:
            verify = False  # the SHA-256 matched, so these bytes passed make_sd.py
    pkg.inspect(verify, strict=not community)
    check(pkg.product == product, "package identity does not match metadata")
    check_sha256(pkg.loader_sha256, meta["loader_sha256"], "loader does not match metadata")
    if stock and verify:
        bank = pkg.factory_bank()

        def bank_sha256():
            h = sha256()
            if h is None:
                return None
            # 1 KB at a time: as one 16 KB update() the digest came back all
            # zeros, every try, on a fragmented heap (DEVNOTES 6.9). mbedtls
            # may copy each update's input to a temporary buffer.
            mv = memoryview(bank)
            for i in range(0, len(bank), 1024):
                h.update(mv[i:i + 1024])
            return hexstr(h.digest())

        check_sha256(bank_sha256, FACTORY_SHA256, "invalid factory voice data (SHA-256)")
        del bank
    meta = dict(meta)
    meta["loader_identity"] = loader_identity(meta, pkg)
    return pkg, meta
