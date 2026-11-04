# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""v2 spike 2, raw: what the FM-1's MIDI endpoints do on the Metro ESP32-P4.
Sends the identity query (read-only) and prints every write result and
each raw read (3 s timeout, timed), three times. Copy to CIRCUITPY as code.py.
"""
import time

import board
import digitalio
import usb.core
import usb_host

import fm1proto as P
import fm1usb

# A clean start: wait for the FM-1 to be unplugged, then plugged back in.
power = digitalio.DigitalInOut(board.USB_HOST_POWER)
power.switch_to_output(value=True)
port = usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM)
time.sleep(1)
if usb.core.find() is not None:
    print("UNPLUG the FM-1's USB cable now")
    while usb.core.find() is not None:
        time.sleep(0.1)
print("PLUG the FM-1 back in")
while usb.core.find() is None:
    time.sleep(0.05)
print("plugged in")

dev = None
t0 = time.monotonic()
while dev is None and time.monotonic() - t0 < 10:
    dev = usb.core.find()
    time.sleep(0.1)
print("device:", dev and "%04x:%04x speed=%s" % (dev.idVendor, dev.idProduct, getattr(dev, "speed", "?")))
iface, ep_in, ep_out, size = fm1usb.midi_endpoints(dev)
print("midi iface %d in 0x%02x out 0x%02x size %d" % (iface, ep_in, ep_out, size))
dev.set_configuration()
try:
    dev.detach_kernel_driver(iface)
except Exception as e:
    print("detach:", repr(e))

query = fm1usb.encode_sysex(P.frame(P.CMD_IDENTITY))
READ_MS = 3000
WAIT = 0  # after each write, before reading: is a reply that's already there read at once?
buf = bytearray(64)
for round_ in range(5):
    try:
        n = dev.write(ep_out, query, 1000)
        print("round %d: write %d of %d bytes" % (round_, n, len(query)))
    except Exception as e:
        print("round %d: write error %r" % (round_, e))
    time.sleep(WAIT)
    for _ in range(3):
        t = time.monotonic()
        try:
            n = dev.read(ep_in, buf, READ_MS)
            print("  read %d after %.3f s: %s" % (n, time.monotonic() - t, bytes(buf[:n])))
        except usb.core.USBTimeoutError:
            print("  read timeout after %.3f s" % (time.monotonic() - t))
            break
        except Exception as e:
            print("  read error %r after %.3f s" % (e, time.monotonic() - t))
            break
print("raw done")
