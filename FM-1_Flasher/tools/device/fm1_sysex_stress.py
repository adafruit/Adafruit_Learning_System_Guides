# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""SysEx stress test over the USB host port. Writes nothing to the FM-1's flash.

A: repeated identity queries (FM-1 to host replies).
B: long host-to-FM-1 SysEx at install sizes and beyond, sent as manufacturer 0x7D
   (non-commercial) so stock firmware ignores them; identity is checked after each batch.
C: an install-like stream: 305-byte messages with 10 ms pacing.
Run with `exec(open('fm1_sysex_stress.py').read())` from the REPL."""
import time

import fm1proto as P
import fm1update as U
import fm1usb


def ms_since(t):
    return (time.monotonic_ns() - t) / 1e6


def junk(size, seed):
    # F0 7D 'T' ... F7, 7-bit pattern bytes; total length = size.
    msg = bytearray(size)
    msg[0], msg[1], msg[2] = 0xF0, 0x7D, 0x54
    for i in range(3, size - 1):
        msg[i] = (i * 7 + seed) & 0x7F
    msg[-1] = 0xF7
    return msg


def ident_ok(link):
    try:
        return P.identity(link.query(P.CMD_IDENTITY, ms=750)) == "FM-1_015"
    except P.FM1Error:
        return False


found = fm1usb.finder()()
if not found:
    print("no FM-1 on the host port")
else:
    t = found[0]
    link = U.Link(t, U.Clock())

    print("A: 200 identity queries")
    ok = 0
    lat = []
    for i in range(200):
        t0 = time.monotonic_ns()
        if ident_ok(link):
            ok += 1
            lat.append(ms_since(t0))
    print("  %d/200 ok, latency min %.1f avg %.1f max %.1f ms" % (
        ok, min(lat), sum(lat) / len(lat), max(lat)) if lat else "  0/200 ok")

    print("B: long SysEx batches (50 each), identity after each batch")
    for size in (305, 603, 1024, 4096):
        t0 = time.monotonic_ns()
        sent = 0
        try:
            for i in range(50):
                t.send(junk(size, i))
                sent += 1
        except Exception as e:
            print("  %5d B: send failed after %d: %r" % (size, sent, e))
        ms = ms_since(t0)
        print("  %5d B x %d: %.0f ms, %.1f KB/s, identity %s" % (
            size, sent, ms, sent * size / ms, "ok" if ident_ok(link) else "FAILED"))

    print("C: install-like stream, 400 x 305 B with 10 ms pacing")
    t0 = time.monotonic_ns()
    fails = 0
    for i in range(400):
        t.send(junk(305, i))
        time.sleep(0.01)
        if i % 100 == 99 and not ident_ok(link):
            fails += 1
    ms = ms_since(t0)
    print("  %.0f ms (%.1f ms per message), identity checks failed: %d/4, lost: %s" % (
        ms, ms / 400, fails, t.lost))
    print("final identity:", "ok" if ident_ok(link) else "FAILED")
print("stress done")
