# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

from adafruit_button import Button

class EventButton(Button):
    """A button that can be used to trigger a callback when clicked.

    :param callback: The callback function to call when the button is clicked.
    A tuple can be passed with an argument that will be passed to the
    callback function. The first element of the tuple should be the
    callback function, and the remaining elements will be passed as
    arguments to the callback function.
    """
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.args = []
        if isinstance(callback, tuple):
            self.callback = callback[0]
            self.args = callback[1:]
        else:
            self.callback = callback

    def click(self):
        """Call the function when the button is pressed."""
        self.callback(*self.args)

    def handle_mouse(self, point, clicked, waiting_for_release):
        if waiting_for_release:
            return False

        # Handle mouse events for the button
        if self.contains(point):
            super().selected = True
            if clicked:
                self.click()
                return True
        else:
            super().selected = False
        return False
