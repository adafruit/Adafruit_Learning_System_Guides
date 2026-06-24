# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""USB audio Morse code paddle. Connect Morse paddle 3.5mm jack to pin A1 and GND.

Connect the board to a host computer and select the CircuitPython USB
microphone as a recording/input device.

Use the paddle to enter Morse code live, update the button messages to
automatically convert and send pre-programmed strings with the built-in
buttons.
"""

import time

import board
import digitalio
import synthio
import usb_audio
import adafruit_debouncer

# Configuration

BTN_A_MESSAGE = "HELLO WORLD"
BTN_B_MESSAGE = "CIRCUITPYTHON"

TONE_NOTE = 60  # synthio note number for the tone pitch (MIDI note, 60 = C4)

# Morse timing is defined in "units". A dot is one unit long; everything else
# is a multiple of that unit. Increase UNIT_SECONDS to slow the code down.
UNIT_SECONDS = 0.085

DOT_DURATION = UNIT_SECONDS  # length of a dot
DASH_DURATION = UNIT_SECONDS * 3  # length of a dash
SYMBOL_GAP = UNIT_SECONDS  # silence between dots/dashes in one letter
LETTER_GAP = UNIT_SECONDS * 3  # silence between letters
WORD_GAP = UNIT_SECONDS * 7  # silence between words (the " " character)

# Morse code table

MORSE_CODE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "(": "-.--.",
    ")": "-.--.-",
    "&": ".-...",
    ":": "---...",
    ";": "-.-.-.",
    "=": "-...-",
    "+": ".-.-.",
    "-": "-....-",
    "_": "..--.-",
    '"': ".-..-.",
    "$": "...-..-",
    "@": ".--.-.",
}

# Setup

mic = usb_audio.usb_microphone
synth = synthio.Synthesizer(sample_rate=16000, channel_count=1)
mic.play(synth)


def play_tone(duration):
    """Sound the tone for ``duration`` seconds, then go silent."""
    synth.press(TONE_NOTE)
    time.sleep(duration)
    synth.release(TONE_NOTE)


def play_morse(text):
    """Translate ``text`` to Morse code and play it with synthio."""
    words = text.upper().split(" ")
    for word_index, word in enumerate(words):
        if word_index > 0:
            # gap between words
            time.sleep(WORD_GAP)

        for letter_index, letter in enumerate(word):
            pattern = MORSE_CODE.get(letter)
            if pattern is None:
                # skip characters we don't know how to send
                continue

            if letter_index > 0:
                # gap between letters
                time.sleep(LETTER_GAP)

            for symbol_index, symbol in enumerate(pattern):
                if symbol_index > 0:
                    # gap between symbols within a letter
                    time.sleep(SYMBOL_GAP)
                if symbol == ".":
                    play_tone(DOT_DURATION)
                else:
                    play_tone(DASH_DURATION)


btn_a = digitalio.DigitalInOut(board.BUTTON_A)
btn_a.switch_to_input(digitalio.Pull.DOWN)
btn_a_debounce = adafruit_debouncer.Debouncer(btn_a)

btn_b = digitalio.DigitalInOut(board.BUTTON_B)
btn_b.switch_to_input(digitalio.Pull.DOWN)
btn_b_debounce = adafruit_debouncer.Debouncer(btn_b)

morse_paddle_dio = digitalio.DigitalInOut(board.A1)
morse_paddle_dio.switch_to_input(digitalio.Pull.UP)
morse_paddle_debounce = adafruit_debouncer.Debouncer(morse_paddle_dio)

# Main loop

while True:
    btn_a_debounce.update()
    btn_b_debounce.update()
    morse_paddle_debounce.update()

    if morse_paddle_debounce.fell:
        synth.press(60)
    if morse_paddle_debounce.rose:
        synth.release(60)

    if btn_a_debounce.rose:
        play_morse(BTN_A_MESSAGE)
    if btn_b_debounce.rose:
        play_morse(BTN_B_MESSAGE)
