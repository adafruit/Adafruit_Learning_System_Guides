# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Planetary Gear Dreidel Code - slightly modified from the STSPIN220 example
"""

import board

import adafruit_stspin

STEPS_PER_REVOLUTION = 200

DIR_PIN = board.D2  # DIRection pin
STEP_PIN = board.D3  # STEP pin
MODE1_PIN = board.D4  # Mode 1 pin (REQUIRED for mode switching)
MODE2_PIN = board.D5  # Mode 2 pin (REQUIRED for mode switching)
EN_FAULT_PIN = board.D6  # Enable/Fault pin (optional)
STBY_RESET_PIN = board.D7  # Standby/Reset pin (REQUIRED for mode switching)

print("Initializing STSPIN220...")
motor = adafruit_stspin.STSPIN(
    STEP_PIN,
    DIR_PIN,
    STEPS_PER_REVOLUTION,
    mode1_pin=MODE1_PIN,
    mode2_pin=MODE2_PIN,
    en_fault_pin=EN_FAULT_PIN,
    stby_reset_pin=STBY_RESET_PIN,
)

# Set the speed to 60 RPM
motor.speed = 60
motor.step_mode = adafruit_stspin.Modes.STEP_1_128

while True:
    # continuously step the motor
    total_microsteps = STEPS_PER_REVOLUTION * motor.microsteps_per_step
    motor.step(total_microsteps)
