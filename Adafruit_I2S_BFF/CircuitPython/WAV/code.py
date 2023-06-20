# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython I2S WAV file playback.
"""
import audiocore
import board
import audiobusio

LOOP = False  # Update to True loop WAV playback. False plays once.

audio = audiobusio.I2SOut(board.A2, board.A1, board.A0)

with open("chikken.wav", "rb") as wave_file:
    wav = audiocore.WaveFile(wave_file)

    print("Playing wav file!")
    audio.play(wav, loop=LOOP)
    while audio.playing:
        pass

print("Done!")
