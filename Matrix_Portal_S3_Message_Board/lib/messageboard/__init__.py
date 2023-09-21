# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import bitmaptools
import displayio
import adafruit_imageload
from .doublebuffer import DoubleBuffer
from .message import Message


class MessageBoard:
    def __init__(self, matrix):
        self.fonts = {}
        self.display = matrix.display
        self._buffer_width = self.display.width * 2
        self._buffer_height = self.display.height * 2
        self._dbl_buf = DoubleBuffer(
            self.display, self._buffer_width, self._buffer_height
        )
        self._background = None
        self.set_background()  # Set to black
        self._position = (0, 0)

    def set_background(self, file_or_color=0x000000):
        """The background image to a bitmap file."""
        if isinstance(file_or_color, str):  # its a filenme:
            background, bg_shader = adafruit_imageload.load(file_or_color)
            self._dbl_buf.shader = bg_shader
            self._background = background
        elif isinstance(file_or_color, int):
            # Make a background color fill
            bg_shader = displayio.ColorConverter(
                input_colorspace=displayio.Colorspace.RGB565
            )
            background = displayio.Bitmap(
                self.display.width, self.display.height, 65535
            )
            background.fill(displayio.ColorConverter().convert(file_or_color))
            self._dbl_buf.shader = bg_shader
            self._background = background
        else:
            raise RuntimeError("Unknown type of background")

    def animate(self, message, animation_class, animation_function, **kwargs):
        anim_class = __import__(
            f"{self.__module__}.animations.{animation_class.lower()}"
        )
        anim_class = getattr(anim_class, "animations")
        anim_class = getattr(anim_class, animation_class.lower())
        anim_class = getattr(anim_class, animation_class)
        animation = anim_class(
            self.display, self._draw, self._position
        )  # Instantiate the class
        # Call the animation function and pass kwargs along with the message (positional)
        anim_func = getattr(animation, animation_function)
        anim_func(message, **kwargs)

    def set_message_position(self, x, y):
        """Set the position of the message on the display"""
        self._position = (x, y)

    def _draw(
        self,
        image,
        x,
        y,
        opacity=None,
        mask_color=0xFF00FF,
        blendmode=bitmaptools.BlendMode.Normal,
        post_draw_position=None,
    ):
        """Draws a message to the buffer taking its current settings into account.
        It also sets the current position and performs a swap.
        """
        self._position = (x, y)
        buffer_x_offset = self._buffer_width - self.display.width
        buffer_y_offset = self._buffer_height - self.display.height

        # Image can be a message in which case its properties will be used
        if isinstance(image, Message):
            if opacity is None:
                opacity = image.opacity
            mask_color = image.mask_color
            blendmode = image.blendmode
            image = image.buffer
        if opacity is None:
            opacity = 1.0

        if mask_color > 65535:
            mask_color = displayio.ColorConverter().convert(mask_color)

        # Blit the background
        bitmaptools.blit(
            self._dbl_buf.active_buffer,
            self._background,
            buffer_x_offset,
            buffer_y_offset,
        )

        # If the image is wider than the display buffer, we need to shrink it
        if x + buffer_x_offset < 0:
            new_image = displayio.Bitmap(
                image.width - self.display.width, image.height, 65535
            )
            bitmaptools.blit(
                new_image,
                image,
                0,
                0,
                x1=self.display.width,
                y1=0,
                x2=image.width,
                y2=image.height,
            )
            x += self.display.width
            image = new_image

        # If the image is taller than the display buffer, we need to shrink it
        if y + buffer_y_offset < 0:
            new_image = displayio.Bitmap(
                image.width, image.height - self.display.height, 65535
            )
            bitmaptools.blit(
                new_image,
                image,
                0,
                0,
                x1=0,
                y1=self.display.height,
                x2=image.width,
                y2=image.height,
            )
            y += self.display.height
            image = new_image

        # Clear the foreground buffer
        foreground_buffer = displayio.Bitmap(
            self._buffer_width, self._buffer_height, 65535
        )
        foreground_buffer.fill(mask_color)

        bitmaptools.blit(
            foreground_buffer, image, x + buffer_x_offset, y + buffer_y_offset
        )

        # Blend the foreground buffer into the main buffer
        bitmaptools.alphablend(
            self._dbl_buf.active_buffer,
            self._dbl_buf.active_buffer,
            foreground_buffer,
            displayio.Colorspace.RGB565,
            1.0,
            opacity,
            blendmode=blendmode,
            skip_source2_index=mask_color,
        )
        self._dbl_buf.show()

        # Allow for an override of the position after drawing (needed for split effects)
        if post_draw_position is not None and isinstance(post_draw_position, tuple):
            self._position = post_draw_position
