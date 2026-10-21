# SPDX-FileCopyrightText: Copyright (c) 2026 Mikey Sklar for Adafruit Industries
# SPDX-License-Identifier: MIT
"""Play a FLAC file once on a Feather through a MAX98357A I2S amp and a speaker.

Wiring: Feather A0 to BCLK, A1 to LRC, A2 to DIN, 3V to Vin, GND to GND. The amp mixes
stereo files down to mono.
"""

import audiobusio
import board

import adafruit_flac

# Make the decoder first: it decodes faster with its buffers in internal RAM.
decoder = adafruit_flac.FLACDecoder("song.flac")

audio = audiobusio.I2SOut(bit_clock=board.A0, word_select=board.A1, data=board.A2)

player = adafruit_flac.FLACPlayer(audio, level=0.1)  # 0.0 (silent) to 1.0 (full)
print("Playing FLAC file!")
player.play(decoder)
while player.playing:
    player.update()  # decode the next piece; call this often while playing

print("Done!")
