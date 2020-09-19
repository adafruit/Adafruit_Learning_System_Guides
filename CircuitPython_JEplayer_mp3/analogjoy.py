# The MIT License (MIT)
#
# Copyright (c) 2020 Jeff Epler for Adafruit Industries LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Convert an analog joystick to digital
"""

import analogio
import board

class AnalogJoystick:
    """Convert an analog joystick to digital"""
    def __init__(self, pin_x=None, pin_y=None, x_invert=False, y_invert=True, deadzone=8000):
        self._x = analogio.AnalogIn(pin_x or board.JOYSTICK_X)
        self._y = analogio.AnalogIn(pin_y or board.JOYSTICK_Y)
        self.x_invert = x_invert
        self.y_invert = y_invert
        self.deadzone = deadzone
        self.recenter()
        self.poll()

    def poll(self):
        """Read the analog values and update the digital outputs"""
        self.x = (self._x.value - self.x_center) * (-1 if self.x_invert else 1)
        self.y = (self._y.value - self.y_center) * (-1 if self.y_invert else 1)
        return [self.up, self.down, self.left, self.right]

    # pylint: disable=invalid-name
    @property
    def up(self):
        """Return true when the stick was pressed up at the last poll"""
        return self.y > self.deadzone
    # pylint: enable=invalid-name

    @property
    def down(self):
        """Return true when the stick was pressed down at the last poll"""
        return self.y < -self.deadzone

    @property
    def left(self):
        """Return true when the stick was pressed left at the last poll"""
        return self.x < -self.deadzone

    @property
    def right(self):
        """Return true when the stick was pressed right at the last poll"""
        return self.x > self.deadzone

    def recenter(self):
        """Use the current position of the analog joystick as the center"""
        self.x_center = self._x.value
        self.y_center = self._y.value
