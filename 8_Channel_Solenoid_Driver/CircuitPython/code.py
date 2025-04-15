# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_mcp230xx.mcp23017 import MCP23017

i2c = board.STEMMA_I2C()

mcp = MCP23017(i2c)

noid_1 = mcp.get_pin(0)
noid_2 = mcp.get_pin(4)
noid_1.switch_to_output(value=False)
noid_2.switch_to_output(value=False)

while True:
    noid_1.value = True
    print(f"Solenoid 1: {noid_1.value}, Solenoid 2: {noid_2.value}")
    time.sleep(0.2)
    noid_1.value = False
    print(f"Solenoid 1: {noid_1.value}, Solenoid 2: {noid_2.value}")
    time.sleep(0.2)
    noid_2.value = True
    print(f"Solenoid 1: {noid_1.value}, Solenoid 2: {noid_2.value}")
    time.sleep(0.2)
    noid_2.value = False
    print(f"Solenoid 1: {noid_1.value}, Solenoid 2: {noid_2.value}")
    time.sleep(1)
    noid_1.value = True
    noid_2.value = True
    print(f"Solenoid 1: {noid_1.value}, Solenoid 2: {noid_2.value}")
    time.sleep(1)
    noid_1.value = False
    noid_2.value = False
    print(f"Solenoid 1: {noid_1.value}, Solenoid 2: {noid_2.value}")
    time.sleep(2)
