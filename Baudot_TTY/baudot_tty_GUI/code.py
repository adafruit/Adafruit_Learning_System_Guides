# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

### Baudot TTY Message Transmitter with CLUE GUI
### Pick from four phrases to send from the CLUE screen with buttons

### The 5-bit mode is defined in ANSI TIA/EIA-825 (2000)
### "A Frequency Shift Keyed Modem for use on the Public Switched Telephone Network"

import time
import math
import array
import board
from audiocore import RawSample
import audiopwmio
import displayio
from adafruit_display_shapes.circle import Circle
from adafruit_clue import clue
from adafruit_display_text import label
import terminalio

# Enter your messages here no more than 34 characters including spaces per line
messages = [
    "HELLO FROM ADAFRUIT INDUSTRIES",
    "12345678910 -$!+='()/:;?",
    "WOULD YOU LIKE TO PLAY A GAME?",
    "WELCOME TO JOHN PARK'S WORKSHOP",
]


clue.display.brightness = 1.0
screen = displayio.Group()

VFD_GREEN = 0x00FFD2
VFD_BG = 0x000505

# setup screen
# BG
color_bitmap = displayio.Bitmap(240, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = VFD_BG
bg_sprite = displayio.TileGrid(color_bitmap, x=0, y=0, pixel_shader=color_palette)
screen.append(bg_sprite)

# title
title_label = label.Label(
    terminalio.FONT, text="TTY CLUE", scale=4, color=VFD_GREEN
)
title_label.x = 20
title_label.y = 16
screen.append(title_label)

# footer
footer_label = label.Label(
    terminalio.FONT, text="<PICK         SEND>", scale=2, color=VFD_GREEN
)
footer_label.x = 4
footer_label.y = 220
screen.append(footer_label)

# message configs
messages_config = [
    (0, messages[0], VFD_GREEN, 2, 60),
    (1, messages[1], VFD_GREEN, 2, 90),
    (2, messages[2], VFD_GREEN, 2, 120),
    (3, messages[3], VFD_GREEN, 2, 150),
]

messages_labels = {}  # dictionary of configured messages_labels

message_group = displayio.Group(scale=1)

for message_config in messages_config:
    (name, textline, color, x, y) = message_config  # unpack tuple into five var names
    message_label = label.Label(terminalio.FONT, text=textline, color=color)
    message_label.x = x
    message_label.y = y
    messages_labels[name] = message_label
    message_group.append(message_label)
screen.append(message_group)

# selection dot
dot_y = [52, 82, 112, 142]
dot = Circle(220, 60, 8, outline=VFD_GREEN, fill=VFD_BG)
screen.append(dot)

clue.display.root_group = screen

# constants for sine wave generation
SIN_LENGTH = 100  # more is less choppy
SIN_AMPLITUDE = 2 ** 12  # 0 (min) to 32768 (max)  8192 is nice
SIN_OFFSET = 32767.5  # for 16bit range, (2**16 - 1) / 2
DELTA_PI = 2 * math.pi / SIN_LENGTH  # happy little constant

sine_wave = [
    int(SIN_OFFSET + SIN_AMPLITUDE * math.sin(DELTA_PI * i)) for i in range(SIN_LENGTH)
]
tones = (
    RawSample(array.array("H", sine_wave), sample_rate=1800 * SIN_LENGTH),  # Bit 0
    RawSample(array.array("H", sine_wave), sample_rate=1400 * SIN_LENGTH),  # Bit 1
)

bit_0 = tones[0]
bit_1 = tones[1]
carrier = tones[1]


char_pause = 0.1  # pause time between chars, set to 0 for fastest rate possible

dac = audiopwmio.PWMAudioOut(
    board.A2
)  # the CLUE edge connector marked "#0" to STEMMA speaker
# The CLUE's on-board speaker works OK, not great, just crank amplitude to full before trying.
# dac = audiopwmio.PWMAudioOut(board.SPEAKER)


LTRS = (
    "\b",
    "E",
    "\n",
    "A",
    " ",
    "S",
    "I",
    "U",
    "\r",
    "D",
    "R",
    "J",
    "N",
    "F",
    "C",
    "K",
    "T",
    "Z",
    "L",
    "W",
    "H",
    "Y",
    "P",
    "Q",
    "O",
    "B",
    "G",
    "FIGS",
    "M",
    "X",
    "V",
    "LTRS",
)

FIGS = (
    "\b",
    "3",
    "\n",
    "-",
    " ",
    "-",
    "8",
    "7",
    "\r",
    "$",
    "4",
    "'",
    ",",
    "!",
    ":",
    "(",
    "5",
    '"',
    ")",
    "2",
    "=",
    "6",
    "0",
    "1",
    "9",
    "?",
    "+",
    "FIGS",
    ".",
    "/",
    ";",
    "LTRS",
)

char_count = 0
current_mode = LTRS

#  The 5-bit Baudot text telephone (TTY) mode is a Frequency Shift Keyed modem
#  for use on the Public Switched Telephone network.
#
#   Definitions:
#       Carrier tone is a 1400Hz tone.
#       Binary 0 is an 1800Hz tone.
#       Binary 1 is a 1400Hz tone.
#       Bit duration is 20ms.

#       Two modes exist: Letters, aka LTRS, for alphabet characters
#       and Figures aka FIGS for numbers and symbols. These modes are switched by
#       sending the appropriate 5-bit LTRS or FIGS character.
#
#   Character transmission sequence:
#       Carrier tone transmits for 150ms before each character.
#       Start bit is a binary 0 (sounded for one bit duration of 20ms).
#       5-bit character code can be a combination of binary 0s and binary 1s.
#       Stop bit is a binary 1 with a minimum duration of 1-1/2 bits (30ms)
#
#


def baudot_bit(pitch=bit_1, duration=0.022):  # spec says 20ms, but adjusted as needed
    dac.play(pitch, loop=True)
    time.sleep(duration)
    # dac.stop()


def baudot_carrier(duration=0.15):  # Carrier tone is transmitted for 150 ms before the
    # first character is transmitted
    baudot_bit(carrier, duration)
    dac.stop()


def baudot_start():
    baudot_bit(bit_0)


def baudot_stop():
    baudot_bit(bit_1, 0.04)  # minimum duration is 30ms
    dac.stop()


def send_character(value):
    baudot_carrier()  # send carrier tone
    baudot_start()  # send start bit tone
    for i in range(5):  # send each bit of the character
        bit = (value >> i) & 0x01  # bit shift and bit mask to get value of each bit
        baudot_bit(tones[bit])  # send each bit, either 0 or 1, of a character
    baudot_stop()  # send stop bit
    baudot_carrier()  # not to spec, but works better to extend carrier


def send_message(text):
    global char_count, current_mode  # pylint: disable=global-statement
    for char in text:
        if char not in LTRS and char not in FIGS:  # just skip unknown characters
            print("Unknown character:", char)
            continue

        if char not in current_mode:  # switch mode
            if current_mode == LTRS:
                print("Switching mode to FIGS")
                current_mode = FIGS
                send_character(current_mode.index("FIGS"))
            elif current_mode == FIGS:
                print("Switching mode to LTRS")
                current_mode = LTRS
                send_character(current_mode.index("LTRS"))
        # Send char mode at beginning of message and every 72 characters
        if char_count >= 72 or char_count == 0:
            print("Resending mode")
            if current_mode == LTRS:
                send_character(current_mode.index("LTRS"))
            elif current_mode == FIGS:
                send_character(current_mode.index("FIGS"))
            # reset counter
            char_count = 0
        print(char)
        send_character(current_mode.index(char))
        time.sleep(char_pause)
        # increment counter
        char_count += 1


message_pick = 0

while True:
    if clue.button_a:
        message_pick = (message_pick + 1) % 4  # loop through the lines
        dot.y = dot_y[message_pick]
        time.sleep(0.4)  # debounce

    if clue.button_b:
        dot.fill = VFD_GREEN
        send_message(messages[message_pick])
        dot.fill = VFD_BG
