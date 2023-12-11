# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import displayio
import bitmaptools
from . import Animation


class Split(Animation):
    def out_horizontally(self, message, duration=0.5):
        """Show the effect of a message splitting horizontally
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=0.5)
        :type message: Message
        """
        current_x, current_y = self._position
        image = message.buffer
        left_image = displayio.Bitmap(image.width // 2, image.height, 65535)
        bitmaptools.blit(
            left_image, image, 0, 0, x1=0, y1=0, x2=image.width // 2, y2=image.height
        )

        right_image = displayio.Bitmap(image.width // 2, image.height, 65535)
        bitmaptools.blit(
            right_image,
            image,
            0,
            0,
            x1=image.width // 2,
            y1=0,
            x2=image.width,
            y2=image.height,
        )

        distance = self._display.width // 2
        for i in range(distance + 1):
            start_time = time.monotonic()
            effect_buffer = displayio.Bitmap(
                self._display.width + image.width, image.height, 65535
            )
            effect_buffer.fill(message.mask_color)
            bitmaptools.blit(effect_buffer, left_image, distance - i, 0)
            bitmaptools.blit(
                effect_buffer, right_image, distance + image.width // 2 + i, 0
            )

            self._draw(
                effect_buffer,
                current_x - self._display.width // 2,
                current_y,
                message.opacity,
                post_draw_position=(current_x - self._display.width // 2, current_y),
            )
            self._wait(start_time, duration / distance)

    def out_vertically(self, message, duration=0.5):
        """Show the effect of a message splitting vertically
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=0.5)
        :type message: Message
        """
        current_x, current_y = self._position
        image = message.buffer

        top_image = displayio.Bitmap(image.width, image.height // 2, 65535)
        bitmaptools.blit(
            top_image, image, 0, 0, x1=0, y1=0, x2=image.width, y2=image.height // 2
        )

        bottom_image = displayio.Bitmap(image.width, image.height // 2, 65535)
        bitmaptools.blit(
            bottom_image,
            image,
            0,
            0,
            x1=0,
            y1=image.height // 2,
            x2=image.width,
            y2=image.height,
        )

        distance = self._display.height // 2
        effect_buffer_width = self._display.width
        if current_x < 0:
            effect_buffer_width -= current_x
        for i in range(distance + 1):
            start_time = time.monotonic()
            effect_buffer = displayio.Bitmap(
                effect_buffer_width, self._display.height + image.height, 65535
            )
            effect_buffer.fill(message.mask_color)
            bitmaptools.blit(effect_buffer, top_image, 0, distance - i)
            bitmaptools.blit(
                effect_buffer, bottom_image, 0, distance + image.height // 2 + i + 1
            )

            self._draw(
                effect_buffer,
                current_x,
                current_y - self._display.height // 2,
                message.opacity,
                post_draw_position=(current_x, current_y - self._display.height // 2),
            )
            self._wait(start_time, duration / distance)

    def in_horizontally(self, message, duration=0.5):
        """Show the effect of a split message joining horizontally
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=0.5)
        :type message: Message
        """
        current_x = int(self._display.width / 2 - message.buffer.width / 2)
        current_y = int(self._display.height / 2 - message.buffer.height / 2)
        image = message.buffer
        left_image = displayio.Bitmap(image.width // 2, image.height, 65535)
        bitmaptools.blit(
            left_image, image, 0, 0, x1=0, y1=0, x2=image.width // 2, y2=image.height
        )

        right_image = displayio.Bitmap(image.width // 2, image.height, 65535)
        bitmaptools.blit(
            right_image,
            image,
            0,
            0,
            x1=image.width // 2,
            y1=0,
            x2=image.width,
            y2=image.height,
        )

        distance = self._display.width // 2
        effect_buffer = displayio.Bitmap(
            self._display.width + image.width, image.height, 65535
        )
        effect_buffer.fill(message.mask_color)
        for i in range(distance + 1):
            start_time = time.monotonic()
            bitmaptools.blit(effect_buffer, left_image, i, 0)
            bitmaptools.blit(
                effect_buffer,
                right_image,
                self._display.width + image.width // 2 - i + 1,
                0,
            )
            self._draw(
                effect_buffer,
                current_x - self._display.width // 2,
                current_y,
                message.opacity,
                post_draw_position=(current_x, current_y),
            )
            self._wait(start_time, duration / distance)

    def in_vertically(self, message, duration=0.5):
        """Show the effect of a split message joining vertically
        over a certain period of time.

        :param message: The message to animate.
        :param float duration: (optional) The period of time to perform the animation
                               over. (default=0.5)
        :type message: Message
        """
        current_x = int(self._display.width / 2 - message.buffer.width / 2)
        current_y = int(self._display.height / 2 - message.buffer.height / 2)

        image = message.buffer
        top_image = displayio.Bitmap(image.width, image.height // 2, 65535)
        bitmaptools.blit(
            top_image, image, 0, 0, x1=0, y1=0, x2=image.width, y2=image.height // 2
        )

        bottom_image = displayio.Bitmap(image.width, image.height // 2, 65535)
        bitmaptools.blit(
            bottom_image,
            image,
            0,
            0,
            x1=0,
            y1=image.height // 2,
            x2=image.width,
            y2=image.height,
        )

        distance = self._display.height // 2
        effect_buffer_width = self._display.width
        if current_x < 0:
            effect_buffer_width -= current_x

        effect_buffer = displayio.Bitmap(
            effect_buffer_width, self._display.height + image.height, 65535
        )
        effect_buffer.fill(message.mask_color)
        for i in range(distance + 1):
            start_time = time.monotonic()
            bitmaptools.blit(effect_buffer, top_image, 0, i + 1)
            bitmaptools.blit(
                effect_buffer,
                bottom_image,
                0,
                self._display.height + image.height // 2 - i + 1,
            )

            self._draw(
                effect_buffer,
                current_x,
                current_y - self._display.height // 2,
                message.opacity,
                post_draw_position=(current_x, current_y),
            )
            self._wait(start_time, duration / distance)
