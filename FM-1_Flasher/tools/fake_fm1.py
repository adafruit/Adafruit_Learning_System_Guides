# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""A simulated FM-1 for exercising fm1update.Updater without hardware.

It plays the device side of the request-driven update protocol on a fake
clock: identity/capability replies, the kick, read requests, finish markers,
re-enumeration into the loader and back, and factory bank writes. Every byte
served is checked against the package.
"""

import fm1proto as P


class FakeClock:
    def __init__(self):
        self.t = 0

    def now_ms(self):
        return self.t

    def sleep_ms(self, ms):
        self.t += int(ms)


class FakeFM1:
    def __init__(self, pkg, clock, identity="FM1_OFFICIAL_OPEN", build="00" * 32, capability=True,
                 loader_identity="ota-FM-1_015", new_identity=None, new_build=None,
                 reenum_ms=3000, duplicate_finish=1, noise=False, chunk=512,
                 lossy_over=None, lossy_modes=("app", "loader"), retry_ms=3000, retries=2,
                 reenum_after_boot=None):
        self.pkg = pkg
        self.clock = clock
        self.identity = identity
        self.build = build
        self.has_cap = capability
        self.loader_identity = loader_identity
        self.new_identity = new_identity or pkg.product
        self.new_build = new_build
        self.reenum_ms = reenum_ms
        self.duplicate_finish = duplicate_finish
        self.noise = noise
        self.chunk = chunk
        # Lossy link: host messages longer than lossy_over bytes are dropped until
        # the transport has slowed down (as the MAX3421E lost bursts to SLOOP's
        # loader). A request left unanswered is repeated every retry_ms, up to
        # `retries` times; after that the device goes silent.
        self.lossy_over = lossy_over
        self.lossy_modes = lossy_modes
        self.retry_ms = retry_ms
        self.retries = retries
        self.retries_left = retries
        # Stock V15 re-enumerates once shortly after its first boot: the device
        # drops off the bus on this many-th message after booting the new app.
        self.reenum_after_boot = reenum_after_boot
        self.boot_messages = None
        self.ignore_identity = 0  # identity queries to leave unanswered (Aisling once didn't answer one)
        self.last_req_at = 0
        self.mode = "app"
        self.generation = 0
        self.available_at = 0
        self.armed = None
        self.requests = []
        self.seq = 0
        self.served = 0
        self.bank_writes = []
        self.log = []
        self.pending_reset = None

    # -- device lifecycle --------------------------------------------------

    def present(self):
        return self.clock.now_ms() >= self.available_at

    def reset(self, mode):
        self.generation += 1
        self.mode = mode
        self.available_at = self.clock.now_ms() + self.reenum_ms
        self.requests = []
        self.log.append(("reset", mode))
        if mode == "app":
            self.boot_messages = 0 if self.reenum_after_boot else None
            self.identity = self.new_identity
            self.build = self.new_build
            self.has_cap = self.new_build is not None

    def current_identity(self):
        return self.loader_identity if self.mode == "loader" else self.identity

    # -- transfer plans ----------------------------------------------------

    def _plan(self, finish):
        """Read requests for a stage."""
        if self.pkg.entries is None:
            self.pkg.inspect(verify=False, strict=False)
        # As logged from SLOOP 2.8's updater and loader (2026-10-22): stage 1
        # reads the header, one app block, and the loader; stage 2 reads
        # everything from 0 to the end of the flash entry.
        f, ld = self.pkg.flash, self.pkg.loader
        if finish == P.FINISH_STAGE1:
            spans = [(0, 0x600), (f["offset"] + 0x4000, 0x200), (ld["offset"], ld["size"])]
        else:
            spans = [(0, f["offset"] + f["size"])]
        reqs = []
        for start, size in spans:
            for a in range(start, start + size, self.chunk):
                reqs.append((a, min(self.chunk, start + size - a)))
        reqs.append((finish, 8))
        return reqs

    def _next_request(self, out):
        if not self.requests:
            return
        a, n = self.requests[0]
        self.seq = (self.seq + 1) & 0xFF
        p = bytes((self.seq,)) + a.to_bytes(4, "little") + n.to_bytes(3, "little")
        self.current = p
        self.last_req_at = self.clock.now_ms()
        self.retries_left = self.retries
        out.append(bytes(P.frame(P.CMD_READ, p)))

    # -- host -> device ----------------------------------------------------

    def receive(self, msg, out):
        if bytes(msg) == P.KICK:
            if self.mode == "app" and self.has_cap and self.armed is None:
                self.log.append(("kick-ignored-unarmed",))
                return
            finish = P.FINISH_STAGE2 if self.mode == "loader" else P.FINISH_STAGE1
            self.requests = self._plan(finish)
            self.log.append(("kick", self.mode))
            self._next_request(out)
            return
        if self.boot_messages is not None:
            self.boot_messages += 1
            if self.boot_messages == self.reenum_after_boot:
                self.boot_messages = None
                self.generation += 1
                self.available_at = self.clock.now_ms() + self.reenum_ms
                self.log.append(("reenumerate",))
                return
        p = P.parse(msg)
        if p is None:
            # The host sends frames in our reply format too; decode leniently.
            self.log.append(("garbage", bytes(msg[:8])))
            return
        cmd, data = p
        if self.noise:
            out.append(bytes(P.frame(99, b"noise")))
        if cmd == P.CMD_IDENTITY and self.ignore_identity:
            self.ignore_identity -= 1
        elif cmd == P.CMD_IDENTITY:
            out.append(bytes(P.frame(cmd, self.current_identity().encode().ljust(27, b"\0"))))
        elif cmd == P.CMD_CAPABILITY:
            if self.has_cap and self.mode == "app":
                d = bytearray(47)
                d[0:4] = b"FMC1"
                d[4], d[5], d[6], d[7] = 1, P.FAMILY, 0, 1
                d[8:10] = (512).to_bytes(2, "little")
                d[10:14] = (1048576).to_bytes(4, "little")
                d[14:46] = bytes.fromhex(self.build)
                out.append(bytes(P.frame(cmd, d)))
        elif cmd == P.CMD_ARM:
            self.armed = bytes(data)
            out.append(bytes(P.frame(cmd, b"\x00")))
        elif cmd in (P.CMD_BANK_BEGIN, P.CMD_BANK_WRITE):
            self.bank_writes.append((cmd, bytes(data)))
            out.append(bytes(P.frame(P.CMD_ACK, b"\x00")))
        elif cmd == P.CMD_READ and self.requests:
            a, n = self.requests[0]
            assert bytes(data[0:8]) == self.current, "reply header does not echo the request"
            body = bytes(data[8:])
            if a in (P.FINISH_STAGE1, P.FINISH_STAGE2):
                assert body == P.SUCCESS
                if self.duplicate_finish > 0:
                    self.duplicate_finish -= 1
                    out.append(bytes(P.frame(P.CMD_READ, self.current)))
                    return
                self.requests = []
                self.pending_reset = "loader" if a == P.FINISH_STAGE1 else "app"
                return
            assert body == self.pkg.read(a, n), "served bytes differ at 0x%x" % a
            self.served += n
            self.requests.pop(0)
            self._next_request(out)


class FakeTransport:
    def __init__(self, dev):
        self.dev = dev
        self.generation = dev.generation
        self.inbox = []
        self.closed = False
        self.slow_level = 0

    def slow_down(self):
        if self.slow_level >= 3:
            return False
        self.slow_level += 1
        return True

    @property
    def lost(self):
        return self.closed or self.dev.generation != self.generation

    def send(self, msg):
        assert not self.lost, "send on a lost transport"
        dev = self.dev
        if (dev.lossy_over and len(msg) > dev.lossy_over and dev.mode in dev.lossy_modes
                and not self.slow_level):
            dev.log.append(("lost", len(msg)))
            return
        dev.receive(msg, self.inbox)

    def recv(self, timeout_ms):
        if self.inbox and not self.lost:
            return self.inbox.pop(0)
        dev = self.dev
        if dev.requests and not self.lost and dev.retries_left > 0 and not dev.pending_reset:
            due = dev.last_req_at + dev.retry_ms
            if due <= dev.clock.now_ms() + timeout_ms:
                dev.clock.sleep_ms(max(0, due - dev.clock.now_ms()))
                dev.retries_left -= 1
                dev.last_req_at = dev.clock.now_ms()
                dev.log.append(("repeat", dev.requests[0][0]))
                return bytes(P.frame(P.CMD_READ, dev.current))
        # The device resets once the host has stopped answering the finish.
        if self.dev.pending_reset and not self.lost:
            self.dev.clock.sleep_ms(timeout_ms)
            mode, self.dev.pending_reset = self.dev.pending_reset, None
            self.dev.reset(mode)
            return None
        self.dev.clock.sleep_ms(timeout_ms)
        return None

    def close(self):
        self.closed = True


def finder_for(dev):
    def finder():
        return [FakeTransport(dev)] if dev.present() else []
    return finder
