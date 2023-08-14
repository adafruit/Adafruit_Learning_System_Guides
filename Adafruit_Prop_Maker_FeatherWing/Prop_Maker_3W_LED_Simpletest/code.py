# SPDX-FileCopyrightText: 2019, 2023 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple rainbow swirl example for 3W LED"""
import time
import pwmio
import board
import digitalio

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True


def colorwheel(pos):
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - pos * 3)


red = pwmio.PWMOut(board.D11, duty_cycle=0, frequency=20000)
green = pwmio.PWMOut(board.D12, duty_cycle=0, frequency=20000)
blue = pwmio.PWMOut(board.D13, duty_cycle=0, frequency=20000)

while True:
    for i in range(255):
        r, g, b = colorwheel(i)
        red.duty_cycle = int(r * 65536 / 256)
        green.duty_cycle = int(g * 65536 / 256)
        blue.duty_cycle = int(b * 65536 / 256)
        time.sleep(0.05)
