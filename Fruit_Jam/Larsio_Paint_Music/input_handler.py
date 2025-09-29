# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# input_handler.py: CircuitPython Music Staff Application component
"""

from adafruit_usb_host_mouse import find_and_init_boot_mouse

# pylint: disable=invalid-name,no-member,too-many-instance-attributes,too-many-arguments
# pylint: disable=too-many-branches,too-many-statements,broad-except
# pylint: disable=too-many-nested-blocks,too-many-locals,no-self-use
class InputHandler:
    """Handles user input through mouse and interactions with UI elements"""

    def __init__(self, screen_width, screen_height, staff_y_start, staff_height):
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        self.STAFF_Y_START = staff_y_start
        self.STAFF_HEIGHT = staff_height

        # Mouse state
        self.last_left_button_state = 0
        self.last_right_button_state = 0
        self.left_button_pressed = False
        self.right_button_pressed = False
        self.mouse = None
        self.buf = None
        self.in_endpoint = None

        # Mouse position
        self.mouse_x = screen_width // 2
        self.mouse_y = screen_height // 2

    def find_mouse(self):
        self.mouse = find_and_init_boot_mouse(cursor_image=None)
        if self.mouse is None:
            print("Failed to find a working mouse after multiple attempts")
            return False

        # Change the mouse resolution so it's not too sensitive
        self.mouse.sensitivity = 4

        return True

    def process_mouse_input(self):
        """Process mouse input - simplified version without wheel support"""
        buttons = self.mouse.update()

        # Extract button states
        if buttons is None:
            current_left_button_state = 0
            current_right_button_state = 0
        else:
            current_left_button_state = 1 if 'left' in buttons else 0
            current_right_button_state = 1 if 'right' in buttons else 0

        # Detect button presses
        if current_left_button_state == 1 and self.last_left_button_state == 0:
            self.left_button_pressed = True
        else:
            self.left_button_pressed = False

        if current_right_button_state == 1 and self.last_right_button_state == 0:
            self.right_button_pressed = True
        else:
            self.right_button_pressed = False

        # Update button states
        self.last_left_button_state = current_left_button_state
        self.last_right_button_state = current_right_button_state

        # Update position
        self.mouse_x = self.mouse.x
        self.mouse_y = self.mouse.y

        # Ensure position stays within bounds
        self.mouse_x = max(0, min(self.SCREEN_WIDTH - 1, self.mouse_x))
        self.mouse_y = max(0, min(self.SCREEN_HEIGHT - 1, self.mouse_y))

        return True

    def point_in_rect(self, x, y, rect_x, rect_y, rect_width, rect_height):
        """Check if a point is inside a rectangle"""
        return (rect_x <= x < rect_x + rect_width and
                rect_y <= y < rect_y + rect_height)

    def is_over_staff(self, y):
        """Check if mouse is over the staff area"""
        return self.STAFF_Y_START <= y <= self.STAFF_Y_START + self.STAFF_HEIGHT
