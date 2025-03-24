# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import displayio
import bitmaptools
from . import Animation


class Loop(Animation):
    def _create_loop_image(self, image, x_offset, y_offset, mask_color):
        """Attach a copy of an image by a certain offset so it can be looped."""
        if 0 < x_offset < self._display.width:
            x_offset = self._display.width
        if 0 < y_offset < self._display.height:
            y_offset = self._display.height

        loop_image = displayio.Bitmap(
            image.width + x_offset, image.height + y_offset, 65535
        )
        loop_image.fill(mask_color)
        bitmaptools.blit(loop_image, image, 0, 0)
        bitmaptools.blit(loop_image, image, x_offset, y_offset)

        return loop_image

    def left(self, message, duration=1, count=1):
        """Loop a message towards the left side of the display over a certain period of time by a
        certain number of times. The message will re-enter from the right and end up back a the
        starting position.

        :param message: The message to animate.
        :param float count: (optional) The number of times to loop. (default=1)
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        distance = max(message.buffer.width, self._display.width)
        loop_image = self._create_loop_image(
            message.buffer, distance, 0, message.mask_color
        )
        for _ in range(count):
            for _ in range(distance):
                start_time = time.monotonic()
                current_x -= 1
                if current_x < 0 - message.buffer.width:
                    current_x += distance
                self._draw(
                    loop_image,
                    current_x,
                    current_y,
                    message.opacity,
                )
                self._wait(start_time, duration / distance / count)

    def right(self, message, duration=1, count=1):
        """Loop a message towards the right side of the display over a certain period of time by a
        certain number of times. The message will re-enter from the left and end up back a the
        starting position.

        :param message: The message to animate.
        :param float count: (optional) The number of times to loop. (default=1)
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        distance = max(message.buffer.width, self._display.width)
        loop_image = self._create_loop_image(
            message.buffer, distance, 0, message.mask_color
        )
        for _ in range(count):
            for _ in range(distance):
                start_time = time.monotonic()
                current_x += 1
                if current_x > 0:
                    current_x -= distance
                self._draw(
                    loop_image,
                    current_x,
                    current_y,
                    message.opacity,
                )
                self._wait(start_time, duration / distance / count)

    def up(self, message, duration=0.5, count=1):
        """Loop a message towards the top side of the display over a certain period of time by a
        certain number of times. The message will re-enter from the bottom and end up back a the
        starting position.

        :param message: The message to animate.
        :param float count: (optional) The number of times to loop. (default=1)
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        distance = max(message.buffer.height, self._display.height)
        loop_image = self._create_loop_image(
            message.buffer, 0, distance, message.mask_color
        )
        for _ in range(count):
            for _ in range(distance):
                start_time = time.monotonic()
                current_y -= 1
                if current_y < 0 - message.buffer.height:
                    current_y += distance
                self._draw(
                    loop_image,
                    current_x,
                    current_y,
                    message.opacity,
                )
                self._wait(start_time, duration / distance / count)

    def down(self, message, duration=0.5, count=1):
        """Loop a message towards the bottom side of the display over a certain period of time by a
        certain number of times. The message will re-enter from the top and end up back a the
        starting position.

        :param message: The message to animate.
        :param float count: (optional) The number of times to loop. (default=1)
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=1)
        :type message: Message
        """
        current_x, current_y = self._position
        distance = max(message.buffer.height, self._display.height)
        loop_image = self._create_loop_image(
            message.buffer, 0, distance, message.mask_color
        )
        for _ in range(count):
            for _ in range(distance):
                start_time = time.monotonic()
                current_y += 1
                if current_y > 0:
                    current_y -= distance
                self._draw(
                    loop_image,
                    current_x,
                    current_y,
                    message.opacity,
                )
                self._wait(start_time, duration / distance / count)
