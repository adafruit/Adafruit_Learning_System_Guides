# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import digitalio


def blink(pin, interval, count):
    with digitalio.DigitalInOut(pin) as led:
        led.switch_to_output(value=False)
        for _ in range(count):
            led.value = True
            time.sleep(interval)
            led.value = False
            time.sleep(interval)


def main():
    blink(board.D1, 0.25, 10)
    print("done")


main()
