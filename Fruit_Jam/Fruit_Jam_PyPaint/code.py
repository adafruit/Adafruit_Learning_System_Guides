# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Paint for PyPortal, PyBadge, PyGamer, and the like.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import array
import gc
import time
import supervisor
import board
import displayio

try:
    import usb.core
    usb_available = True
except ImportError:
    usb_available = False

try:
    from adafruit_fruitjam.peripherals import request_display_config
except ImportError:
    request_display_config = None
try:
    import adafruit_touchscreen
except ImportError:
    pass
try:
    from adafruit_cursorcontrol.cursorcontrol import Cursor
    from adafruit_cursorcontrol.cursorcontrol_cursormanager import DebouncedCursorManager
except ImportError:
    pass

class Color():
    """Standard colors"""

    WHITE = 0xFFFFFF
    BLACK = 0x000000
    RED = 0xFF0000
    ORANGE = 0xFFA500
    YELLOW = 0xFFFF00
    GREEN = 0x00FF00
    BLUE = 0x0000FF
    PURPLE = 0x800080
    PINK = 0xFFC0CB

    colors = (BLACK, RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, WHITE)

    def __init__(self):
        pass


################################################################################


class TouchscreenPoller():
    """Get 'pressed' and location updates from a touch screen device."""

    def __init__(self, splash, cursor_bmp):
        print("Creating a TouchscreenPoller")
        self._display_grp = splash
        self._touchscreen = adafruit_touchscreen.Touchscreen(
            board.TOUCH_XL, board.TOUCH_XR,
            board.TOUCH_YD, board.TOUCH_YU,
            calibration=((9000, 59000), (8000, 57000)),
            size=(320, 240),
        )
        self._cursor_grp = displayio.Group()
        self._cur_palette = displayio.Palette(3)
        self._cur_palette.make_transparent(0)
        self._cur_palette[1] = 0xFFFFFF
        self._cur_palette[2] = 0x0000
        self._cur_sprite = displayio.TileGrid(
            cursor_bmp, pixel_shader=self._cur_palette
        )
        self._cursor_grp.append(self._cur_sprite)
        self._display_grp.append(self._cursor_grp)
        self._x_offset = cursor_bmp.width // 2
        self._y_offset = cursor_bmp.height // 2

    def poll(self):
        """Check for input. Returns contact (a bool), False (no button B),
        and it's location ((x,y) or None)"""

        p = self._touchscreen.touch_point
        if p is not None:
            self._cursor_grp.x = p[0] - self._x_offset
            self._cursor_grp.y = p[1] - self._y_offset
            return True, False, p
        else:
            return False, False, None

    def poke(self, location=None):
        """Force a bitmap refresh."""
        self._display_grp.remove(self._cursor_grp)
        if location is not None:
            self._cursor_grp.x = location[0] - self._x_offset
            self._cursor_grp.y = location[1] - self._y_offset
        self._display_grp.append(self._cursor_grp)

    def set_cursor_bitmap(self, bmp):
        """Update the cursor bitmap.

        :param bmp: the new cursor bitmap
        """
        self._cursor_grp.remove(self._cur_sprite)
        self._cur_sprite = displayio.TileGrid(bmp, pixel_shader=self._cur_palette)
        self._cursor_grp.append(self._cur_sprite)
        self.poke()


################################################################################


class CursorPoller():
    """Get 'pressed' and location updates from a D-Pad/joystick device."""

    def __init__(self, splash, cursor_bmp):
        print("Creating a CursorPoller")
        self._mouse_cursor = Cursor(
            board.DISPLAY, display_group=splash, bmp=cursor_bmp, cursor_speed=2
        )
        self._x_offset = cursor_bmp.width // 2
        self._y_offset = cursor_bmp.height // 2
        self._cursor = DebouncedCursorManager(self._mouse_cursor)

    def poll(self):
        """Check for input. Returns press of A (a bool), B,
        and the cursor location ((x,y) or None)"""
        location = None
        self._cursor.update()
        a_button = self._cursor.held
        if a_button:
            location = (
                self._mouse_cursor.x + self._x_offset,
                self._mouse_cursor.y + self._y_offset,
            )
        return a_button, False, location

    def poke(self):
        """Force a bitmap refresh."""
        self._mouse_cursor.hide()
        self._mouse_cursor.show()

    def set_cursor_bitmap(self, bmp):
        """Update the cursor bitmap.

        :param bmp: the new cursor bitmap
        """
        self._mouse_cursor.cursor_bitmap = bmp
        self.poke()


################################################################################

class MousePoller():
    """Get 'pressed' and location updates from a USB mouse."""

    def __init__(self, splash, cursor_bmp, screen_width, screen_height):
        print("Creating a MousePoller")
        self._display_grp = splash
        self._cursor_grp = displayio.Group()
        self._cur_palette = displayio.Palette(3)
        self._cur_palette.make_transparent(0)
        self._cur_palette[1] = 0xFFFFFF
        self._cur_palette[2] = 0x0000
        self._cur_sprite = displayio.TileGrid(
            cursor_bmp, pixel_shader=self._cur_palette
        )
        self._cursor_grp.append(self._cur_sprite)
        self._display_grp.append(self._cursor_grp)
        self._x_offset = cursor_bmp.width // 2
        self._y_offset = cursor_bmp.height // 2

        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height

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

        if not self.find_mouse():
            print("WARNING: Mouse not found after multiple attempts.")
            print("The application will run, but mouse control may not work.")


    def find_mouse(self): # pylint: disable=too-many-statements, too-many-locals
        """Find the mouse device with multiple retry attempts"""
        MAX_ATTEMPTS = 5
        RETRY_DELAY = 1  # seconds

        if not usb_available:
            print("USB library not available; cannot find mouse.")
            return False

        for attempt in range(MAX_ATTEMPTS):
            print(f"Mouse detection attempt {attempt+1}/{MAX_ATTEMPTS}")

            # Constants for USB control transfers
            DIR_OUT = 0
            # DIR_IN = 0x80  # Unused variable
            REQTYPE_CLASS = 1 << 5
            REQREC_INTERFACE = 1 << 0
            HID_REQ_SET_PROTOCOL = 0x0B

            # Find all USB devices
            devices_found = False

            for device in usb.core.find(find_all=True):
                devices_found = True
                print(f"Found device: {device.idVendor:04x}:{device.idProduct:04x}")

                try:
                    # Try to get device info
                    try:
                        manufacturer = device.manufacturer
                        product = device.product
                    except Exception:  # pylint: disable=broad-except
                        manufacturer = "Unknown"
                        product = "Unknown"

                    # Just use whatever device we find
                    self.mouse = device

                    # Try to detach kernel driver
                    try:
                        has_kernel_driver = hasattr(device, 'is_kernel_driver_active')
                        if has_kernel_driver and device.is_kernel_driver_active(0):
                            device.detach_kernel_driver(0)
                    except Exception as e:  # pylint: disable=broad-except
                        print(f"Error detaching kernel driver: {e}")

                    # Set configuration
                    try:
                        device.set_configuration()
                    except Exception as e:  # pylint: disable=broad-except
                        print(f"Error setting configuration: {e}")
                        continue  # Try next device

                    # Just assume endpoint 0x81 (common for mice)
                    self.in_endpoint = 0x81
                    print(f"Using mouse: {manufacturer}, {product}")

                    # Set to report protocol mode
                    try:
                        bmRequestType = DIR_OUT | REQTYPE_CLASS | REQREC_INTERFACE
                        bRequest = HID_REQ_SET_PROTOCOL
                        wValue = 1  # 1 = report protocol
                        wIndex = 0  # First interface

                        buf = bytearray(1)
                        device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buf)
                        print("Set to report protocol mode")
                    except Exception as e:  # pylint: disable=broad-except
                        print(f"Could not set protocol: {e}")

                    # Buffer for reading data
                    self.buf = array.array("B", [0] * 4)
                    print("Created 4-byte buffer for mouse data")

                    # Verify mouse works by reading from it
                    try:
                        # Try to read some data with a short timeout
                        data = device.read(self.in_endpoint, self.buf, timeout=100)
                        print(f"Mouse test read successful: {data} bytes")
                        return True
                    except usb.core.USBTimeoutError:
                        # Timeout is normal if mouse isn't moving
                        print("Mouse connected but not sending data (normal)")
                        return True
                    except Exception as e:  # pylint: disable=broad-except
                        print(f"Mouse test read failed: {e}")
                        # Continue to try next device or retry
                        self.mouse = None
                        self.in_endpoint = None
                        continue

                except Exception as e:  # pylint: disable=broad-except
                    print(f"Error initializing device: {e}")
                    continue

            if not devices_found:
                print("No USB devices found")

            # If we get here without returning, no suitable mouse was found
            print(f"No working mouse found on attempt {attempt+1}, retrying...")
            gc.collect()
            time.sleep(RETRY_DELAY)

        print("Failed to find a working mouse after multiple attempts")
        return False


    def poll(self):
        """Check for input. Returns contact (a bool), False (no button B),
        and it's location ((x,y) or None)"""

        if self._process_mouse_input():
            self._cursor_grp.x = self.mouse_x - self._x_offset
            self._cursor_grp.y = self.mouse_y - self._y_offset
            return self.left_button_pressed, self.right_button_pressed, \
                (self.mouse_x, self.mouse_y)
        else:
            return False, False, None

    def poke(self, location=None):
        """Force a bitmap refresh."""
        self._display_grp.remove(self._cursor_grp)
        if location is not None:
            self._cursor_grp.x = location[0] - self._x_offset
            self._cursor_grp.y = location[1] - self._y_offset
        self._display_grp.append(self._cursor_grp)

    def set_cursor_bitmap(self, bmp):
        """Update the cursor bitmap.

        :param bmp: the new cursor bitmap
        """
        self._cursor_grp.remove(self._cur_sprite)
        self._cur_sprite = displayio.TileGrid(bmp, pixel_shader=self._cur_palette)
        self._cursor_grp.append(self._cur_sprite)
        self.poke()

    def _process_mouse_input(self):
        """Process mouse input - simplified version without wheel support"""

        try:
            # Attempt to read data from the mouse (10ms timeout)
            count = self.mouse.read(self.in_endpoint, self.buf, timeout=10)

        except usb.core.USBTimeoutError:
            # Timeout is normal if mouse isn't moving
            return False
        except usb.core.USBError as e:
            # Handle timeouts silently
            if e.errno == 110:  # Operation timed out
                return False

            # Handle disconnections
            if e.errno == 19:  # No such device
                print("Mouse disconnected")
                self.mouse = None
                self.in_endpoint = None
                gc.collect()

            return False
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error reading mouse: {type(e).__name__}")
            return False

        if count >= 3:  # We need at least buttons, X and Y
            # Extract mouse button states
            buttons = self.buf[0]
            x = self.buf[1]
            y = self.buf[2]

            # Convert to signed values if needed
            if x > 127:
                x = x - 256
            if y > 127:
                y = y - 256

            # Extract button states
            current_left_button_state = buttons & 0x01
            current_right_button_state = (buttons & 0x02) >> 1

            # Detect button presses
            if current_left_button_state == 1 and self.last_left_button_state == 0:
                self.left_button_pressed = True
            elif current_left_button_state == 0 and self.last_left_button_state == 1:
                self.left_button_pressed = False

            if current_right_button_state == 1 and self.last_right_button_state == 0:
                self.right_button_pressed = True
            elif current_right_button_state == 0 and self.last_right_button_state == 1:
                self.right_button_pressed = False

            # Update button states
            self.last_left_button_state = current_left_button_state
            self.last_right_button_state = current_right_button_state

            # Update position
            self.mouse_x += x
            self.mouse_y += y

            # Ensure position stays within bounds
            self.mouse_x = max(0, min(self.SCREEN_WIDTH - 1, self.mouse_x))
            self.mouse_y = max(0, min(self.SCREEN_HEIGHT - 1, self.mouse_y))

            return True

        return False

################################################################################

class Paint(): # pylint: disable=too-many-statements
    def __init__(self, display=None):

        def _cursor_bitmap_1():
            bmp = displayio.Bitmap(9, 9, 3)
            for i in range(9):
                bmp[4, i] = 1
                bmp[i, 4] = 1
            bmp[4, 4] = 0
            return bmp

        def _cursor_bitmap_3():
            bmp = displayio.Bitmap(9, 9, 3)
            for i in range(9):
                bmp[3, i] = 1
                bmp[4, i] = 1
                bmp[5, i] = 1
                bmp[i, 3] = 1
                bmp[i, 4] = 1
                bmp[i, 5] = 1
            for i in range(3, 6):
                for j in range(3, 6):
                    bmp[i, j] = 0
            return bmp

        if display is None:
            if hasattr(board, "DISPLAY"):
                display = board.DISPLAY
            else:
                if request_display_config is not None:
                    request_display_config(320, 240)
                    display = supervisor.runtime.display
                else:
                    raise RuntimeError("No display found.")

        self._display = display
        self._w = self._display.width
        self._h = self._display.height
        self._x = self._w // 2
        self._y = self._h // 2

        self._splash = displayio.Group()

        self._bg_bitmap = displayio.Bitmap(self._w, self._h, 1)
        self._bg_palette = displayio.Palette(1)
        self._bg_palette[0] = Color.BLACK
        self._bg_sprite = displayio.TileGrid(
            self._bg_bitmap, pixel_shader=self._bg_palette, x=0, y=0
        )
        self._splash.append(self._bg_sprite)

        self._palette_bitmap = displayio.Bitmap(self._w, self._h, 8)
        self._palette_palette = displayio.Palette(len(Color.colors))
        for i, c in enumerate(Color.colors):
            self._palette_palette[i] = c
        self._palette_sprite = displayio.TileGrid(
            self._palette_bitmap, pixel_shader=self._palette_palette, x=0, y=0
        )
        self._splash.append(self._palette_sprite)

        self._fg_bitmap = displayio.Bitmap(self._w, self._h, 9)
        self._fg_palette = displayio.Palette(len(Color.colors)+1)
        for i, c in enumerate(Color.colors):
            self._fg_palette[i] = c
        self._fg_palette[8] = Color.PINK # Marker for filled areas
        self._fg_sprite = displayio.TileGrid(
            self._fg_bitmap, pixel_shader=self._fg_palette, x=0, y=0
        )
        self._splash.append(self._fg_sprite)

        self._number_of_palette_options = len(Color.colors) + 2
        self._swatch_height = self._h // self._number_of_palette_options
        self._swatch_width = self._w // 10
        print(f"Height: {self._h}")
        print(f"Swatch height: {self._swatch_height}")

        self._palette = self._make_palette()
        self._splash.append(self._palette)

        self._display.root_group = self._splash
        try:
            gc.collect()
            self._display.refresh(target_frames_per_second=60)
        except AttributeError:
            self._display.refresh_soon()
            gc.collect()
            self._display.wait_for_frame()

        self._brush = 0
        self._cursor_bitmaps = [_cursor_bitmap_1(), _cursor_bitmap_3()]
        if hasattr(board, "TOUCH_XL"):
            self._poller = TouchscreenPoller(self._splash, self._cursor_bitmaps[0])
        elif hasattr(board, "BUTTON_CLOCK"):
            self._poller = CursorPoller(self._splash, self._cursor_bitmaps[0])
        elif usb_available:
            self._poller = MousePoller(self._splash, self._cursor_bitmaps[0], self._w, self._h)
            if not self._poller.mouse:
                raise RuntimeError("No mouse found. Please connect a USB mouse.")
        else:
            raise AttributeError("PyPaint requires a touchscreen or cursor.")

        self._a_pressed = False
        self._last_a_pressed = False
        self._b_pressed = False
        self._last_b_pressed = False
        self._location = None
        self._last_location = None

        self._pencolor = 7

    def _make_palette(self):
        self._palette_bitmap = displayio.Bitmap(self._w // 10, self._h, 8)
        self._palette_palette = displayio.Palette(len(Color.colors))
        for i, c in enumerate(Color.colors):
            self._palette_palette[i] = c
            for y in range(self._swatch_height):
                for x in range(self._swatch_width):
                    self._palette_bitmap[x, self._swatch_height * i + y] = i

        swatch_x_offset = (self._swatch_width - 9) // 2
        swatch_y_offset = (self._swatch_height - 9) // 2
        swatch_y = self._swatch_height * len(Color.colors) + swatch_y_offset
        for i in range(9):
            self._palette_bitmap[swatch_x_offset + 4, swatch_y + i] = 1
            self._palette_bitmap[swatch_x_offset + i, swatch_y + 4] = 1
            self._palette_bitmap[swatch_x_offset + 4, swatch_y + 4] = 0

        swatch_y += self._swatch_height
        for i in range(9):
            self._palette_bitmap[swatch_x_offset + 3, swatch_y + i] = 1
            self._palette_bitmap[swatch_x_offset + 4, swatch_y + i] = 1
            self._palette_bitmap[swatch_x_offset + 5, swatch_y + i] = 1
            self._palette_bitmap[swatch_x_offset + i, swatch_y + 3] = 1
            self._palette_bitmap[swatch_x_offset + i, swatch_y + 4] = 1
            self._palette_bitmap[swatch_x_offset + i, swatch_y + 5] = 1
        for i in range(swatch_x_offset + 3, swatch_x_offset + 6):
            for j in range(swatch_y + 3, swatch_y + 6):
                self._palette_bitmap[i, j] = 0

        for i in range(self._h):
            self._palette_bitmap[self._swatch_width - 1, i] = 7

        return displayio.TileGrid(
            self._palette_bitmap, pixel_shader=self._palette_palette, x=0, y=0
        )

    def _plot(self, x, y, c):
        if self._brush == 0:
            r = [0]
        else:
            r = [-1, 0, 1]
        for i in r:
            for j in r:
                try:
                    self._fg_bitmap[int(x + i), int(y + j)] = c
                except IndexError:
                    pass

    def _draw_line(self, start, end):
        """Draw a line from the previous position to the current one.

        :param start: a tuple of (x, y) coordinatess to fram from
        :param end: a tuple of (x, y) coordinates to draw to
        """
        x0 = start[0]
        y0 = start[1]
        x1 = end[0]
        y1 = end[1]
        print(f"* GoTo from ({x0}, {y0}) to ({x1}, {y1})")
        steep = abs(y1 - y0) > abs(x1 - x0)
        rev = False
        dx = x1 - x0

        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
            dx = x1 - x0

        if x0 > x1:
            rev = True
            dx = x0 - x1

        dy = abs(y1 - y0)
        err = dx / 2
        ystep = -1
        if y0 < y1:
            ystep = 1

        while (not rev and x0 <= x1) or (rev and x1 <= x0):
            if steep:
                try:
                    self._plot(int(y0), int(x0), self._pencolor)
                except IndexError:
                    pass
                self._x = y0
                self._y = x0
                self._poller.poke()
                time.sleep(0.003)
            else:
                try:
                    self._plot(int(x0), int(y0), self._pencolor)
                except IndexError:
                    pass
                self._x = x0
                self._y = y0
                self._poller.poke()
                time.sleep(0.003)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx
            if rev:
                x0 -= 1
            else:
                x0 += 1

    def _fill(self, x, y, c): # pylint: disable=too-many-branches,too-many-locals
        """Fill an area with the current color.

        :param x: x coordinate to start filling from
        :param y: y coordinate to start filling from
        :param c: color to fill with
        """
        MARKER = 8  # Marker for filled areas
        print(f"Filling at ({x}, {y}) with color {c}")

        # pylint: disable-next=too-many-nested-blocks
        if self._fg_bitmap[x, y] != c: 
            blank_color = self._fg_bitmap[x, y]
            self._fg_bitmap[x, y] = MARKER
            done = False
            min_row = 0
            max_row = self._h - 1
            min_col = (self._w // 10) + 1
            max_col = self._w - 1
            while not done:
                newmin_row = self._h - 1
                newmax_row = 0
                newmin_col = self._w - 1
                newmax_col = (self._w // 10) + 1
                done = True
                for i in range(min_row,max_row):
                    for j in range(min_col,max_col):
                        if self._fg_bitmap[j, i] == MARKER:
                            newmarker = False
                            if j > self._w // 10 and self._fg_bitmap[j - 1, i] == blank_color:
                                self._fg_bitmap[j - 1, i] = MARKER
                                newmarker = True
                            if j < self._w - 1 and self._fg_bitmap[j + 1, i] == blank_color:
                                self._fg_bitmap[j + 1, i] = MARKER
                                newmarker = True
                            if i > 0 and self._fg_bitmap[j, i - 1] == blank_color:
                                self._fg_bitmap[j, i - 1] = MARKER
                                newmarker = True
                            if i < self._h - 1 and self._fg_bitmap[j, i + 1] == blank_color:
                                self._fg_bitmap[j, i + 1] = MARKER
                                newmarker = True

                            if newmarker:
                                done = False
                                if i < newmin_row:
                                    newmin_row = i
                                if i > newmax_row:
                                    newmax_row = i
                                if j < newmin_col:
                                    newmin_col = j
                                if j > newmax_col:
                                    newmax_col = j

                max_row = min(newmax_row + 2, self._h - 1)
                min_row = max(newmin_row - 2, 0)
                max_col = min(newmax_col + 2, self._w - 1)
                min_col = max(newmin_col - 2, (self._w // 10) + 1)

                self._poller.poke()

            for i in range(self._h):
                for j in range(self._w):
                    if self._fg_bitmap[j, i] == MARKER:
                        self._fg_bitmap[j, i] = c

            self._poller.poke()

    def _handle_palette_selection(self, location):
        selected = location[1] // self._swatch_height
        if selected >= self._number_of_palette_options:
            return
        print(f"Palette selection: {selected}")
        if selected < len(Color.colors):
            self._pencolor = selected
        else:
            self._brush = selected - len(Color.colors)
            self._poller.set_cursor_bitmap(self._cursor_bitmaps[self._brush])

    def _handle_motion(self, start, end):
        print(f"Moved: ({start[0]}, {start[1]}) -> ({end[0]}, {end[1]})")
        self._draw_line(start, end)

    def _handle_a_press(self, location):
        print("A Pressed!")
        if location[0] < self._w // 10:  # in color picker
            self._handle_palette_selection(location)
        else:
            self._plot(location[0], location[1], self._pencolor)
            self._poller.poke()

    @staticmethod
    def _handle_a_release():
        print("A Released!")

    def _handle_b_release(self, location):
        print("B Released!")
        if location[0] >= self._w // 10:  # not in color picker
            self._fill(location[0], location[1], self._pencolor)
            self._poller.poke()

    @property
    def _was_a_just_pressed(self):
        return self._a_pressed and not self._last_a_pressed

    @property
    def _was_a_just_released(self):
        return not self._a_pressed and self._last_a_pressed

    @property
    def _was_b_just_released(self):
        return not self._b_pressed and self._last_b_pressed

    @property
    def _did_move(self):
        if self._location is not None and self._last_location is not None:
            x_changed = self._location[0] != self._last_location[0]
            y_changed = self._location[1] != self._last_location[1]
            return x_changed or y_changed
        else:
            return False

    def _update(self):
        self._last_a_pressed = self._a_pressed
        self._last_b_pressed = self._b_pressed
        if self._location is not None:
            self._last_location = self._location
        self._a_pressed, self._b_pressed, self._location = self._poller.poll()

    def run(self):
        """Run the painting program."""
        while True:
            self._update()
            if self._was_a_just_pressed:
                self._handle_a_press(self._location)
            elif self._was_a_just_released:
                self._handle_a_release()
            if self._was_b_just_released:
                self._handle_b_release(self._last_location)
            if self._did_move and self._a_pressed:
                self._handle_motion(self._last_location, self._location)
            time.sleep(0.1)


painter = Paint()
painter.run()
