# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time


class Animation:
    def __init__(self, display, draw_callback, starting_position=(0, 0)):
        self._display = display
        self._position = starting_position
        self._draw = draw_callback

    @staticmethod
    def _wait(start_time, duration):
        """Uses time.monotonic() to wait from the start time for a specified duration"""
        while time.monotonic() < (start_time + duration):
            pass
        return time.monotonic()

    def _get_centered_position(self, message):
        return int(self._display.width / 2 - message.buffer.width / 2), int(
            self._display.height / 2 - message.buffer.height / 2
        )
