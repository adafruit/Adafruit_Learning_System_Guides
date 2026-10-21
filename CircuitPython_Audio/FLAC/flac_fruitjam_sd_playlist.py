# SPDX-FileCopyrightText: Copyright (c) 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Play every FLAC file on the Fruit Jam's microSD card, in alphabetical order.

CircuitPython mounts the card at /sd on the Fruit Jam. For files up to 48 kHz; see
flac_fruitjam_sd_hires.py for 88.2/96 kHz.
"""

import os
from adafruit_fruitjam.peripherals import Peripherals
import adafruit_flac

fruit_jam = Peripherals(audio_output="headphone")
fruit_jam.volume = 0.5

flac_files = sorted(
    "/sd/" + name
    for name in os.listdir("/sd")
    if name.lower().endswith(".flac") and not name.startswith(".")
)

# Make one decoder and reuse it for every file; this avoids running out of memory.
decoder = adafruit_flac.FLACDecoder(flac_files[0])
player = adafruit_flac.FLACPlayer(fruit_jam.audio)

while True:
    for filename in flac_files:
        decoder.open(filename)
        fruit_jam.dac.configure_clocks(sample_rate=decoder.sample_rate, bit_depth=16)
        print("Playing", filename)
        player.play(decoder)
        while player.playing:
            player.update()  # your code can run here too, between updates
