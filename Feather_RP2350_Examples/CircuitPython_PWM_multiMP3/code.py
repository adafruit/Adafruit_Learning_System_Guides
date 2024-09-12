# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython multiple MP3 playback example.
Plays two MP3 files consecutively, once time each.
"""

import board
import audiomp3
import audiopwmio

audio = audiopwmio.PWMAudioOut(board.A0)

mp3files = ["slow.mp3", "happy.mp3"]

with open(mp3files[0], "rb") as mp3:
    decoder = audiomp3.MP3Decoder(mp3)

    for filename in mp3files:
        with open(filename, "rb") as decoder.file:
            audio.play(decoder)
            print("Playing:", filename)
            while audio.playing:
                pass

print("Done playing!")
