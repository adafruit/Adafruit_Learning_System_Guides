# SPDX-FileCopyrightText: 2022 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import microcontroller
status = 'enabled' if microcontroller.nvm[0] == 1 else 'disabled'
print(f"USB Mass Storage is {status} on this device")
