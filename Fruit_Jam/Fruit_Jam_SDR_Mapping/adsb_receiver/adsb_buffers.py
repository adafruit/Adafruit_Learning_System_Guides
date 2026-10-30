# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The decoder's buffers and its native module, loaded before anything else
(code.py imports this first), so that they are in internal SRAM."""
# _adsb.armv7emsp.mpy is the Arm build (Fruit Jam), _adsb.rv32imc.mpy the
# RISC-V one (Metro ESP32-P4): `import _adsb` loads the one for this board.
import _adsb
import board

try:
    import usb_host_bulk
except ImportError:
    usb_host_bulk = None
# (as adsb_radio.AdsbRadio.streaming: USB_HOST_DP is the Metro ESP32-P4's high-speed port)
if usb_host_bulk is None or hasattr(board, 'USB_HOST_DP'):
    SNAPSHOT = 36864         # adsb_radio.STREAM_CHUNK: the stream on a high-speed host
else:
    SNAPSHOT = 3760          # adsb_radio.SNAPSHOT: the RTL2832U's FIFO, 20 x 188 bytes
MAX_RECORDS = 32
state = bytearray(_adsb.STATE_BYTES)
records = bytearray(_adsb.RECORD * MAX_RECORDS)
# Two: one is decoded while the next one comes in.
snapshots = (bytearray(SNAPSHOT), bytearray(SNAPSHOT))
