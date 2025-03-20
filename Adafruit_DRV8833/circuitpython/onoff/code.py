# SPDX-FileCopyrightText: 2025 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio

# Configure pins
AIN1 = digitalio.DigitalInOut(board.D5)
AIN2 = digitalio.DigitalInOut(board.D6)
SLP = digitalio.DigitalInOut(board.D7)

AIN1.switch_to_output()
AIN2.switch_to_output()
SLP.switch_to_output()

# Enable DRV8833
SLP.value = True

# Loop forever
while True:
    #
    # FORWARD
    #
    print("Forward")
    AIN1.value = True
    AIN2.value = False
    time.sleep(1)

    #
    # REVERSE
    #
    print("Reverse")
    AIN1.value = False
    AIN2.value = True
    time.sleep(1)
