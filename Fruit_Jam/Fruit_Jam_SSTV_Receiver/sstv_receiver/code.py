# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""HF and ISS SSTV receiver on Fruit Jam (NESDR SMArt v5); pictures go to
/sd/hf_sstv/. They are shown on a 128x64 SH1107 OLED if one is on the
STEMMA QT port (I2C 0x3C), otherwise on HDMI.

For an ISS SSTV event, start
on its preset: run(preset=7) for 145.800 MHz, run(preset=8) for 437.550.
"""
import time
import supervisor

# hf_sstv_iss.py is compiled when imported, before its first line (the ring
# buffer, which moves the heap to PSRAM) runs, and compiling it grows the
# heap in internal SRAM: then the jack's audio buffers do not fit. A 1 MB
# block first puts the heap in PSRAM.
# pylint: disable=wrong-import-position
_ballast = bytearray(1024 * 1024)
from hf_sstv_iss import run

del _ballast

supervisor.runtime.autoreload = False
while True:
    try:
        run()
    except Exception as error:  # pylint: disable=broad-except
        print("RADIO_ERROR", type(error).__name__, str(error))
        time.sleep(3)
