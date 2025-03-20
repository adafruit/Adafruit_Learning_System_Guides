# SPDX-FileCopyrightText: 2025 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import pwmio

# Configure pins
AIN1 = pwmio.PWMOut(board.D5, frequency=2000)
AIN2 = pwmio.PWMOut(board.D6, frequency=2000)
SLP = digitalio.DigitalInOut(board.D7)

SLP.switch_to_output()

# Enable DRV8833
SLP.value = True

# Loop forever
while True:
    #
    # FORWARD
    #
    print("Forward")
    AIN2.duty_cycle = 0
    print("  ramping up")
    for duty_cycle in range(0, 65536, 100):
        AIN1.duty_cycle = duty_cycle
        time.sleep(0.01)
    print("  ramping down")
    for duty_cycle in range(65535, -1, -100):
        AIN1.duty_cycle = duty_cycle
        time.sleep(0.01)

    #
    # REVERSE
    #
    print("Reverse")
    AIN1.duty_cycle = 0
    print("  ramping up")
    for duty_cycle in range(0, 65536, 100):
        AIN2.duty_cycle = duty_cycle
        time.sleep(0.01)
    print("  ramping down")
    for duty_cycle in range(65535, -1, -100):
        AIN2.duty_cycle = duty_cycle
        time.sleep(0.01)
