# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython PWM Audio Out WAV example
Play a WAV file once.
"""
import board
from audiocore import WaveFile
from audiopwmio import PWMAudioOut as AudioOut

audio = AudioOut(board.A0)

with open("StreetChicken.wav", "rb") as wave_file:
    wave = WaveFile(wave_file)
    print("Playing wav file!")
    audio.play(wave)
    while audio.playing:
        pass

print("Done!")
