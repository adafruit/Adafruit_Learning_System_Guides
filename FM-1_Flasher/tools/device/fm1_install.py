# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Install a firmware folder (meta.json + .fwsc) on the FM-1 from the device.

From the REPL, with the USB host already started (e.g. metro_install.py):
    import fm1_install
    fm1_install.run("/firmware/sloop")            # dry run: identity/capability only
    fm1_install.run("/firmware/sloop", go=True)   # writes the FM-1

Sends go out as separate 64-byte USB writes with no extra gap (chunk=64,
gap_ms=0): the FM-1's loaders and the SLOOP app lose replies sent as one long
burst through the MAX3421E. If the FM-1 still re-asks for a block it already
got (a lost reply), the transport slows down further for the rest of the
install. chunk=None sends each reply in one write.
"""
import json
import time

import fm1proto as P
import fm1update as U
import fm1usb


def run(folder, go=False, force=True, debug=True, chunk=64, gap_ms=0):
    t0 = time.monotonic()
    ring = []  # (t, dir, len, head bytes) of recent USB-MIDI SysEx, printed after a failure

    def log(direction, msg):
        ring.append(("%.3f" % (time.monotonic() - t0), direction, len(msg), bytes(msg[:12]).hex()))
        if len(ring) > 80:
            ring.pop(0)

    def stamp():
        return "%6.1f s" % (time.monotonic() - t0)

    meta = json.load(open(folder + "/meta.json"))
    f = open(folder + "/" + meta["file"], "rb")
    print(stamp(), "verifying package ...")
    pkg, meta = P.prepare(meta, f, verify=True)
    print(stamp(), "package: %s %s (%s), %d bytes, %s route, loader %s" % (
        meta.get("name", meta["product"]), meta.get("version", ""), meta["product"],
        meta["bytes"], meta.get("kind"), meta["loader_identity"]))

    state = {"phase": None, "pct": -10, "reads": 0}

    def trace(event, *values):
        if event == "read":
            state["reads"] += 1
        elif event == "found":
            print(stamp(), "found:", values[0])
        elif event == "wait":
            print(stamp(), "waiting:", values)
        elif event == "resend":
            print(stamp(), "lost reply at 0x%x (%d bytes): resending, slow level %s" % values)

    def status(phase, pct):
        if phase != state["phase"]:
            state["phase"] = phase
            state["pct"] = -10
            print(stamp(), phase, "...")
        if pct >= state["pct"] + 10 or pct == 100:
            state["pct"] = pct
            print(stamp(), "  %3d%%  (%d reads)" % (pct, state["reads"]))

    up = U.Updater(fm1usb.finder(log if debug else None, chunk, gap_ms), pkg, meta, status=status)
    up.trace = trace
    info = up.connect(force=force)
    print(stamp(), "device: %s, mode: %s" % (info["identity"], up.mode), info)
    if not go:
        up.disconnect()
        print(stamp(), "dry run: nothing was written")
        return info
    print(stamp(), "INSTALLING %s: keep the FM-1 on and connected" % meta["product"])
    try:
        up.install(force=force)
    except Exception as e:  # FM1Error, or a USBError the transport gave up on
        print(stamp(), "FAILED:", repr(e), "after", state["reads"], "reads")
        for entry in ring:
            print(*entry)
        raise
    print(stamp(), "done:", state["reads"], "reads")
    return info
