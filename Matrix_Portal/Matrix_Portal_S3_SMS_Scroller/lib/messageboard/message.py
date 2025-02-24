# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import bitmaptools
import displayio
import adafruit_imageload
from adafruit_display_text import bitmap_label


class Message:
    def __init__(
        self,
        font,
        opacity=1.0,
        mask_color=0xFF00FF,
        blendmode=bitmaptools.BlendMode.Normal,
    ):
        self._current_font = font
        self._current_color = 0xFF0000
        self._buffer = displayio.Bitmap(0, 0, 65535)
        self._cursor = [0, 0]
        self.opacity = opacity
        self._blendmode = blendmode
        self._mask_color = 0
        self.mask_color = mask_color
        self._width = 0
        self._height = 0

    def _enlarge_buffer(self, width, height):
        """Resize the message buffer to grow as necessary"""
        new_width = self._width
        if self._cursor[0] + width >= self._width:
            new_width = self._cursor[0] + width

        new_height = self._height
        if self._cursor[1] + height >= self._height:
            new_height = self._cursor[1] + height

        if new_width > self._width or new_height > self._height:
            new_buffer = displayio.Bitmap(new_width, new_height, 65535)
            if self._mask_color is not None:
                bitmaptools.fill_region(
                    new_buffer, 0, 0, new_width, new_height, self._mask_color
                )
            bitmaptools.blit(new_buffer, self._buffer, 0, 0)
            self._buffer = new_buffer
            self._width = new_width
            self._height = new_height

    def _add_bitmap(self, bitmap, x_offset=0, y_offset=0):
        new_width, new_height = (
            self._cursor[0] + bitmap.width + x_offset,
            self._cursor[1] + bitmap.height + y_offset,
        )
        # Resize the buffer if necessary
        self._enlarge_buffer(new_width, new_height)
        # Blit the image into the buffer
        source_left, source_top = 0, 0
        if self._cursor[0] + x_offset < 0:
            source_left = 0 - (self._cursor[0] + x_offset)
            x_offset = 0
        if self._cursor[1] + y_offset < 0:
            source_top = 0 - (self._cursor[1] + y_offset)
            y_offset = 0
        bitmaptools.blit(
            self._buffer,
            bitmap,
            self._cursor[0] + x_offset,
            self._cursor[1] + y_offset,
            x1=source_left,
            y1=source_top,
        )
        # Move the cursor
        self._cursor[0] += bitmap.width + x_offset

    def add_text(
        self,
        text,
        color=None,
        font=None,
        x_offset=0,
        y_offset=0,
    ):
        if font is None:
            font = self._current_font
        if color is None:
            color = self._current_color
        color_565value = displayio.ColorConverter().convert(color)
        # Create a bitmap label and add it to the buffer
        bmp_label = bitmap_label.Label(font, text=text)
        color_overlay = displayio.Bitmap(
            bmp_label.bitmap.width, bmp_label.bitmap.height, 65535
        )
        color_overlay.fill(color_565value)
        mask_overlay = displayio.Bitmap(
            bmp_label.bitmap.width, bmp_label.bitmap.height, 65535
        )
        mask_overlay.fill(self._mask_color)
        bitmaptools.blit(color_overlay, bmp_label.bitmap, 0, 0, skip_source_index=1)
        bitmaptools.blit(
            color_overlay, mask_overlay, 0, 0, skip_dest_index=color_565value
        )
        bmp_label = None

        self._add_bitmap(color_overlay, x_offset, y_offset)

    def add_image(self, image, x_offset=0, y_offset=0):
        # Load the image with imageload and add it to the buffer
        bmp_image, _ = adafruit_imageload.load(image)
        self._add_bitmap(bmp_image, x_offset, y_offset)

    def clear(self):
        """Clear the canvas content, but retain all of the style settings"""
        self._buffer = displayio.Bitmap(0, 0, 65535)
        self._cursor = [0, 0]
        self._width = 0
        self._height = 0

    @property
    def buffer(self):
        """Return the current buffer"""
        if self._width == 0 or self._height == 0:
            raise RuntimeError("No content in the message")
        return self._buffer

    @property
    def mask_color(self):
        """Get or Set the mask color"""
        return self._mask_color

    @mask_color.setter
    def mask_color(self, value):
        self._mask_color = displayio.ColorConverter().convert(value)

    @property
    def blendmode(self):
        """Get or Set the blendmode"""
        return self._blendmode

    @blendmode.setter
    def blendmode(self, value):
        if value in bitmaptools.BlendMode:
            self._blendmode = value
