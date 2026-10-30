# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""FT8 receiver on the Fruit Jam or the Metro ESP32-P4 (NESDR SMArt v5):
decodes FT8 on 10 m (other bands: serial . / , or 1-9, or buttons B1 / B3
on the Fruit Jam) every 15 s slot, shows the decodes on the screen (the
Fruit Jam's DVI output via picodvi, or the 2.8" TFT shield on the Metro
ESP32-P4) and logs them to /sd/ft8/ALL.TXT. Needs Wi-Fi in settings.toml
for the time. To start elsewhere: run(preset=1) or run(frequency=7074000) from
ft8_receiver. DISPLAY = 'color' shows the decodes with callsigns in colors
(needs adafruit_color_terminal in lib/); DISPLAY = 'map' the exchanges of
the last few minutes on a map (needs adafruit_maptiles in lib/). With
REPLAY_START set it first plays /sd/ft8/ALL.TXT back onto the screen
(no radio) and keeps that screen up.
"""
import time
import supervisor

# ft8_receiver.py is compiled when imported, before its first lines (the
# big buffers, which move the heap to PSRAM) run, and compiling it grows
# the heap in internal SRAM: then the jack's audio buffers do not fit. A
# 1 MB block first puts the heap in PSRAM.
_ballast = bytearray(1024 * 1024)
# pylint: disable=wrong-import-position
from ft8_receiver import run, replay_log

del _ballast

# 'dvi' (plain text, on either screen), 'color' (callsigns in colors), 'map'
# (exchanges on a map), or several: ('color', 'map'), the m or l key shows the next
DISPLAY = ('color', 'map')
# the map: your grid ('EM28'), a cross and the map's centre; None: centred
# on the first station heard with a grid
MAP_HOME = None
# 1 (the world) .. 10; 3 is ~4800 km across the screen
MAP_ZOOM = 3
# replay /sd/ft8/ALL.TXT from here instead of listening: a UTC time
# ('12:56', '12:56:30'), a slot stamp ('261020_1256') or a line number
REPLAY_START = None
# stop there (the same forms); None: the end of the log
REPLAY_END = None
# times real time
REPLAY_SPEED = 1
# (only the map uses them)
OPTIONS = {'home': MAP_HOME, 'zoom': MAP_ZOOM}

supervisor.runtime.autoreload = False
if REPLAY_START is not None:
    # the last screen stays up (and the keys work) when the replay ends
    replay_log(start=REPLAY_START, end=REPLAY_END, speed=REPLAY_SPEED, display=DISPLAY,
               display_options=OPTIONS, hold=True)
while True:
    try:
        run(display=DISPLAY, display_options=OPTIONS)
    except Exception as error:  # pylint: disable=broad-except
        print('RADIO_ERROR', type(error).__name__, str(error))
        time.sleep(3)
