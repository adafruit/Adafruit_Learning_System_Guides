# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython 10.x SD Write Demo
  • Assumes /sd is auto-mounted by the runtime
  • Just open and append — no mount or SD driver code needed
  • Not compatible with CircuitPython 9.x
  • Uses SDIO
"""

import time
import microcontroller

print("Logging temperature to /sd/temperature.txt")

while True:
    t = microcontroller.cpu.temperature
    print("T = %0.1f °C" % t)
    with open("/sd/temperature.txt", "a") as f:
        f.write("%0.1f\n" % t)
    time.sleep(1)
