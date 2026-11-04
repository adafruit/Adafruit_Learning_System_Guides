# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""FM-1 install sequence (Link and Updater from WebUpdate.js).

Transport-independent. A transport is any object with:
    send(sysex)        send one complete F0..F7 message
    recv(timeout_ms)   one complete SysEx message (bytes), or None on timeout
    lost               True once the device has gone away
    close()
A finder is a callable returning a list of open candidate transports; it is
called again after each re-enumeration.
"""

# Disabled for the Learn Guides lint check: modules are imported where they're needed, to keep RAM
# free and start-up quick; methods kept on their class: the screen interface, or overridden;
# self.trace is called only after checking it's set; some drawing and protocol functions are long
# by nature.
# pylint: disable=import-outside-toplevel,no-self-use,not-callable,too-many-branches,too-many-locals
# pylint: disable=too-many-return-statements,too-many-statements
import time

import fm1proto as P
from fm1proto import FM1Error, check


class FM1Timeout(FM1Error):
    pass


class Clock:
    def now_ms(self):
        if hasattr(time, "monotonic_ns"):
            return time.monotonic_ns() // 1000000
        return int(time.monotonic() * 1000)

    def sleep_ms(self, ms):
        time.sleep(ms / 1000)


TIMING = {"idle": 10000, "write_idle": 180000, "reconnect": 40000, "settle": 600,
          # Community (Firmware Hub) route: pause after the kick, per-block
          # pacing, and a pause before looking for the restarted device.
          "kick_wait": 2000, "pace": 10, "restart_wait": 3000,
          "lost_reply": 1000}


class Link:
    def __init__(self, transport, clock):
        self.t = transport
        self.clock = clock

    @property
    def lost(self):
        return self.t.lost

    def send(self, sysex):
        check(not self.t.lost, "USB connection lost")
        self.t.send(sysex)

    def slow_down(self):
        """Ask the transport for gentler sending; False if it can't slow further."""
        f = getattr(self.t, "slow_down", None)
        return bool(f and f())

    def read(self, ms):
        """Next valid (command, data) packet, or None after ms."""
        end = self.clock.now_ms() + ms
        while True:
            msg = self.t.recv(max(0, end - self.clock.now_ms()))
            if msg is not None:
                p = P.parse(msg)
                if p is not None:
                    return p
            if msg is None or self.clock.now_ms() >= end or self.t.lost:
                return None

    def drain(self):
        while self.t.recv(0) is not None:
            pass

    def query(self, command, payload=b"", ms=1500):
        self.drain()
        self.send(P.frame(command, payload))
        end = self.clock.now_ms() + ms
        while self.clock.now_ms() < end:
            p = self.read(min(250, end - self.clock.now_ms()))
            if p is not None and p[0] == command:
                return p[1]
            check(not self.lost, "USB connection lost")
        raise FM1Timeout("device did not respond")

    def close(self):
        self.t.close()


class Updater:
    """status(phase, percent) is called as the install progresses.
    trace(event, *values), if set, sees every read request and stage change."""

    def __init__(self, finder, pkg, meta, status=None, timing=None, clock=None):
        self.finder = finder
        self.pkg = pkg
        self.meta = meta
        self.status = status or (lambda phase, pct: None)
        self.timing = dict(TIMING)
        if timing:
            self.timing.update(timing)
        self.clock = clock or Clock()
        self.link = None
        self.identity = None
        self.mode = None
        self.force = False
        self.family = None
        self.community = meta.get("kind") == "community"
        # Hub timing (kick wait, pacing) whenever a community package or a
        # community firmware's own updater is involved.
        self.hub_timing = self.community
        self.trace = None
        # Times the transport has been slowed after a lost reply; reapplied to
        # every new link so it survives re-enumeration into the loader.
        self.slow_level = 0

    # -- discovery ------------------------------------------------------------

    def _open(self, transport):
        link = Link(transport, self.clock)
        for _ in range(self.slow_level):
            link.slow_down()
        try:
            reply = None
            # Three tries: when the FM-1 stayed enumerated through a soft reload,
            # the host's data toggles restart and the FM-1's don't. The first
            # query is dropped by the FM-1 and the second reply by the host; the
            # third gets through (DEVNOTES 6.9). The stock V15 loader refuses the
            # CLEAR_FEATURE that would avoid this (fm1usb.USBMidiTransport).
            for attempt in range(3):
                try:
                    reply = link.query(P.CMD_IDENTITY, ms=750)
                    break
                except FM1Timeout:
                    if attempt == 2 or link.lost:
                        raise
            return link, P.identity(reply)
        except Exception:
            link.close()
            raise

    def discover(self):
        found = []
        last = None
        for t in self.finder():
            try:
                found.append(self._open(t))
            except FM1Error as e:
                last = e
        if len(found) > 1:
            for link, _ in found:
                link.close()
            raise FM1Error("more than one possible FM-1 found")
        if found:
            return found[0]
        if last is not None and not isinstance(last, FM1Timeout):
            raise last
        return None

    def connect(self, force=False):
        """Probe the device and pick an install mode. Returns a dict with
        identity and one of resume / migration / legacy / tagged."""
        self.disconnect()
        self.force = force
        self.mode = None
        device = self.discover()
        check(device is not None, "no FM-1 answered; power it on and reconnect USB")
        self.link, self.identity = device
        ident = self.identity
        self.hub_timing = self.community or (
            P.community_identity(ident) and ident != P.STOCK_PRODUCT
        )
        try:
            if self.community:
                return self._connect_community(ident, force)
            if ident == self.meta["loader_identity"] or (force and P.is_loader(ident)):
                self.mode = "loader"
                return {"identity": ident, "resume": True}
            if not force and ident != self.meta["product"] and not P.open_identity(ident):
                self.mode = "migration"
                return {"identity": ident, "migration": True}
            # Stock V15 has the request-driven updater but no capability
            # command. Entering this route still requires force.
            if force and ident == P.STOCK_PRODUCT:
                self.mode = "legacy"
                return {"identity": ident, "legacy": True}
            try:
                cap = P.capability(self.link.query(P.CMD_CAPABILITY))
            except FM1Timeout:
                if self.link.lost:
                    raise
                if not force:
                    self.mode = "migration"
                    return {"identity": ident, "migration": True}
                self.mode = "legacy"
                return {"identity": ident, "legacy": True}
            if not force and cap["family"] != self.meta["family"]:
                self.mode = "migration"
                return {"identity": ident, "migration": True}
            check(cap["state"] == 0, "device is busy with another update")
            self.mode = "tagged"
            self.family = cap["family"]
            return {"identity": ident, "tagged": True, "current": cap["build"],
                    "same": cap["build"] == self.meta["build_id"]}
        except Exception:
            self.disconnect()
            raise

    def _connect_community(self, ident, force):
        """The Firmware Hub's rules: resume only into a loader this package
        expects (another firmware's loader may lay out flash differently);
        otherwise any FM-1_<n> firmware may be replaced. Anything else, such
        as stock V15 or FM1 Open, is a migration and needs force."""
        if P.is_loader(ident):
            if P.loader_matches(self.meta, ident):
                self.mode = "loader"
                return {"identity": ident, "resume": True}
            self.disconnect()
            raise FM1Error("the FM-1 is in another firmware's update mode (%s); "
                           "install that firmware again, or power-cycle it" % ident)
        # Stock V15 matches FM-1_<n> too, but leaving stock is a migration.
        if P.community_identity(ident) and ident != P.STOCK_PRODUCT:
            self.mode = "community"
            return {"identity": ident, "community": True, "same": ident == self.meta["product"]}
        if not force:
            self.mode = "migration"
            return {"identity": ident, "migration": True}
        self.mode = "community"
        return {"identity": ident, "community": True, "legacy": True}

    def disconnect(self):
        if self.link is not None:
            self.link.close()
        self.link = None
        self.identity = None

    def wait_for(self, identity, legacy_loader=False):
        """Wait for a device whose identity is `identity` (a string, or a
        predicate taking the identity)."""
        if self.trace:
            self.trace("wait", identity if isinstance(identity, str) else "loader")
        match = identity if callable(identity) else (lambda s: s == identity)
        end = self.clock.now_ms() + self.timing["reconnect"]
        while self.clock.now_ms() < end:
            device = None
            try:
                device = self.discover()
            except FM1Error as e:
                if "more than one" in str(e):
                    raise
            if device is not None:
                link, ident = device
                if self.trace:
                    self.trace("found", ident)
                if match(ident) or (legacy_loader and P.is_loader(ident)):
                    self.link, self.identity = link, ident
                    return
                link.close()
            self.clock.sleep_ms(self.timing["settle"])
        raise FM1Error("timed out waiting for the FM-1 to reconnect")

    # -- transfer -------------------------------------------------------------

    def _expected_blocks(self, finish):
        """256-byte blocks a stage is expected to read: the header and table
        plus the loader (stage 1) or flash entry (stage 2). Without this the
        bar would stall near 86% in stage 2, as the web updater's does."""
        pkg = self.pkg
        if pkg.entries is None:
            return (pkg.image_len + 255) // 256
        e = pkg.loader if finish == P.FINISH_STAGE1 else pkg.flash
        head = 64 + len(pkg.entries) * 80
        return (head + 255) // 256 + (e["size"] + 255) // 256 + 1

    def serve(self, finish, idle, phase):
        """Answer read requests until the finish marker. Progress counts
        256-byte blocks touched (a byte bitmap would need ~90 KB of RAM)."""
        image_len = self.pkg.image_len
        blocks = self._expected_blocks(finish)
        covered = bytearray(((image_len + 255) // 256 + 7) // 8)
        total = 0
        buf = bytearray(512)
        started = last = self.clock.now_ms()
        link = self.link
        pace = self.timing["pace"] if self.hub_timing else 0
        prev = None
        replied_at = 0
        while True:
            now = self.clock.now_ms()
            check(now - started < max(idle * 3, 120000), "update took too long")
            check(now - last < idle, "device stopped requesting data")
            packet = link.read(250)
            if packet is None:
                check(not link.lost, "USB disconnected unexpectedly")
                continue
            cmd, p = packet
            req = P.read_request(p) if cmd == P.CMD_READ else None
            if req is None:
                continue
            _, address, n = req
            if self.trace:
                self.trace("read", address, n)
            # The device repeats a request when our reply didn't arrive (loaders
            # retry after ~3 s). Quick repeats are normal read plans; a slow one
            # means the transport lost the reply, so send more gently from now on.
            if p == prev and self.clock.now_ms() - replied_at >= self.timing["lost_reply"]:
                slowed = link.slow_down()
                if slowed:
                    self.slow_level += 1
                if self.trace:
                    self.trace("resend", address, n, self.slow_level if slowed else None)
            prev = p
            check(0 < n <= 512, "invalid request length")
            if address in (P.FINISH_STAGE1, P.FINISH_STAGE2):
                if self.community and address != finish:
                    # The hub acknowledges the other stage's finish and keeps serving.
                    link.send(P.read_reply(p, P.SUCCESS))
                    continue
                check(address == finish and n == 8, "update stage mismatch")
                link.send(P.read_reply(p, P.SUCCESS))
                # Answer duplicate finish requests before letting go.
                end = self.clock.now_ms() + self.timing["settle"]
                while self.clock.now_ms() < end and not link.lost:
                    again = link.read(min(100, end - self.clock.now_ms()))
                    if again is not None and again[0] == P.CMD_READ:
                        r = P.read_request(again[1])
                        if r is not None and r[1] == finish and r[2] == 8:
                            link.send(P.read_reply(again[1], P.SUCCESS))
                return
            check(address <= image_len and n <= image_len - address, "request outside package")
            last = self.clock.now_ms()
            # Hub pacing is a minimum gap between request and reply; building the
            # reply counts towards it (on CircuitPython that alone takes ~16 ms).
            self.pkg.read_into(address, buf, n)
            reply = P.read_reply(p, memoryview(buf)[:n])
            if pace:
                self.clock.sleep_ms(max(0, pace - (self.clock.now_ms() - last)))
            link.send(reply)
            replied_at = self.clock.now_ms()
            for b in range(address >> 8, ((address + n - 1) >> 8) + 1):
                if not covered[b >> 3] & (1 << (b & 7)):
                    covered[b >> 3] |= 1 << (b & 7)
                    total += 1
            self.status(phase, min(99, total * 100 // blocks))

    def _ack(self, command, payload):
        self.link.drain()
        self.link.send(P.frame(command, payload))
        end = self.clock.now_ms() + self.timing["idle"]
        while self.clock.now_ms() < end:
            r = self.link.read(min(250, end - self.clock.now_ms()))
            check(not self.link.lost, "USB connection lost")
            if r is not None and r[0] == P.CMD_ACK:
                check(r[1] == b"\x00", "device refused the factory voice restore")
                return
        raise FM1Error("factory voice restore did not finish; reconnect stock V15 and retry")

    def restore_factory(self):
        check(self.meta.get("kind") == "stock" and self.identity == P.STOCK_PRODUCT and self.link
              and not self.link.lost, "restoring voices needs stock V15")
        try:
            import gc
            gc.collect()
        except ImportError:
            pass
        factory = self.pkg.factory_bank()
        check(
            P.identity(self.link.query(P.CMD_IDENTITY)) == P.STOCK_PRODUCT,
            "restoring voices needs stock V15",
        )
        phase = "Restoring factory voices"
        self.status(phase, 0)
        for bank in range(0, 16384, 4096):
            self._ack(P.CMD_BANK_BEGIN, P.bank_begin_payload(bank))
            for offset in range(bank, bank + 4096, 512):
                self._ack(
                    P.CMD_BANK_WRITE, P.bank_write_payload(offset, factory[offset : offset + 512])
                )
                self.status(phase, (offset + 512) * 99 // 16384)
        check(
            P.identity(self.link.query(P.CMD_IDENTITY)) == P.STOCK_PRODUCT,
            "restoring voices needs stock V15",
        )

    def _restore_after_boot(self):
        """V15 re-enumerates once a few seconds after its first boot, which drops
        the link early in the restore. Wait for it to come back and start over."""
        try:
            self.restore_factory()
        except (FM1Error, OSError):  # OSError covers usb.core.USBError
            if self.trace:
                self.trace("restore-retry")
            self.disconnect()
            self.clock.sleep_ms(self.timing["restart_wait"])
            self.wait_for(P.STOCK_PRODUCT)
            self.restore_factory()

    def _install_community(self):
        t = self.timing
        if self.mode != "loader":
            self.status("Staging loader", 0)
            self.link.send(P.KICK)
            self.clock.sleep_ms(t["kick_wait"])
            self.serve(P.FINISH_STAGE1, t["idle"], "Staging loader")
            self.disconnect()
            self.status("Restarting", 0)
            self.clock.sleep_ms(t["restart_wait"])
            self.wait_for(lambda s: P.loader_matches(self.meta, s))
        self.status("Writing firmware", 0)
        self.link.send(P.KICK)
        self.clock.sleep_ms(t["kick_wait"])
        self.serve(P.FINISH_STAGE2, t["write_idle"], "Writing firmware")
        self.disconnect()
        self.status("Verifying", 99)
        self.clock.sleep_ms(t["restart_wait"])
        # Community firmwares have no build hash to read back: identity only.
        self.wait_for(self.meta["product"])
        self.status("Done", 100)

    def _identity_again(self):
        """The identity, asked again before anything is written. Three tries:
        once, Aisling (a legacy community firmware) didn't answer the first,
        right after the capability query it doesn't support had timed out
        (4 November 2026)."""
        for attempt in range(3):
            try:
                return P.identity(self.link.query(P.CMD_IDENTITY))
            except FM1Timeout:
                if attempt == 2 or self.link.lost:
                    raise
        return None  # not reached: the last try returns or raises

    def install(self, force=False):
        check(self.link is not None, "connect first")
        try:
            check(not self.force or force, "forced install not confirmed")
            check(self.mode, "reconnect the device")
            check(self.mode != "migration", "confirm the migration and reconnect with force")
            original = self.identity
            check(self._identity_again() == original, "device identity changed; reconnect")
            stock = self.meta.get("kind") == "stock"
            if stock and original == P.STOCK_PRODUCT:
                self.restore_factory()
                self.status("Done", 100)
                return
            if self.community:
                self._install_community()
                return
            if self.mode != "loader":
                if self.mode == "tagged":
                    cap = P.capability(self.link.query(P.CMD_CAPABILITY))
                    check(
                        cap["family"] == self.family and cap["state"] == 0,
                        "device state changed; reconnect",
                    )
                    check(cap["build"] != self.meta["build_id"], "device already runs this build")
                    ack = self.link.query(
                        P.CMD_ARM,
                        P.arm_payload(cap["family"], self.pkg.image_len, self.meta["build_id"]),
                    )
                    check(ack == b"\x00", "device refused this package")
                self.status("Staging loader", 0)
                self.link.send(P.KICK)
                if self.hub_timing:
                    self.clock.sleep_ms(self.timing["kick_wait"])
                self.serve(P.FINISH_STAGE1, self.timing["idle"], "Staging loader")
                self.disconnect()
                self.status("Restarting", 0)
                self.wait_for(self.meta["loader_identity"], self.mode == "legacy" or stock)
            self.status("Writing firmware", 0)
            self.link.send(P.KICK)
            self.serve(P.FINISH_STAGE2, self.timing["write_idle"], "Writing firmware")
            self.disconnect()
            self.status("Verifying", 99)
            self.wait_for(self.meta["product"])
            if stock:
                check(P.identity(self.link.query(P.CMD_IDENTITY)) == self.meta["product"],
                      "restarted, but the firmware identity does not match")
                self._restore_after_boot()
            else:
                after = P.capability(self.link.query(P.CMD_CAPABILITY))
                check(
                    after["family"] == self.meta["family"]
                    and after["build"] == self.meta["build_id"]
                    and after["state"] == 0,
                    "restarted, but the firmware build does not match",
                )
            self.status("Done", 100)
        finally:
            self.disconnect()
