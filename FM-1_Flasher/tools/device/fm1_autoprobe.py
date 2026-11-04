# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Wait for an FM-1 on the USB host port, then probe it (cmd 17 and cmd 49).
Run with `import fm1_autoprobe` from the REPL. Writes nothing to the FM-1."""
import time

import usb.core

import fm1proto as P
import fm1update as U
import fm1usb

t0 = time.monotonic()
print("waiting for a USB MIDI device (120 s)")
found = []
while time.monotonic() - t0 < 120 and not found:
    found = fm1usb.finder()()
    if not found:
        time.sleep(0.5)
for d in usb.core.find(find_all=True):
    print("device %04x:%04x" % (d.idVendor, d.idProduct), "midi", fm1usb.midi_endpoints(d))
for t in found:
    link = U.Link(t, U.Clock())
    try:
        start = time.monotonic()
        print("identity:", P.identity(link.query(P.CMD_IDENTITY, ms=750)),
              "(%.0f ms)" % ((time.monotonic() - start) * 1000))
        try:
            print("capability:", P.capability(link.query(P.CMD_CAPABILITY)))
        except U.FM1Timeout:
            print("capability: no reply")
    except P.FM1Error as e:
        print("error:", repr(e))
print("autoprobe done")
