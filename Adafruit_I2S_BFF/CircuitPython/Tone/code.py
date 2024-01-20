# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython I2S Tone playback example.
"""
import time
import array
import math
import audiocore
import board
import audiobusio

TONE_VOLUME = 0.1  # Increase this to increase the volume of the tone.
FREQUENCY = 440  # Set this to the Hz of the tone you want to generate.

audio = audiobusio.I2SOut(board.A2, board.A1, board.A0)

length = 8000 // FREQUENCY
sine_wave = array.array("h", [0] * length)
for i in range(length):
    sine_wave[i] = int((math.sin(math.pi * 2 * i / length)) * TONE_VOLUME * (2 ** 15 - 1))
sine_wave_sample = audiocore.RawSample(sine_wave)

while True:
    audio.play(sine_wave_sample, loop=True)
    time.sleep(1)
    audio.stop()
    time.sleep(1)
