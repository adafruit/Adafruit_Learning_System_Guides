# SPDX-FileCopyrightText: 2022 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

import board

from kmk.kmk_keyboard import KMKKeyboard as _KMKKeyboard
from kmk.matrix import DiodeOrientation

# For PB Gherkin (version with no LEDs and where switches can be mounted in 4 orientations)
# and Adafruit KB2040


class KMKKeyboard(_KMKKeyboard):
    row_pins = (board.D10, board.MOSI, board.MISO, board.SCK, board.A0)
    col_pins = (
        board.D3,
        board.D4,
        board.D5,
        board.D6,
        board.D7,
        board.D8,
    )
    diode_orientation = DiodeOrientation.COLUMNS
    i2c = board.I2C
