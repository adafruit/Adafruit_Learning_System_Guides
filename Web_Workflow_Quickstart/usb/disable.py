# SPDX-FileCopyrightText: 2022 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import microcontroller
microcontroller.nvm[0] = 0
microcontroller.reset()
