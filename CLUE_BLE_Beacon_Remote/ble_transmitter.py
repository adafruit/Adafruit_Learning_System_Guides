# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''MagicBand+ BLE transmitter for the Adafruit CLUE.

Wraps _bleio.adapter to broadcast raw advertisement packets with Disney's
0x0183 manufacturer company identifier. Works directly with the BLE stack
on the nRF52840 without going through adafruit_ble's Advertisement classes.
'''
# Target: Adafruit CLUE (nRF52840) - the BLE remote
import time
import _bleio

from magicband_protocol import DISNEY_CID

# BLE advertising interval in seconds. CircuitPython requires this to be
# in the range 0.02-10.24. We use 0.025 instead of 0.02 because float
# precision can cause 0.02 to internally evaluate as slightly less than
# the minimum, raising "interval must be in range" ValueError.
_AD_INTERVAL = 0.025

# Default broadcast duration. MagicBands latch a command within the first
# ~second, but the timing byte in the payload controls the actual fade so
# we can stop advertising well before the animation finishes.
_BROADCAST_SECONDS = 3.0


def _build_advertisement(payload):
    '''Assemble a 31-byte BLE advertisement packet with Disney manufacturer data.'''
    cid_lo = DISNEY_CID & 0xFF
    cid_hi = (DISNEY_CID >> 8) & 0xFF
    mfr_field_len = 3 + len(payload)
    return bytes((
        0x02, 0x01, 0x06,                      # Flags AD: LE General Discoverable
        mfr_field_len, 0xFF, cid_lo, cid_hi,   # Manufacturer data header
    )) + payload


def broadcast(payload, duration=_BROADCAST_SECONDS):
    '''Advertise a MagicBand+ manufacturer-data payload for duration seconds.'''
    packet = _build_advertisement(payload)
    adapter = _bleio.adapter
    if not adapter.enabled:
        adapter.enabled = True
    if adapter.advertising:
        adapter.stop_advertising()
    adapter.start_advertising(packet, connectable=False, interval=_AD_INTERVAL)
    time.sleep(duration)
    adapter.stop_advertising()
