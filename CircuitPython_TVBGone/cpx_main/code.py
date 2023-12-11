# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array
import time

import board
import pulseio
from digitalio import DigitalInOut, Direction, Pull

# pylint: disable=eval-used
# Switch to select 'stealth-mode'
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
# Button to see output debug
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# Speaker as haptic feedback
spkr_en = DigitalInOut(board.SPEAKER_ENABLE)
spkr_en.direction = Direction.OUTPUT
spkr_en.value = True
spkr = DigitalInOut(board.SPEAKER)
spkr.direction = Direction.OUTPUT

# Allow any button to trigger activity!
button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN
button_b = DigitalInOut(board.BUTTON_B)
button_b.direction = Direction.INPUT
button_b.pull = Pull.DOWN

while True:
    # Wait for button press!
    while not (button_a.value or button_b.value):
        pass
    time.sleep(0.5)  # Give a half second before starting

    # gooooo!
    f = open("/codes.txt", "r")
    for line in f:
        code = eval(line)
        print(code)
        if switch.value:
            led.value = True
        else:
            spkr.value = True
        # If this is a repeating code, extract details
        try:
            repeat = code["repeat"]
            delay = code["repeat_delay"]
        except KeyError:  # by default, repeat once only!
            repeat = 1
            delay = 0
        # The table holds the on/off pairs
        table = code["table"]
        pulses = []  # store the pulses here
        # Read through each indexed element
        for i in code["index"]:
            pulses += table[i]  # and add to the list of pulses
        pulses.pop()  # remove one final 'low' pulse

        with pulseio.PulseOut(
            board.REMOTEOUT, frequency=code["freq"], duty_cycle=2**15
        ) as pulse:
            for i in range(repeat):
                pulse.send(array.array("H", pulses))
                time.sleep(delay)

        led.value = False
        spkr.value = False
        time.sleep(code["delay"])

    f.close()
