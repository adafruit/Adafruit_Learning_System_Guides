# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython I2S Tone playback example.
Plays a tone for one second on, one
second off, in a loop.

Remove this line and all of the following docstring content before submitting to the Learn repo.

Update the three I2S pins to match the wiring chosen for the microcontroller. If you are unsure of
a proper I2S pin combination, run the pin combination script found here:
https://adafru.it/i2s-pin-combo-finder

Update the following pin names to a viable pin combination:
* BIT_CLOCK_PIN
* WORD_SELECT_PIN
* DATA_PIN
"""
import time
import array
import math
import audiocore
import board
import audiobusio

audio = audiobusio.I2SOut(board.BIT_CLOCK_PIN, board.WORD_SELECT_PIN, board.DATA_PIN)

tone_volume = 0.1  # Increase this to increase the volume of the tone.
frequency = 440  # Set this to the Hz of the tone you want to generate.
length = 8000 // frequency
sine_wave = array.array("h", [0] * length)
for i in range(length):
    sine_wave[i] = int((math.sin(math.pi * 2 * i / length)) * tone_volume * (2 ** 15 - 1))
sine_wave_sample = audiocore.RawSample(sine_wave)

while True:
    audio.play(sine_wave_sample, loop=True)
    time.sleep(1)
    audio.stop()
    time.sleep(1)
