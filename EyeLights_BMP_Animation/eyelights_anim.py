# SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
EyeLightsAnim provides EyeLights LED glasses with pre-drawn frame-by-frame
animation from BMP images. Sort of a catch-all for modest projects that may
want to implement some animation without having to express that animation
entirely in code. The idea is based upon two prior projects:

https://learn.adafruit.com/32x32-square-pixel-display/overview
learn.adafruit.com/circuit-playground-neoanim-using-bitmaps-to-animate-neopixels

The 18x5 matrix and the LED rings are regarded as distinct things, fed from
two separate BMPs (or can use just one or the other). The former guide above
uses the vertical axis for time (like a strip of movie film), while the
latter uses the horizontal axis for time (as in audio or video editing).
Despite this contrast, the same conventions are maintained here to avoid
conflicting explanations...what worked in those guides is what works here,
only the resolutions are different."""

import displayio
import adafruit_imageload


def gamma_adjust(palette):
    """Given a color palette that was returned by adafruit_imageload, apply
    gamma correction and place results back in original palette. This makes
    LED brightness and colors more perceptually linear, to better match how
    the source BMP might've appeared on screen."""

    for index, entry in enumerate(palette):
        palette[index] = sum(
            [
                int(((((entry >> shift) & 0xFF) / 255) ** 2.6) * 255 + 0.5) << shift
                for shift in range(16, -1, -8)
            ]
        )


class EyeLightsAnim:
    """Class encapsulating BMP image-based frame animation for the matrix
    and rings of an LED_Glasses object."""

    def __init__(self, glasses, matrix_filename, ring_filename, rings_on_top=True):
        """Constructor for EyeLightsAnim. Accepts an LED_Glasses object and
        filenames for two indexed-color BMP images: first is a "sprite
        sheet" for animating on the matrix portion of the glasses, second is
        a pixels-over-time graph for the rings portion. Either filename may
        be None if not used. Because the matrix and rings share some pixels
        in common, the last argument determines the "stacking order" - which
        of the two bitmaps is drawn later or "on top." Default of True
        places the rings over the matrix, False gives the matrix priority.
        It's possible to use transparent palette indices but that may be
        more trouble than it's worth."""

        self.glasses = glasses
        self.matrix_bitmap = self.ring_bitmap = None
        self.rings_on_top = rings_on_top

        if matrix_filename:
            self.matrix_bitmap, self.matrix_palette = adafruit_imageload.load(
                matrix_filename, bitmap=displayio.Bitmap, palette=displayio.Palette
            )
            if (self.matrix_bitmap.width < glasses.width) or (
                self.matrix_bitmap.height < glasses.height
            ):
                raise ValueError("Matrix bitmap must be at least 18x5 pixels")
            gamma_adjust(self.matrix_palette)
            self.tiles_across = self.matrix_bitmap.width // glasses.width
            self.tiles_down = self.matrix_bitmap.height // glasses.height
            self.matrix_frames = self.tiles_across * self.tiles_down
            self.matrix_frame = self.matrix_frames - 1

        if ring_filename:
            self.ring_bitmap, self.ring_palette = adafruit_imageload.load(
                ring_filename, bitmap=displayio.Bitmap, palette=displayio.Palette
            )
            if self.ring_bitmap.height < 48:
                raise ValueError("Ring bitmap must be at least 48 pixels tall")
            gamma_adjust(self.ring_palette)
            self.ring_frames = self.ring_bitmap.width
            self.ring_frame = self.ring_frames - 1

    def draw_matrix(self, matrix_frame=None):
        """Draw the matrix portion of EyeLights from one frame of the matrix
        bitmap "sprite sheet." Can either request a specific frame index
        (starting from 0), or pass None (or no arguments) to advance by one
        frame, "wrapping around" to beginning if needed. For internal use by
        library; user code should call frame(), not this function."""

        if matrix_frame:  # Go to specific frame
            self.matrix_frame = matrix_frame
        else:  # Advance one frame forward
            self.matrix_frame += 1
        self.matrix_frame %= self.matrix_frames  # Wrap to valid range

        xoffset = self.matrix_frame % self.tiles_across * self.glasses.width
        yoffset = self.matrix_frame // self.tiles_across * self.glasses.height

        for y in range(self.glasses.height):
            y1 = y + yoffset
            for x in range(self.glasses.width):
                idx = self.matrix_bitmap[x + xoffset, y1]
                if not self.matrix_palette.is_transparent(idx):
                    self.glasses.pixel(x, y, self.matrix_palette[idx])

    def draw_rings(self, ring_frame=None):
        """Draw the rings portion of EyeLights from one frame of the rings
        bitmap graph. Can either request a specific frame index (starting
        from 0), or pass None (or no arguments) to advance by one frame,
        'wrapping around' to beginning if needed. For internal use by
        library; user code should call frame(), not this function."""

        if ring_frame:  # Go to specific frame
            self.ring_frame = ring_frame
        else:  # Advance one frame forward
            self.ring_frame += 1
        self.ring_frame %= self.ring_frames  # Wrap to valid range

        for y in range(24):
            idx = self.ring_bitmap[self.ring_frame, y]
            if not self.ring_palette.is_transparent(idx):
                self.glasses.left_ring[y] = self.ring_palette[idx]
            idx = self.ring_bitmap[self.ring_frame, y + 24]
            if not self.ring_palette.is_transparent(idx):
                self.glasses.right_ring[y] = self.ring_palette[idx]

    def frame(self, matrix_frame=None, ring_frame=None):
        """Draw one frame of animation to the matrix and/or rings portions
        of EyeLights. Frame index (starting from 0) for matrix and rings
        respectively can be passed as arguments, or either/both may be None
        to advance by one frame, 'wrapping around' to beginning if needed.
        Because some pixels are shared in common between matrix and rings,
        the "stacking order" -- which of the two appears "on top", is
        specified as an argument to the constructor."""

        if self.matrix_bitmap and self.rings_on_top:
            self.draw_matrix(matrix_frame)

        if self.ring_bitmap:
            self.draw_rings(ring_frame)

        if self.matrix_bitmap and not self.rings_on_top:
            self.draw_matrix(matrix_frame)
