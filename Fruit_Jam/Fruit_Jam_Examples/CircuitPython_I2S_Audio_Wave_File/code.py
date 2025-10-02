# SPDX-FileCopyrightText: 2025 Liz Clark, Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import audiocore

from adafruit_fruitjam.peripherals import Peripherals

fruit_jam = Peripherals()

# use headphones
fruit_jam.dac.headphone_output = True
fruit_jam.dac.dac_volume = -10  # dB
# or use speaker
# fruit_jam.dac.speaker_output = True
# fruit_jam.dac.speaker_volume = -20 # dB

# set sample rate & bit depth, use bclk
fruit_jam.dac.configure_clocks(sample_rate=44100, bit_depth=16)

with open("StreetChicken.wav", "rb") as wave_file:
    wav = audiocore.WaveFile(wave_file)

    print("Playing wav file!")
    fruit_jam.audio.play(wav)
    while fruit_jam.audio.playing:
        pass

print("Done!")
