# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from . import Animation


class Static(Animation):
    def show(self, message):
        """Show the message at its current position.

        :param message: The message to show.
        :type message: Message
        """
        x, y = self._position
        self._draw(message, x, y)

    def hide(self, message):
        """Hide the message at its current position.

        :param message: The message to hide.
        :type message: Message
        """
        x, y = self._position
        self._draw(message, x, y, opacity=0)

    def blink(self, message, count=3, duration=1):
        """Blink the foreground on and off a centain number of
        times over a certain period of time.

        :param message: The message to animate.
        :param float count: (optional) The number of times to blink. (default=3)
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :type message: Message
        """
        delay = duration / count / 2
        for _ in range(count):
            start_time = time.monotonic()
            self.hide(message)
            start_time = self._wait(start_time, delay)
            self.show(message)
            self._wait(start_time, delay)

    def flash(self, message, count=3, duration=1):
        """Fade the foreground in and out a centain number of
        times over a certain period of time.

        :param message: The message to animate.
        :param float count: (optional) The number of times to flash. (default=3)
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :type message: Message
        """
        delay = duration / count / 2
        steps = 50 // count
        for _ in range(count):
            self.fade_out(message, duration=delay, steps=steps)
            self.fade_in(message, duration=delay, steps=steps)

    def fade_in(self, message, duration=1, steps=50):
        """Fade the foreground in over a certain period of time
        by a certain number of steps. More steps is smoother, but too high
        of a number may slow down the animation too much.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :param float steps: (optional) The number of steps to perform the animation. (default=50)
        :type message: Message
        """
        current_x = int(self._display.width / 2 - message.buffer.width / 2)
        current_y = int(self._display.height / 2 - message.buffer.height / 2)
        delay = duration / (steps + 1)
        for opacity in range(steps + 1):
            start_time = time.monotonic()
            self._draw(message, current_x, current_y, opacity=opacity / steps)
            self._wait(start_time, delay)

    def fade_out(self, message, duration=1, steps=50):
        """Fade the foreground out over a certain period of time
        by a certain number of steps. More steps is smoother, but too high
        of a number may slow down the animation too much.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :param float steps: (optional) The number of steps to perform the animation. (default=50)
        :type message: Message
        """
        delay = duration / (steps + 1)
        for opacity in range(steps + 1):
            start_time = time.monotonic()
            self._draw(
                message,
                self._position[0],
                self._position[1],
                opacity=(steps - opacity) / steps,
            )
            self._wait(start_time, delay)
