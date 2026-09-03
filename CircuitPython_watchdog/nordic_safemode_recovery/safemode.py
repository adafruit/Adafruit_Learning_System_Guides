# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Reboot back into normal mode from safemode after a short delay.
"""
import time
import microcontroller

time.sleep(3)
microcontroller.reset()
