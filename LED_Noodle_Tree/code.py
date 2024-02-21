# SPDX-FileCopyrightText: 2023 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import math
import time
import board
import adafruit_aw9523

GAMMA = 2.6         # For perceptually-linear brightness
PINS = (15, 14, 13, 12, 7, 6, 5, 4) # List of pins, one per nOOd

# Instantiate AW9523 on STEMMA I2C bus. This was tested on QT Py RP2040.
# Other boards might require board.I2C() instead of board.STEMMA_I2C().
aw = adafruit_aw9523.AW9523(board.STEMMA_I2C())

for pin in PINS:
    aw.get_pin(pin).switch_to_output(value=True) # Activate pin, initialize OFF
    aw.LED_modes |= 1 << pin                     # Enable constant-current on pin

while True:                        # Repeat forever...
    for i, pin in enumerate(PINS): # For each pin...
        # Calc sine wave, phase offset for each pin, with gamma correction.
        # If using red, green, blue nOOds, you'll get a cycle of hues.
        phase = (time.monotonic() - 2 * i / len(PINS)) * math.pi
        brightness = int((math.sin(phase) + 1.0) * 0.5 ** GAMMA * 255 + 0.5)
        aw.set_constant_current(pin, brightness)
