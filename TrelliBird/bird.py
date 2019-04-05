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

import time
from color_names import *

class Bird(object):
    """The 'bird': the user's piece."""

    def __init__(self, weight=0.5):
        """Initialize a Bird instance.
        weight -- the weight of the bird (default 0.5)
        """
        self._position = 0.75
        self._weight = weight

    def _y_position(self):
        """Get the verical pixel position."""
        if self._position >= 0.75:
            return 0
        elif self._position >= 0.5:
            return 1
        elif self._position >= 0.25:
            return 2
        return 3

    def _move_up(self, amount):
        """Move the bird up.
        amount -- how much to move up, 0.0-1.0
        """
        self._position = min(1.0, self._position + amount)

    def _move_down(self, amount):
        """Move the bird down.
        amount -- how much to move down, 0.0-1.0
        """
        self._position = max(0.0, self._position - amount)

    def flap(self):
        """Flap. This moves the bird up by a fixed amount."""
        self._move_up(0.25)

    def update(self):
        """Periodic update: add the effect of gravity."""
        self._move_down(0.05 * self._weight)

    def did_hit_ground(self):
        """Return whether this bird hit the ground."""
        return self._position == 0.0

    def is_colliding_with(self, post):
        """Check for a collision.
        post -- the Post instance to check for a collicion with
        """
        return post.is_collision_at(3, self._y_position())

    def draw_on(self, trellis, color=YELLOW):
        """Draw the bird.
        trellis -- the TrellisM4Express instance to use as a screen
        color   -- the color to display as (default YELLOW)
        """
        trellis.pixels[3, self._y_position()] = color

    def flash(self, trellis):
        """Flash between RED and YELLOW to indicate a collision.
        trellis -- the TrellisM4Express instance to use as a screen """
        for _ in range(5):
            time.sleep(0.1)
            self.draw_on(trellis, RED)
            trellis.pixels.show()
            time.sleep(0.1)
            self.draw_on(trellis, YELLOW)
            trellis.pixels.show()
