# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
SweepAnimation helper class
"""
from adafruit_led_animation.animation import Animation


class SweepAnimation(Animation):

    def __init__(self, pixel_object, speed, color):
        """
        Sweeps across the strand lighting up one pixel at a time.
        Once the full strand is lit, sweeps across again turning off
        each pixel one at a time.

        :param pixel_object: The initialized pixel object
        :param speed: The speed to run the animation
        :param color: The color the pixels will be lit up.
        """

        # Call super class initialization
        super().__init__(pixel_object, speed, color)

        # custom variable to store the current step of the animation
        self.current_step = 0

        # one step per pixel
        self.last_step = len(pixel_object)

        # boolean indicating whether we're currently sweeping LEDs on or off
        self.sweeping_on = True

    # This animation supports the cycle complete callback
    on_cycle_complete_supported = True

    def draw(self):
        """
        Display the current frame of the animation

        :return: None
        """
        if self.sweeping_on:
            # Turn on the next LED
            self.pixel_object[self.current_step] = self.color
        else:  # sweeping off
            # Turn off the next LED
            self.pixel_object[self.current_step] = 0x000000

        # increment the current step variable
        self.current_step += 1

        # if we've reached the last step
        if self.current_step >= self.last_step:

            # if we are currently sweeping off
            if not self.sweeping_on:
                # signal that the cycle is complete
                self.cycle_complete = True

            # reset the step variable to 0
            self.current_step = 0

            # flop sweeping on/off indicator variable
            self.sweeping_on = not self.sweeping_on
