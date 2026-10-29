# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""SDIO microSD card data logging example"""
import time
import board
import microcontroller
import storage
import sdioio

sd = sdioio.SDCard(
    clock=board.SD_CLK,
    command=board.SD_CMD,
    data=(board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3),
    frequency=25000000)
vfs = storage.VfsFat(sd)
storage.mount(vfs, '/sd')
print("Logging temperature to microSD card")
# append to the file!
while True:
    # open file for append
    with open("/sd/temperature.txt", "a") as f:
        t = microcontroller.cpu.temperature
        print("Temperature = %0.1f" % t)
        f.write("%0.1f\n" % t)
    # file is saved
    time.sleep(1)
