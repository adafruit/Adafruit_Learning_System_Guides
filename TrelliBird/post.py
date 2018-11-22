"""
FlappyBird type game for the NeoTrellisM4

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=wildcard-import,unused-wildcard-import,eval-used

from color_names import *


class Post(object):
    """Obstacles the user must avoice colliding with."""

    def __init__(self, from_bottom=0, from_top=0):
        """Initialize a Post instance.
        from_bottom -- how far the post extends from the bottom of the screen (default 0)
        from_top    -- how far the post extends from the top of the screen (default 0)
        """
        self._x = 7
        self._top = from_top
        self._bottom = from_bottom

    def update(self):
        """Periodic update: move one step to the left."""
        self._x -= 1

    def _on_post(self, x, y):
        """Determine whether the supplied coordinate is occupied by part of this post.
        x -- the horizontal pixel coordinate
        y -- the vertical pixel coordinate
        """
        return x == self._x and (y < self._top or y > (3 - self._bottom))

    def draw_on(self, trellis):
        """Draw this post on the screen.
        trellis -- the TrellisM4Express instance to use as a screen
        """
        for i in range(4):
            if self._on_post(self._x, i):
                trellis.pixels[self._x, i] = GREEN

    def is_collision_at(self, x, y):
        """Determine whether something at the supplied coordinate is colliding with this post.
        x -- the horizontal pixel coordinate
        y -- the vertical pixel coordinate
        """
        return self._on_post(x, y)

    @property
    def off_screen(self):
        """Return whether this post has moved off the left edge of the screen."""
        return self._x < 0
