# SPDX-FileCopyrightText: 2022 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import storage
import microcontroller

if microcontroller.nvm[0] != 1:
    storage.disable_usb_drive()
