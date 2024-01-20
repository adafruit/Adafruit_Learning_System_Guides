# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import displayio


class DoubleBuffer:
    def __init__(self, display, width, height, shader=None, bit_depth=16):
        self._buffer_group = (displayio.Group(), displayio.Group())
        self._buffer = (
            displayio.Bitmap(width, height, 2**bit_depth - 1),
            displayio.Bitmap(width, height, 2**bit_depth - 1),
        )
        self._x_offset = display.width - width
        self._y_offset = display.height - height
        self.display = display
        self._active_buffer = 0  # The buffer we are updating

        if shader is None:
            shader = displayio.ColorConverter()

        buffer0_sprite = displayio.TileGrid(
            self._buffer[0],
            pixel_shader=shader,
            x=self._x_offset,
            y=self._y_offset,
        )
        self._buffer_group[0].append(buffer0_sprite)

        buffer1_sprite = displayio.TileGrid(
            self._buffer[1],
            pixel_shader=shader,
            x=self._x_offset,
            y=self._y_offset,
        )
        self._buffer_group[1].append(buffer1_sprite)

    def show(self, swap=True):
        self.display.root_group = self._buffer_group[self._active_buffer]
        if swap:
            self.swap()

    def swap(self):
        self._active_buffer = 0 if self._active_buffer else 1

    @property
    def active_buffer(self):
        return self._buffer[self._active_buffer]

    @property
    def shader(self):
        return self._buffer_group[0][0].pixel_shader

    @shader.setter
    def shader(self, shader):
        self._buffer_group[0][0].pixel_shader = shader
        self._buffer_group[1][0].pixel_shader = shader
