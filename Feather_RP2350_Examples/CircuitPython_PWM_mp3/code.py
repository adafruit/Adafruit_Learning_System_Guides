# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython single MP3 playback example.
Plays a single MP3 once.
"""
import board
import audiomp3
import audiopwmio

audio = audiopwmio.PWMAudioOut(board.A0)

with open("slow.mp3", "rb") as mp3_file:
    decoder = audiomp3.MP3Decoder(mp3_file)

    audio.play(decoder)
    while audio.playing:
        pass

print("Done playing!")
