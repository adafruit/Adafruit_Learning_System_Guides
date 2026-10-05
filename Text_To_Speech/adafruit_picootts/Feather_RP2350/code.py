# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# An example using the Adafruit_PicoTTS library to generate speech using an Adafruit Feather
#   RP2350 with a MAX 98357A I2S amplifier

import time
import audiobusio
import board

import adafruit_picotts as speech

# On the RP2350, bit clock and word select must be consecutive GPIOs: A0 and A1 are GPIO26
# and GPIO27.
audio = audiobusio.I2SOut(board.A0, board.A1, board.A2)

tts = speech.TTS(audio)

while True:
    for text in (
        "Hello from Circuit Python.",
        "This is the S VOX Pico voice.",
        "Dr. Smith read 1,234 pages on the 1st of May.",
    ):
        start = time.monotonic()
        tts.say(text)
        print(f"{text} {time.monotonic() - start:.2f} s")
        time.sleep(1)
    time.sleep(3)
