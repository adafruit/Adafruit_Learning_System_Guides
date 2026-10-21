# SPDX-FileCopyrightText: Copyright (c) 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Play an Ogg Vorbis file once through the Fruit Jam headphone jack."""

from adafruit_fruitjam.peripherals import Peripherals
import adafruit_ogg

# Make the decoder first: it decodes several times faster with its buffers in internal RAM.
decoder = adafruit_ogg.OggDecoder("song.ogg")

fruit_jam = Peripherals(audio_output="headphone", sample_rate=decoder.sample_rate)
fruit_jam.volume = 0.5

player = adafruit_ogg.OggPlayer(fruit_jam.audio)
print("Playing Ogg file!")
player.play(decoder)
while player.playing:
    player.update()  # decode the next piece; call this often while playing

print("Done!")
