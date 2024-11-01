# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
ZipperAnimation helper class
"""
from adafruit_led_animation.animation import Animation


class ZipperAnimation(Animation):

    def __init__(self, pixel_object, speed, color, alternate_color=None):
        """
        Lights up every other LED from each ends of the strand, passing each
        other in the middle and resulting in the full strand being lit at the
        end of the cycle.

        :param pixel_object: The initialized pixel object
        :param speed: The speed to run the animation
        :param color: The color the pixels will be lit up.
        """

        # Call super class initialization
        super().__init__(pixel_object, speed, color)

        # if alternate color is None then use single color
        if alternate_color is None:
            self.alternate_color = color
        else:
            self.alternate_color = alternate_color

        # custom variable to store the current step of the animation
        self.current_step = 0

        # We're lighting up every other LED, so we have half the strand
        # length in steps.
        self.last_step = len(pixel_object) // 2

        self.cycle_complete = False

    # This animation supports the cycle complete callback
    on_cycle_complete_supported = True

    def draw(self):
        """
        Display the current frame of the animation

        :return: None
        """

        # Use try/except to ignore indexes outside the strand
        try:
            # Turn on 1 even indexed pixel starting from the start of the strand
            self.pixel_object[self.current_step * 2] = self.color

            # Turn on 1 odd indexed pixel starting from the end of the strand
            self.pixel_object[-(self.current_step * 2) - 1] = self.alternate_color
        except IndexError:
            pass

        # increment the current step variable
        self.current_step += 1

        # if we've reached the last step
        if self.current_step > self.last_step:
            # signal that the cycle is complete
            self.cycle_complete = True

            # call internal reset() function
            self.reset()

    def reset(self):
        """
        Turns all the LEDs off and resets the current step variable to 0
        :return: None
        """
        # turn LEDs off
        self.pixel_object.fill(0x000000)

        # reset current step variable
        self.current_step = 0
