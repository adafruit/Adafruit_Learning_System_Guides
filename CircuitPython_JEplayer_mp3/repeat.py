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
Make a key (button) repeat when held down
"""

import time
class KeyRepeat:
    """Track the state of a button and, while it is held, output a press every
       'rate' seconds"""
    def __init__(self, getter, rate=0.5):
        self.getter = getter
        self.rate_ns = round(rate * 1e9)
        self.next = -1

    @property
    def value(self):
        """True when a button is first pressed, or once every 'rate' seconds
           thereafter"""
        state = self.getter()
        if not state:
            self.next = -1
            return False
        now = time.monotonic_ns()
        if state and now > self.next:
            self.next = now + self.rate_ns
            return True
        return False
