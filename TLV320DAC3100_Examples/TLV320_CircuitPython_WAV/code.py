# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import audiobusio
import audiocore
import board
import adafruit_tlv320

i2c = board.I2C()
dac = adafruit_tlv320.TLV320DAC3100(i2c)

# set sample rate & bit depth, use bclk
dac.configure_clocks(sample_rate=44100, bit_depth=16)

# use headphones
dac.headphone_output = True
dac.headphone_volume = -15  # dB
# or use speaker
# dac.speaker_output = True
# dac.speaker_volume = -10 # dB

audio = audiobusio.I2SOut(board.D9, board.D10, board.D11)

with open("StreetChicken.wav", "rb") as wave_file:
    wav = audiocore.WaveFile(wave_file)

    print("Playing wav file!")
    audio.play(wav)
    while audio.playing:
        pass

print("Done!")
