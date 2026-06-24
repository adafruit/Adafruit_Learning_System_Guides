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
import keypad
import synthio
import usb_audio

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


btns_builtin = keypad.Keys((board.BUTTON_A, board.BUTTON_B), value_when_pressed=True)
btn_morse_key = keypad.Keys((board.A1,), value_when_pressed=False)

# Main loop

while True:
    event = btns_builtin.events.get()
    if event is not None:
        # built-in A button
        if event.pressed and event.key_number == 0:
            play_morse(BTN_A_MESSAGE)
        # built-in B button
        elif event.pressed and event.key_number == 1:
            play_morse(BTN_B_MESSAGE)

    event = btn_morse_key.events.get()
    if event is not None:
        if event.pressed and event.key_number == 0:
            synth.press(TONE_NOTE)
        elif not event.pressed and event.key_number == 0:
            synth.release(TONE_NOTE)
