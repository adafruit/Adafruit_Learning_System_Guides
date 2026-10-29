# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""SDIO microSD card reading directory example"""

import os
import board
import sdioio
import storage

sd = sdioio.SDCard(
    clock=board.SD_CLK,
    command=board.SD_CMD,
    data=(board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3),
    frequency=25000000)
vfs = storage.VfsFat(sd)
storage.mount(vfs, '/sd')
os.listdir('/sd')
print(os.listdir('/sd'))
