# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Adapted From `adafruit_led_animation.animation.rainbow`
"""

from adafruit_led_animation.animation import Animation
from adafruit_led_animation.color import colorwheel
from adafruit_led_animation import MS_PER_SECOND, monotonic_ms


class RainbowSweepAnimation(Animation):
    """
    The classic rainbow color wheel that gets swept across by another specified color.

    :param pixel_object: The initialised LED object.
    :param float speed: Animation refresh rate in seconds, e.g. ``0.1``.
    :param float sweep_speed: How long in seconds to wait between sweep steps
    :param float period: Period to cycle the rainbow over in seconds.  Default 1.
    :param sweep_direction: which way to sweep across the rainbow. Must be one of
      DIRECTION_START_TO_END or DIRECTION_END_TO_START
    :param str name: Name of animation (optional, useful for sequences and debugging).

    """

    # constants to represent the different directions
    DIRECTION_START_TO_END = 0
    DIRECTION_END_TO_START = 1
    # pylint: disable=too-many-arguments
    def __init__(
        self, pixel_object, speed, color, sweep_speed=0.3, period=1,
            name=None, sweep_direction=DIRECTION_START_TO_END
    ):
        super().__init__(pixel_object, speed, color, name=name)
        self._period = period
        # internal var step used inside of color generator
        self._step = 256 // len(pixel_object)

        # internal var wheel_index used inside of color generator
        self._wheel_index = 0

        # instance of the generator
        self._generator = self._color_wheel_generator()

        # convert swap speed from seconds to ms and store it
        self._sweep_speed = sweep_speed * 1000

        # set the initial sweep index
        self.sweep_index = len(pixel_object)

        # internal variable to store the timestamp of when a sweep step occurs
        self._last_sweep_time = 0

        # store the direction argument
        self.direction = sweep_direction

    # this animation supports on cycle complete callbacks
    on_cycle_complete_supported = True

    def _color_wheel_generator(self):
        # convert period to ms
        period = int(self._period * MS_PER_SECOND)

        # how many pixels in the strand
        num_pixels = len(self.pixel_object)

        # current timestamp
        last_update = monotonic_ms()

        cycle_position = 0
        last_pos = 0
        while True:
            cycle_completed = False
            # time vars
            now = monotonic_ms()
            time_since_last_draw = now - last_update
            last_update = now

            # cycle position vars
            pos = cycle_position = (cycle_position + time_since_last_draw) % period

            # if it's time to signal cycle complete
            if pos < last_pos:
                cycle_completed = True

            # update position var for next iteration
            last_pos = pos

            # calculate wheel_index
            wheel_index = int((pos / period) * 256)

            # set all pixels to their color based on the wheel color and step
            self.pixel_object[:] = [
                colorwheel(((i * self._step) + wheel_index) % 255) for i in range(num_pixels)
            ]

            # if it's time for a sweep step
            if self._last_sweep_time + self._sweep_speed <= now:

                # udpate sweep timestamp
                self._last_sweep_time = now

                # decrement the sweep index
                self.sweep_index -= 1

                # if it's finished the last step
                if self.sweep_index == -1:
                    # reset it to the number of pixels in the strand
                    self.sweep_index = len(self.pixel_object)

            # if end to start direction
            if self.direction == self.DIRECTION_END_TO_START:
                # set the current pixels at the end of the strand to the specified color
                self.pixel_object[self.sweep_index:] = (
                        [self.color] * (len(self.pixel_object) - self.sweep_index))

            # if start to end direction
            elif self.direction == self.DIRECTION_START_TO_END:
                # set the pixels at the begining of the strand to the specified color
                inverse_index = len(self.pixel_object) - self.sweep_index
                self.pixel_object[:inverse_index] = [self.color] * (inverse_index)

            # update the wheel index
            self._wheel_index = wheel_index

            # signal cycle complete if it's time
            if cycle_completed:
                self.cycle_complete = True
            yield


    def draw(self):
        """
        draw the current frame of the animation
        :return:
        """
        next(self._generator)

    def reset(self):
        """
        Resets the animation.
        """
        self._generator = self._color_wheel_generator()
