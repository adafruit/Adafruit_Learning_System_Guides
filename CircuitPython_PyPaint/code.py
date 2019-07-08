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

#pylint:disable=invalid-name, no-self-use

import gc
import time
import board
import displayio
import adafruit_logging as logging
try:
    import adafruit_touchscreen
except ImportError:
    pass
try:
    from adafruit_cursorcontrol.cursorcontrol import Cursor
    from adafruit_cursorcontrol.cursorcontrol_cursormanager import DebouncedCursorManager
except ImportError:
    pass

class Color(object):
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

class TouchscreenPoller(object):
    """Get 'pressed' and location updates from a touch screen device."""

    def __init__(self, splash, cursor_bmp):
        logging.getLogger('Paint').debug('Creating a TouchscreenPoller')
        self._display_grp = splash
        self._touchscreen = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                                             board.TOUCH_YD, board.TOUCH_YU,
                                                             calibration=((9000, 59000),
                                                                          (8000, 57000)),
                                                             size=(320, 240))
        self._cursor_grp = displayio.Group(max_size=1)
        self._cur_palette = displayio.Palette(3)
        self._cur_palette.make_transparent(0)
        self._cur_palette[1] = 0xFFFFFF
        self._cur_palette[2] = 0x0000
        self._cur_sprite = displayio.TileGrid(cursor_bmp,
                                              pixel_shader=self._cur_palette)
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
            return True, p
        else:
            return False, None

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
        self._cur_sprite = displayio.TileGrid(bmp,
                                              pixel_shader=self._cur_palette)
        self._cursor_grp.append(self._cur_sprite)
        self.poke()

################################################################################

class CursorPoller(object):
    """Get 'pressed' and location updates from a D-Pad/joystick device."""

    def __init__(self, splash, cursor_bmp):
        logging.getLogger('Paint').debug('Creating a CursorPoller')
        self._mouse_cursor = Cursor(board.DISPLAY,
                                    display_group=splash,
                                    bmp=cursor_bmp,
                                    cursor_speed=2)
        self._x_offset = cursor_bmp.width // 2
        self._y_offset = cursor_bmp.height // 2
        self._cursor = DebouncedCursorManager(self._mouse_cursor)
        self._logger = logging.getLogger('Paint')

    def poll(self):
        """Check for input. Returns press of A (a bool), B,
        and the cursor location ((x,y) or None)"""
        location = None
        self._cursor.update()
        a_button = self._cursor.held
        if a_button:
            location = (self._mouse_cursor.x + self._x_offset,
                        self._mouse_cursor.y + self._y_offset)
        return a_button, location

    #pylint:disable=unused-argument
    def poke(self, x=None, y=None):
        """Force a bitmap refresh."""
        self._mouse_cursor.hide()
        self._mouse_cursor.show()
    #pylint:enable=unused-argument

    def set_cursor_bitmap(self, bmp):
        """Update the cursor bitmap.

        :param bmp: the new cursor bitmap
        """
        self._mouse_cursor.cursor_bitmap = bmp
        self.poke()

################################################################################

class Paint(object):

    def __init__(self, display=board.DISPLAY):
        self._logger = logging.getLogger("Paint")
        self._logger.setLevel(logging.DEBUG)
        self._display = display
        self._w = self._display.width
        self._h = self._display.height
        self._x = self._w // 2
        self._y = self._h // 2

        self._splash = displayio.Group(max_size=5)

        self._bg_bitmap = displayio.Bitmap(self._w, self._h, 1)
        self._bg_palette = displayio.Palette(1)
        self._bg_palette[0] = Color.BLACK
        self._bg_sprite = displayio.TileGrid(self._bg_bitmap,
                                             pixel_shader=self._bg_palette,
                                             x=0, y=0)
        self._splash.append(self._bg_sprite)

        self._palette_bitmap = displayio.Bitmap(self._w, self._h, 5)
        self._palette_palette = displayio.Palette(len(Color.colors))
        for i, c in enumerate(Color.colors):
            self._palette_palette[i] = c
        self._palette_sprite = displayio.TileGrid(self._palette_bitmap,
                                                  pixel_shader=self._palette_palette,
                                                  x=0, y=0)
        self._splash.append(self._palette_sprite)

        self._fg_bitmap = displayio.Bitmap(self._w, self._h, 5)
        self._fg_palette = displayio.Palette(len(Color.colors))
        for i, c in enumerate(Color.colors):
            self._fg_palette[i] = c
        self._fg_sprite = displayio.TileGrid(self._fg_bitmap,
                                             pixel_shader=self._fg_palette,
                                             x=0, y=0)
        self._splash.append(self._fg_sprite)

        self._number_of_palette_options = len(Color.colors) + 2
        self._swatch_height = self._h // self._number_of_palette_options
        self._swatch_width = self._w // 10
        self._logger.debug('Height: %d', self._h)
        self._logger.debug('Swatch height: %d', self._swatch_height)

        self._palette = self._make_palette()
        self._splash.append(self._palette)

        self._display.show(self._splash)
        self._display.refresh_soon()
        gc.collect()
        self._display.wait_for_frame()

        self._brush = 0
        self._cursor_bitmaps = [self._cursor_bitmap_1(), self._cursor_bitmap_3()]
        if hasattr(board, 'TOUCH_XL'):
            self._poller = TouchscreenPoller(self._splash, self._cursor_bitmaps[0])
        elif hasattr(board, 'BUTTON_CLOCK'):
            self._poller = CursorPoller(self._splash, self._cursor_bitmaps[0])
        else:
            raise AttributeError('PyPaint requires a touchscreen or cursor.')

        self._a_pressed = False
        self._last_a_pressed = False
        self._location = None
        self._last_location = None

        self._pencolor = 7

    def _make_palette(self):
        self._palette_bitmap = displayio.Bitmap(self._w // 10, self._h, 5)
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

        return displayio.TileGrid(self._palette_bitmap,
                                  pixel_shader=self._palette_palette,
                                  x=0, y=0)

    def _cursor_bitmap_1(self):
        bmp = displayio.Bitmap(9, 9, 3)
        for i in range(9):
            bmp[4, i] = 1
            bmp[i, 4] = 1
        bmp[4, 4] = 0
        return bmp

    def _cursor_bitmap_3(self):
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

    #pylint:disable=too-many-branches,too-many-statements

    def _draw_line(self, start, end):
        """Draw a line from the previous position to the current one.

        :param start: a tuple of (x, y) coordinatess to fram from
        :param end: a tuple of (x, y) coordinates to draw to
        """
        x0 = start[0]
        y0 = start[1]
        x1 = end[0]
        y1 = end[1]
        self._logger.debug("* GoTo from (%d, %d) to (%d, %d)", x0, y0, x1, y1)
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
                self._poller.poke((int(y0), int(x0)))
                time.sleep(0.003)
            else:
                try:
                    self._plot(int(x0), int(y0), self._pencolor)
                except IndexError:
                    pass
                self._x = x0
                self._y = y0
                self._poller.poke((int(x0), int(y0)))
                time.sleep(0.003)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx
            if rev:
                x0 -= 1
            else:
                x0 += 1

    #pylint:enable=too-many-branches,too-many-statements

    def _handle_palette_selection(self, location):
        selected = location[1] // self._swatch_height
        if selected >= self._number_of_palette_options:
            return
        self._logger.debug('Palette selection: %d', selected)
        if selected < len(Color.colors):
            self._pencolor = selected
        else:
            self._brush = selected - len(Color.colors)
            self._poller.set_cursor_bitmap(self._cursor_bitmaps[self._brush])

    def _handle_motion(self, start, end):
        self._logger.debug('Moved: (%d, %d) -> (%d, %d)', start[0], start[1], end[0], end[1])
        self._draw_line(start, end)

    def _handle_a_press(self, location):
        self._logger.debug('A Pressed!')
        if location[0] < self._w // 10:   # in color picker
            self._handle_palette_selection(location)
        else:
            self._plot(location[0], location[1], self._pencolor)
            self._poller.poke()

    #pylint:disable=unused-argument
    def _handle_a_release(self, location):
        self._logger.debug('A Released!')
    #pylint:enable=unused-argument

    @property
    def _was_a_just_pressed(self):
        return self._a_pressed and not self._last_a_pressed

    @property
    def _was_a_just_released(self):
        return not self._a_pressed and self._last_a_pressed

    @property
    def _did_move(self):
        if self._location is not None and self._last_location is not None:
            x_changed = self._location[0] != self._last_location[0]
            y_changed = self._location[1] != self._last_location[1]
            return x_changed or y_changed
        else:
            return False

    def _update(self):
        self._last_a_pressed, self._last_location = self._a_pressed, self._location
        self._a_pressed, self._location = self._poller.poll()


    def run(self):
        """Run the painting program."""
        while True:
            self._update()
            if self._was_a_just_pressed:
                self._handle_a_press(self._location)
            elif self._was_a_just_released:
                self._handle_a_release(self._location)
            if self._did_move and self._a_pressed:
                self._handle_motion(self._last_location, self._location)
            time.sleep(0.1)

painter = Paint()
painter.run()
