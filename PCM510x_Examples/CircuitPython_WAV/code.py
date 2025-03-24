# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython I2S WAV file playback.
Plays a WAV file once.
"""
import audiocore
import board
import audiobusio

audio = audiobusio.I2SOut(board.D9, board.D10, board.D11)

with open("StreetChicken.wav", "rb") as wave_file:
    wav = audiocore.WaveFile(wave_file)

    print("Playing wav file!")
    audio.play(wav)
    while audio.playing:
        pass

print("Done!")
