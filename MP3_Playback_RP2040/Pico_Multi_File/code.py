# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython multiple MP3 playback example for Raspberry Pi Pico.
Plays two MP3 files consecutively, once time each.
"""
import board
import audiomp3
import audiopwmio

audio = audiopwmio.PWMAudioOut(board.GP0)

mp3files = ["slow.mp3", "happy.mp3"]

mp3 = open(mp3files[0], "rb")
decoder = audiomp3.MP3Decoder(mp3)

for filename in mp3files:
    decoder.file = open(filename, "rb")
    audio.play(decoder)
    print("Playing:", filename)
    while audio.playing:
        pass

print("Done playing!")
