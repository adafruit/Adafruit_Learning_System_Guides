# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""ADS-B receiver on the Fruit Jam or the Metro ESP32-P4 (NESDR SMArt v5):
decodes the aircraft transponders on 1090 MHz, shows the aircraft on the
screen (the Fruit Jam's DVI output via picodvi, or the 2.8" TFT shield on
the Metro ESP32-P4) and logs every message to /sd/adsb/adsb.txt. Wi-Fi in
settings.toml gives the log UTC times.
With REPLAY_START set it plays that log back onto the screen instead (no
radio): e.g. record with the antenna outside, then replay indoors.
"""
import time
import supervisor

# The native module and the decoder's buffers first, into internal SRAM.
# pylint: disable=wrong-import-position, unused-import
import adsb_buffers

# Compiling adsb_receiver.py grows the heap; a 1 MB block first puts the
# heap in PSRAM, leaving internal SRAM for the USB ring.
_ballast = bytearray(1024 * 1024)
from adsb_receiver import run, replay

del _ballast

# (lat, lon) of the antenna: distances and directions, the map's centre
HOME = None
# tuner gain in tenths of a dB (0 .. 496), None: the tuner's AGC
GAIN = None
# 'map' (aircraft on an OpenStreetMap map), 'table' (a line per aircraft) or False
UI = 'map'
# (lat, lon) to centre the map on without HOME; None: the first position heard
MAP_CENTRE = None
# 3 (a continent) .. 13; 8 is ~150 km across the screen
MAP_ZOOM = 8
# replay the log from here instead of listening: a UTC time as in the log
# ('19:36', '2026-10-21 19:36:30') or a line number (1: the first)
REPLAY_START = None
# stop there (the same forms); None: the end of the log
REPLAY_END = None
# times real time
REPLAY_SPEED = 1

supervisor.runtime.autoreload = False
if REPLAY_START is not None:
    # the last screen stays up (and the keys work) when the replay ends
    replay(start=REPLAY_START, end=REPLAY_END, speed=REPLAY_SPEED, home=HOME, display=UI,
           map_centre=MAP_CENTRE, map_zoom=MAP_ZOOM, hold=True)
while True:
    try:
        run(home=HOME, gain=GAIN, display=UI, map_centre=MAP_CENTRE, map_zoom=MAP_ZOOM)
    except Exception as error:  # pylint: disable=broad-except
        print('RADIO_ERROR', type(error).__name__, str(error))
        time.sleep(3)
