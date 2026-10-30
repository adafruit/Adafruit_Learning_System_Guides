# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""APRS receiver on the Fruit Jam or the Metro ESP32-P4 (NESDR SMArt v5):
decodes APRS packets on 144.390 MHz (other presets: serial n / p, or
buttons B1 / B3 on the Fruit Jam), shows them on the screen (the Fruit
Jam's DVI output via picodvi, or the 2.8" TFT shield on the Metro
ESP32-P4; on an OpenStreetMap map, tiles cached in /sd/tiles/osm/) and
logs them to /sd/aprs/aprs.txt. Wi-Fi in settings.toml gives the log UTC
times. To start elsewhere: run(preset=1) (the ISS) or
run(frequency=144800000) from aprs_receiver. With REPLAY_START set it
plays that log back onto the screen instead (no radio).
"""
import time
import supervisor

# The native modules and the DSP's buffers first, into internal SRAM (the
# DSP runs twice as fast there).
# pylint: disable=wrong-import-position, unused-import
import aprs_buffers

# aprs_receiver.py is compiled when imported, before its first lines (the
# audio ring, which moves the heap to PSRAM) run, and compiling it grows
# the heap in internal SRAM: then the jack's audio buffers do not fit. A
# 1 MB block first puts the heap in PSRAM.
_ballast = bytearray(1024 * 1024)
from aprs_receiver import run, replay

del _ballast

# aprs_receiver.PRESETS: 0 is 144.390 MHz (North America), 1 the ISS
PRESET = 0
# (lat, lon): show distance and direction to each station, centre the map there
HOME = None
UI = 'map'
# (lat, lon) to centre the map on without HOME; None: the first position heard
MAP_CENTRE = None
# 3 (a continent) .. 15 (streets); 9 is ~75 km across the screen
MAP_ZOOM = 9
# replay /sd/aprs/aprs.txt from here instead of listening: a UTC time as in
# the log ('19:36', '2026-10-24 19:36:30') or a line number (1: the first)
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
        run(preset=PRESET, home=HOME, display=UI, map_centre=MAP_CENTRE, map_zoom=MAP_ZOOM)
    except Exception as error:  # pylint: disable=broad-except
        print('RADIO_ERROR', type(error).__name__, str(error))
        time.sleep(3)
