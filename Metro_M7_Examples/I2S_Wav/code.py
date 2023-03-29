# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython I2S WAV file playback.
Plays a WAV file once.

Remove this line and all of the following docstring content before submitting to the Learn repo.

Update the three I2S pins to match the wiring chosen for the microcontroller. If you are unsure of
a proper I2S pin combination, run the pin combination script found here:
https://adafru.it/i2s-pin-combo-finder

Update the following pin names to a viable pin combination:
* BIT_CLOCK_PIN
* WORD_SELECT_PIN
* DATA_PIN
"""
import audiocore
import board
import audiobusio

audio = audiobusio.I2SOut(board.D10, board.D9, board.D12)

with open("StreetChicken.wav", "rb") as wave_file:
    wav = audiocore.WaveFile(wave_file)

    print("Playing wav file!")
    audio.play(wav)
    while audio.playing:
        pass

print("Done!")
