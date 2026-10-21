# SPDX-FileCopyrightText: Copyright (c) 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Play an Ogg Vorbis file once on a Feather through a MAX98357A I2S amplifier and a speaker.

Wiring: Feather A0 to BCLK, A1 to LRC, A2 to DIN, 3V to Vin, GND to GND. The amp is mono,
so a mono file at 22 kHz or lower sounds the same and decodes several times faster. On an
ESP32-S3, use 22 kHz or lower: 44.1 kHz stereo does not decode in real time there.
"""

import audiobusio
import board
import adafruit_ogg

# Make the decoder first: it decodes faster with its buffers in internal RAM.
decoder = adafruit_ogg.OggDecoder("song.ogg")

audio = audiobusio.I2SOut(bit_clock=board.A0, word_select=board.A1, data=board.A2)

player = adafruit_ogg.OggPlayer(audio, level=0.1)  # 0.0 (silent) to 1.0 (full)
print("Playing Ogg file!")
player.play(decoder)
while player.playing:
    player.update()  # decode the next piece; call this often while playing

print("Done!")
