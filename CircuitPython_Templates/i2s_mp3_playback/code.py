# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython I2S MP3 playback example.
Plays an MP3 once.

Remove this line and all of the following docstring content before submitting to the Learn repo.

Update the three I2S pins to match the wiring chosen for the microcontroller. If you are unsure of
a proper I2S pin combination, run the pin combination script found here:
https://adafru.it/i2s-pin-combo-finder

Update the following pin names to a viable pin combination:
* BIT_CLOCK_PIN
* WORD_SELECT_PIN
* DATA_PIN
"""
import board
import audiomp3
import audiobusio

audio = audiobusio.I2SOut(board.BIT_CLOCK_PIN, board.WORD_SELECT_PIN, board.DATA_PIN)

with open("slow.mp3", "rb") as mp3_file:
    mp3 = audiomp3.MP3Decoder(mp3_file)

    audio.play(mp3)
    while audio.playing:
        pass

print("Done playing!")
