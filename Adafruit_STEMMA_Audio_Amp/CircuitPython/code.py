# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython PWM Audio Short Tone Tune Demo

Plays a five-note tune on a loop.
"""
import time
import array
import math
import board
from audiocore import RawSample
from audiopwmio import PWMAudioOut as AudioOut

# Increase this to increase the volume of the tone.
tone_volume = 0.1
# The tones are provided as a frequency in Hz. You can change the current tones or
# add your own to make a new tune. Follow the format with commas between values.
tone_frequency = [784, 880, 698, 349, 523]

audio = AudioOut(board.A0)

while True:
    # Play each tone in succession.
    for frequency in tone_frequency:
        # Compute the sine wave for the current frequency.
        length = 8000 // frequency
        sine_wave = array.array("H", [0] * length)
        for index in range(length):
            sine_wave[index] = int((1 + math.sin(math.pi * 2 * index / length))
                                   * tone_volume * (2 ** 15 - 1))

        sine_wave_sample = RawSample(sine_wave)

        # Play the current frequency.
        audio.play(sine_wave_sample, loop=True)
        time.sleep(0.5)
        audio.stop()
        time.sleep(1)

    # All done playing all tones; start over from the beginning.
