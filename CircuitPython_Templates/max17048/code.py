# SPDX-FileCopyrightText: Copyright (c) 2023 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

import time
import board
import adafruit_max1704x

monitor = adafruit_max1704x.MAX17048(board.I2C())

while True:
    print(f"Battery voltage: {monitor.cell_voltage:.2f} Volts")
    print(f"Battery percentage: {monitor.cell_percent:.1f} %")
    print("")
    time.sleep(1)
