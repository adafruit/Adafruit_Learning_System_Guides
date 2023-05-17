# SPDX-FileCopyrightText: 2023 Carter N. for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import digitalio
import adafruit_si4713

radio = adafruit_si4713.SI4713(
    board.I2C(),
    reset=digitalio.DigitalInOut(board.D26),
    timeout_s=0.5
)

with open("freq_scan.dat", "w") as fp:
    for f_khz in range(87500, 108000, 50):
        noise = radio.received_noise_level(f_khz)
        fp.write("{},{}\n".format(f_khz/1000.0, noise))
        print('{0:0.3f} mhz = {1} dBuV'.format(f_khz/1000.0, noise))
