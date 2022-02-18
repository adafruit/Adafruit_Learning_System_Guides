# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython I2S MP3 playback example.
Plays a single MP3 once.
"""
import board
import audiomp3
import audiobusio

audio = audiobusio.I2SOut(board.GP0, board.GP1, board.GP2)

mp3 = audiomp3.MP3Decoder(open("slow.mp3", "rb"))

audio.play(mp3)
while audio.playing:
    pass

print("Done playing!")
