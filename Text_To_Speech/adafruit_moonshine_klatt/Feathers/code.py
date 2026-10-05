# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# An example using the Adafruit_Moonshine_Klatt library to generate speech using an Adafruit Feather
#   boards with an external wired MAX98357A I2S amplifier

import time
import audiobusio
import board

import adafruit_moonshine_klatt as speech

audio = audiobusio.I2SOut(board.A0, board.A1, board.A2)
tts = speech.TTS(audio)

while True:
    for voice in tts.voices:
        tts.voice = voice
        start = time.monotonic()
        tts.say(f"Hello from Circuit Python. This is the {voice} voice.")
        print(f"{voice}: {time.monotonic() - start:.2f} s")
        time.sleep(1)
    time.sleep(3)
