# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# LM73100 IMON Current Monitoring

import time
import board
from analogio import AnalogIn

RIMON = 1500.0 # 1.5kΩ
GIMON = 2.5 # μA/A
analog_in = AnalogIn(board.A0)

def get_voltage(pin):
    return (pin.value * 3.3) / 65536

print("LM73100 Current Monitor Started")
print("================================")
print(f"RIMON: {RIMON} ohms")
print(f"GIMON: {GIMON} μA/A")
print("================================\n")

while True:
    # Read voltage from IMON pin
    vimon = get_voltage(analog_in)

    # Calculate output current
    iout_A = vimon / (RIMON * GIMON)
    iout_mA = iout_A * 1000.0

    print(f"ADC: {analog_in.value} | VIMON: {vimon:.3f}V | Current: {iout_mA:.2f} mA")

    time.sleep(0.5)
