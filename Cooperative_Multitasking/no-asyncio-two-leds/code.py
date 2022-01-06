# SPDX-FileCopyrightText: 2022 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import digitalio


class Blinker:
    def __init__(self, led, interval, count):
        self.led = led
        self.interval = interval
        # Count both on and off.
        self.count2 = count * 2
        self.last_transition = 0

    def blink(self):
        """Return False when blinking is finished."""
        if self.count2 <= 0:
            return False
        now = time.monotonic()
        if now > self.last_transition + self.interval:
            self.led.value = not self.led.value
            self.last_transition = now
            self.count2 -= 1
        return True


def main():
    with digitalio.DigitalInOut(board.D1) as led1, digitalio.DigitalInOut(
        board.D2
    ) as led2:
        led1.switch_to_output(value=False)
        led2.switch_to_output(value=False)

        blinker1 = Blinker(led1, 0.25, 10)
        blinker2 = Blinker(led2, 0.1, 20)
        running1 = True
        running2 = True
        while running1 or running2:
            running1 = blinker1.blink()
            running2 = blinker2.blink()
        print("done")


main()
