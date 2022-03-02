# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Close Encounters Hat with 10 NeoPixels
# ported from Leslie Birch's Arduino to CircuitPython
#
# Photocell voltage divider center wire to GPIO #2 (analog 1)
# and output tone to GPIO #0 (digital 0)

import time

import analogio
import board
import neopixel
import simpleio

# Initialize input/output pins
photocell_pin = board.A1  # cds photocell connected to this ANALOG pin
speaker_pin = board.D0  # speaker is connected to this DIGITAL pin
pixpin = board.D1  # pin where NeoPixels are connected
numpix = 10  # number of neopixels`
darkness_min = (2 ** 16 / 2)  # more dark than light > 32k out of 64k
photocell = analogio.AnalogIn(photocell_pin)
strip = neopixel.NeoPixel(pixpin, numpix, brightness=.4)

# this section is Close Encounters Sounds
toned = 294
tonee = 330
tonec = 262
toneC = 130
toneg = 392


def alien():
    strip[8] = (255, 255, 0)  # yellow front
    strip[3] = (255, 255, 0)  # yellow back
    simpleio.tone(speaker_pin, toned, 1)  # play tone for 1 second

    time.sleep(.025)

    strip[8] = (0, 0, 0)  # clear front
    strip[3] = (0, 0, 0)  # clear back

    time.sleep(.025)

    strip[7] = (255, 0, 255)  # pink front
    strip[2] = (255, 0, 255)  # pink back
    simpleio.tone(speaker_pin, tonee, 1)  # play tone for 1 second

    time.sleep(.025)

    strip[7] = (0, 0, 0)  # clear front
    strip[2] = (0, 0, 0)  # clear back

    time.sleep(.025)

    strip[4] = (128, 255, 0)  # green front
    strip[9] = (128, 255, 0)  # green back
    simpleio.tone(speaker_pin, tonec, 1)  # play tone for 1 second

    time.sleep(.025)

    strip[4] = (0, 0, 0)  # clear front
    strip[9] = (0, 0, 0)  # clear back

    time.sleep(.025)

    strip[5] = (0, 0, 255)  # blue front
    strip[0] = (0, 0, 255)  # blue back
    simpleio.tone(speaker_pin, toneC, 1)  # play tone for 1 second

    time.sleep(.075)

    strip[5] = (0, 0, 0)  # clear front
    strip[0] = (0, 0, 0)  # clear back

    time.sleep(.1)

    strip[6] = (255, 0, 0)  # red front
    strip[1] = (255, 0, 0)  # red back
    simpleio.tone(speaker_pin, toneg, 1)  # play tone for 1 second

    time.sleep(.1)

    strip[6] = (0, 0, 0)  # clear front
    strip[1] = (0, 0, 0)  # clear back

    time.sleep(.1)


# Loop forever...
while True:

    # turn lights and audio on when dark
    # (less than 50% light on analog pin)
    if photocell.value > darkness_min:
        alien()  # close Encounters Loop
