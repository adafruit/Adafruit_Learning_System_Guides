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
import random
import math
from bird import Bird
from post import Post
from color_names import *

BLACK = 0x000000

class Game(object):
    """Overall game control."""

    def __init__(self, trellis, accel, ramp=20, challenge_ramp=30):
        """initialize a Game instance.
        trellis        -- the TrellisM4Express instance to use as input and screen.
        accel          -- the accelerometer interface object to use as input
        ramp           -- how often (in steps) to increase the speed (default 20)
        challenge_ramp -- how often (in steps) to increase the challenge of the posts
        """
        self._trellis = trellis
        self._accel = accel
        self._delay_ramp = ramp
        self._challenge_ramp = challenge_ramp
        self._bird = Bird()
        self._posts = []
        self._interstitial_delay = 1.0
        self._challenge = 10
        self._currently_pressed = set([])
        self._previous_accel_reading = (None, None, None)
        self._previous_shake_result = False

    def _restart(self):
        """Restart the game."""
        self._bird = Bird()
        self._posts = []
        self._interstitial_delay = 0.5
        self._challenge = 10

    def _update(self):
        """Perform a periodic update: move the posts and remove any that go off the screen."""
        for post in self._posts:
            post.update()
        if self._posts and self._posts[0].off_screen:
            self._posts.pop(0)

    def _shaken(self):
        """Return whether the Trellis is shaken."""
        last_result = self._previous_shake_result
        result = False
        x, y, z = self._accel.acceleration
        if self._previous_accel_reading[0] is not None:
            result = math.fabs(self._previous_accel_reading[2] - z) > 4.0
        self._previous_accel_reading = (x, y, z)
        self._previous_shake_result = result
        return result and not last_result

    def _key_pressed(self):
        """Return whether a key was pressed since last time."""
        pressed = set(self._trellis.pressed_keys)
        key_just_pressed = len(pressed - self._currently_pressed) > 0
        self._currently_pressed = pressed
        return key_just_pressed

    def _should_flap(self, mode):
        """Return whether the user wants the bird to flap.
        mode -- input mode: False is key, True is accel
        """
        if mode:
            return self._shaken()
        return self._key_pressed()

    def _update_bird(self, mode):
        """Update the vertical position of the bird based on user activity and gravity.
        mode -- input mode: False is key, True is accel
        """
        self._bird.draw_on(self._trellis, BLACK)
        if self._should_flap(mode):
            self._bird.flap()
        else:
            self._bird.update()
        self._bird.draw_on(self._trellis)
        self._trellis.pixels.show()

    def _check_for_collision(self):
        """Return whether this bird has collided with a post."""
        collided = self._bird.did_hit_ground()
        for post in self._posts:
            collided |= self._bird.is_colliding_with(post)
        return collided

    def _update_display(self):
        """Update the screen."""
        self._trellis.pixels.fill(BLACK)
        for post in self._posts:
            post.draw_on(self._trellis)
        self._bird.draw_on(self._trellis)
        self._trellis.pixels.show()

    def _new_post(self):
        """Return a new post based on the current challenge level"""
        bottom_blocks = random.randint(1, 3)
        top_blocks = random.randint(1, 2)
        # bottom post
        if self._challenge > 6:
            return Post(from_bottom=bottom_blocks)
        # top possible as well
        if self._challenge > 3:
            if random.randint(1, 2) == 1:
                return Post(from_bottom=bottom_blocks)
            return Post(from_top=top_blocks)
        # top, bottom, and both possible
        r = random.randint(1, 3)
        if r == 1:
            return Post(from_bottom=bottom_blocks)
        if r == 2:
            return Post(from_top=top_blocks)
        return Post(from_bottom=bottom_blocks, from_top=random.randint(1, 4 - bottom_blocks))

    def _add_post(self):
        """Add a post."""
        self._posts.append(self._new_post())

    def play(self, mode=False):
        """Play the game.
        mode -- input mode: False is key, True is accel
        """
        self._restart()
        collided = False
        count = 0
        last_tick = 0
        while not collided:
            now = time.monotonic()
            self._update_bird(mode)
            if now >= last_tick + self._interstitial_delay:
                last_tick = now
                count += 1
                self._update()
                collided = self._check_for_collision()
                if count % max(1, (self._challenge - random.randint(0, 4))) == 0:
                    self._add_post()
                self._update_display()
                # handle collision or wait and repeat
                if collided:
                    self._bird.flash(self._trellis)
                else:
                    # time to speed up?
                    if count % self._delay_ramp == 0:
                        self._interstitial_delay -= 0.01
                    # time to increase challenge of the posts?
                    if self._challenge > 0 and count % self._challenge_ramp == 0:
                        self._challenge -= 1
            time.sleep(0.05)
