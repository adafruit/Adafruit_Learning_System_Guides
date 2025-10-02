# SPDX-FileCopyrightText: 2025 Liz Clark, Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array
import math
import time

import audiocore

from adafruit_fruitjam.peripherals import Peripherals

fruit_jam = Peripherals()

# use headphones
fruit_jam.dac.headphone_output = True
fruit_jam.dac.dac_volume = -10  # dB
# or use speaker
# fruit_jam.dac.speaker_output = True
# fruit_jam.dac.speaker_volume = -20 # dB

# generate a sine wave
tone_volume = 0.5
frequency = 440
sample_rate = fruit_jam.dac.sample_rate
length = sample_rate // frequency
sine_wave = array.array("h", [0] * length)
for i in range(length):
    sine_wave[i] = int((math.sin(math.pi * 2 * i / length)) * tone_volume * (2**15 - 1))
sine_wave_sample = audiocore.RawSample(sine_wave, sample_rate=sample_rate)

while True:
    fruit_jam.audio.stop()
    time.sleep(1)
    fruit_jam.audio.play(sine_wave_sample, loop=True)
    time.sleep(1)
