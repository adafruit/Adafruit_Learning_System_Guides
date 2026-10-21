# SPDX-FileCopyrightText: Copyright (c) 2026 Mikey Sklar for Adafruit Industries
# SPDX-License-Identifier: MIT
"""Play a FLAC file once through the Fruit Jam headphone jack."""

from adafruit_fruitjam.peripherals import Peripherals

import adafruit_flac

decoder = adafruit_flac.FLACDecoder("song.flac")

fruit_jam = Peripherals(audio_output="headphone", sample_rate=decoder.sample_rate)
fruit_jam.volume = 0.5

player = adafruit_flac.FLACPlayer(fruit_jam.audio)
print("Playing FLAC file!")
player.play(decoder)
while player.playing:
    player.update()  # decode the next piece; call this often while playing

print("Done!")
