# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# An example using the Adafruit_Moonshine_klatt library to generate speech using an Adafruit Feather
#   RP2040 Prop-Maker with an on-board I2S amplifier

import time
import audiobusio
import board
import digitalio

import adafruit_moonshine_klatt as speech

external_power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
external_power.switch_to_output(value=True)
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
tts = speech.TTS(audio)

while True:
    for voice in tts.voices:
        tts.voice = voice
        start = time.monotonic()
        tts.say(f"Hello from Circuit Python. This is the {voice} voice.")
        print(f"{voice}: {time.monotonic() - start:.2f} s")
        time.sleep(1)
    time.sleep(3)
