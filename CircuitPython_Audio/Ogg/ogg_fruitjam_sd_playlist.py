# SPDX-FileCopyrightText: Copyright (c) 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Play every Ogg Vorbis file on the Fruit Jam's microSD card, in alphabetical order.

CircuitPython mounts the card at /sd on the Fruit Jam.
"""

import os
import adafruit_ogg

ogg_files = sorted(
    "/sd/" + name
    for name in os.listdir("/sd")
    if name.lower().endswith(".ogg") and not name.startswith(".")
)

# Make the decoder before Peripherals: it decodes several times faster with its buffers in
# internal RAM, which Peripherals would otherwise fill. Reuse it for every file.
decoder = adafruit_ogg.OggDecoder(ogg_files[0])

from adafruit_fruitjam.peripherals import Peripherals  # noqa: E402

fruit_jam = Peripherals(audio_output="headphone")
fruit_jam.volume = 0.5
player = adafruit_ogg.OggPlayer(fruit_jam.audio)

while True:
    for filename in ogg_files:
        decoder.open(filename)
        fruit_jam.dac.configure_clocks(sample_rate=decoder.sample_rate, bit_depth=16)
        print("Playing", filename, decoder.comments.get("TITLE", ""))
        player.play(decoder)
        while player.playing:
            player.update()  # your code can run here too, between updates
