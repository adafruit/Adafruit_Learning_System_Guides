# Write your code here :-)
# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from . import Animation


class Scroll(Animation):
    def scroll_from_to(self, message, duration, start_x, start_y, end_x, end_y):
        """
        Scroll the message from one position to another over a certain period of
        time.

        :param message: The message to animate.
        :param float duration: The period of time to perform the animation over in seconds.
        :param int start_x: The Starting X Position
        :param int start_yx: The Starting Y Position
        :param int end_x: The Ending X Position
        :param int end_y: The Ending Y Position
        :type message: Message
        """
        steps = max(abs(end_x - start_x), abs(end_y - start_y))
        if not steps:
            return
        increment_x = (end_x - start_x) / steps
        increment_y = (end_y - start_y) / steps
        for i in range(steps + 1):
            start_time = time.monotonic()
            current_x = start_x + round(i * increment_x)
            current_y = start_y + round(i * increment_y)
            self._draw(message, current_x, current_y)
            if i <= steps:
                self._wait(start_time, duration / steps)

    def out_to_left(self, message, duration=1):
        """Scroll a message off the display from its current position towards the left
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                                over in seconds. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        self.scroll_from_to(
            message, duration, current_x, current_y, 0 - message.buffer.width, current_y
        )

    def in_from_left(self, message, duration=1, x=0):
        """Scroll a message in from the left side of the display over a certain period of
        time. The final position is centered.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :param int x: (optional) The amount of x-offset from the center position (default=0)
        :type message: Message
        """
        center_x, center_y = self._get_centered_position(message)
        self.scroll_from_to(
            message,
            duration,
            0 - message.buffer.width,
            center_y,
            center_x + x,
            center_y,
        )

    def in_from_right(self, message, duration=1, x=0):
        """Scroll a message in from the right side of the display over a certain period of
        time. The final position is centered.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :param int x: (optional) The amount of x-offset from the center position (default=0)
        :type message: Message
        """
        center_x, center_y = self._get_centered_position(message)
        self.scroll_from_to(
            message, duration, self._display.width - 1, center_y, center_x + x, center_y
        )

    def in_from_top(self, message, duration=1, y=0):
        """Scroll a message in from the top side of the display over a certain period of
        time. The final position is centered.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :param int y: (optional) The amount of y-offset from the center position (default=0)
        :type message: Message
        """
        center_x, center_y = self._get_centered_position(message)
        self.scroll_from_to(
            message,
            duration,
            center_x,
            0 - message.buffer.height,
            center_x,
            center_y + y,
        )

    def in_from_bottom(self, message, duration=1, y=0):
        """Scroll a message in from the bottom side of the display over a certain period of
        time. The final position is centered.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :param int y: (optional) The amount of y-offset from the center position (default=0)
        :type message: Message
        """
        center_x, center_y = self._get_centered_position(message)
        self.scroll_from_to(
            message,
            duration,
            center_x,
            self._display.height - 1,
            center_x,
            center_y + y,
        )

    def out_to_right(self, message, duration=1):
        """Scroll a message off the display from its current position towards the right
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        self.scroll_from_to(
            message, duration, current_x, current_y, self._display.width - 1, current_y
        )

    def out_to_top(self, message, duration=1):
        """Scroll a message off the display from its current position towards the top
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        self.scroll_from_to(
            message,
            duration,
            current_x,
            current_y,
            current_x,
            0 - message.buffer.height,
        )

    def out_to_bottom(self, message, duration=1):
        """Scroll a message off the display from its current position towards the bottom
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        self.scroll_from_to(
            message, duration, current_x, current_y, current_x, self._display.height - 1
        )

    def right_to_left(self, message, duration=1):
        """Scroll a message in from the right side of the display and then out the left side over a certain period of
        time. The final position is off-screen to the left.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over in seconds. (default=1)
        :type message: Message
        """
        center_x, center_y = self._get_centered_position(message)
        self.scroll_from_to(
            message, duration,
            self._display.width - 1, center_y,
            - message.buffer.width, center_y
        )
