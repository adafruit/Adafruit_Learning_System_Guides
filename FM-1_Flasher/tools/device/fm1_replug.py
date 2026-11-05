# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Replug test: report each FM-1 attach and detach, and probe identity on each attach.
Run with `exec(open('fm1_replug.py').read())` from the REPL. Writes nothing to the FM-1."""
import time

import usb.core

import fm1proto as P
import fm1update as U
import fm1usb

DURATION = 180
FM1_VIDS = (0x4C4A, 0x1209)  # stock V15 (JieLi); Felucca-family apps and loaders


def fm1_present():
    for d in usb.core.find(find_all=True):
        if d.idVendor in FM1_VIDS:
            return True
    return False


def probe():
    # The first transport open right after attach can fail once; retry briefly.
    for _ in range(3):
        try:
            found = fm1usb.finder()()
            if found:
                return P.identity(U.Link(found[0], U.Clock()).query(P.CMD_IDENTITY, ms=750))
        except P.FM1Error as e:
            last = e
        time.sleep(0.2)
    return "no identity"
t0 = time.monotonic()
present = False
attaches = ok = 0
print("replug test (%d s)" % DURATION)
while time.monotonic() - t0 < DURATION:
    found = fm1_present()
    now = "%5.1f s" % (time.monotonic() - t0)
    if found and not present:
        attaches += 1
        ident = probe()
        if ident != "no identity":
            ok += 1
        print(now, "attach", attaches, "identity:", ident)
    elif present and not found:
        print(now, "detach")
    present = found
    time.sleep(0.5)
print("replug done: %d attaches, %d identities" % (attaches, ok))
