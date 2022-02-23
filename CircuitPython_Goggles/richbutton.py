# SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=import-error, too-many-instance-attributes, too-few-public-methods

"""Glorified button class with debounced tap, double-tap, hold and release"""

from time import monotonic
from digitalio import DigitalInOut, Direction, Pull

class RichButton:
    """
    A button class handling more than basic taps: adds debounced tap,
    double-tap, hold and release.
    """

    TAP = 0
    DOUBLE_TAP = 1
    HOLD = 2
    RELEASE = 3

    def __init__(self, pin, *, debounce_period=0.05, hold_period=0.75,
                 double_tap_period=0.3):
        """
        Constructor for RichButton class.

        Arguments:
            pin (int)                : Digital pin connected to button
                                       (opposite leg to GND). Pin will be
                                       configured as INPUT with pullup.
        Keyword arguments:
            debounce_period (float)  : interval, in seconds, in which multiple
                                       presses are ignored (debounced)
                                       (default = 0.05 seconds).
            hold_period (float)      : interval, in seconds, when a held
                                       button will return a HOLD value from
                                       the action() function (default = 0.75).
            double_tap_period (float): interval, in seconds, when a double-
                                       tap can be sensed (vs returning
                                       a second single-tap) (default = 0.3).
                                       Longer double-tap periods will make
                                       single-taps less responsive.
        """
        self.in_out = DigitalInOut(pin)
        self.in_out.direction = Direction.INPUT
        self.in_out.pull = Pull.UP
        self._debounce_period = debounce_period
        self._hold_period = hold_period
        self._double_tap_period = double_tap_period
        self._holding = False
        self._tap_time = -self._double_tap_period
        self._press_time = monotonic()
        self._prior_state = self.in_out.value

    def action(self):
        """
        Process pin input. This MUST be called frequently for debounce, etc.
        to work, since interrupts are not available.
        Returns:
            None, TAP, DOUBLE_TAP, HOLD or RELEASE.
        """
        new_state = self.in_out.value
        if new_state != self._prior_state:
            # Button state changed since last call
            self._prior_state = new_state
            if not new_state:
                # Button initially pressed (TAP not returned until debounce)
                self._press_time = monotonic()
            else:
                # Button initially released
                if self._holding:
                    # Button released after hold
                    self._holding = False
                    return self.RELEASE
                if (monotonic() - self._press_time) >= self._debounce_period:
                    # Button released after valid debounce time
                    if monotonic() - self._tap_time < self._double_tap_period:
                        # Followed another recent tap, reset double timer
                        self._tap_time = 0
                        return self.DOUBLE_TAP
                    # Else regular debounced release, maybe 1st tap, keep time
                    self._tap_time = monotonic()
        else:
            # Button is in same state as last call
            if self._prior_state:
                # Is not pressed
                if (self._tap_time > 0 and
                        (monotonic() - self._tap_time) > self._double_tap_period):
                    # Enough time since last tap that it's not a double
                    self._tap_time = 0
                    return self.TAP
            elif (not self._holding and
                  (monotonic() - self._press_time) >= self._hold_period):
                # Is pressed, and has been for the holding period
                self._holding = True
                return self.HOLD
        return None
