# SPDX-FileCopyrightText: 2019, 2023 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple example to play a wave file"""
# This example only works on Feathers that have analog audio out!
import digitalio
import board
import audiocore

try:
    from audioio import AudioOut
except ImportError:
    try:
        from audiopwmio import PWMAudioOut as AudioOut
    except ImportError:
        pass  # not always supported by every board!

WAV_FILE_NAME = "StreetChicken.wav"  # Change to the name of your wav file!

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

with AudioOut(board.A0) as audio:  # Speaker connector
    wave_file = open(WAV_FILE_NAME, "rb")
    wave = audiocore.WaveFile(wave_file)

    audio.play(wave)
    while audio.playing:
        pass
