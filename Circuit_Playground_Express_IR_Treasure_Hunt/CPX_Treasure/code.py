# SPDX-FileCopyrightText: 2018 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import pulseio
import adafruit_irremote
import neopixel

# Configure treasure information
TREASURE_ID = 1      # CHANGE THIS NUMBER TO 2, 3, ETC, A UNIQUE NUMBER FOR EACH TREASURE!
TRANSMIT_DELAY = 15  # change this as desired to affect game dynamics, or just leave as is

# Create NeoPixel object to indicate status
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

# Create a 'pulseio' output, to send infrared signals on the IR transmitter @ 38KHz
pulseout = pulseio.PulseOut(board.IR_TX, frequency=38000, duty_cycle=2 ** 15)

# Create an encoder that will take numbers and turn them into IR pulses
encoder = adafruit_irremote.GenericTransmit(header=[9500, 4500],
                                            one=[550, 1700],
                                            zero=[550, 550],
                                            trail=0)

while True:
    pixels.fill(0xFF0000)
    encoder.transmit(pulseout, [TREASURE_ID]*4)
    time.sleep(0.25)
    pixels.fill(0)
    time.sleep(TRANSMIT_DELAY)
