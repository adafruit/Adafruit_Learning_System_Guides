# SPDX-FileCopyrightText: 2022 Charlyn Gonda for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import adafruit_dotstar

from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.color import AMBER, JADE, CYAN, GOLD, PINK
from adafruit_pixel_framebuf import PixelFramebuffer


class Cube(object):
    def __init__(
            self,
            top_cin,
            top_din,
            side_panels_cin,
            side_panels_din,
            bottom_cin,
            bottom_din):

        # static numbers
        self.num_pixels = 64*4
        self.num_pixels_topbottom = 64
        self.pixel_width = 8*4
        self.pixel_height = 8

        # top pixels
        top_pixels = adafruit_dotstar.DotStar(
            top_cin, top_din, self.num_pixels_topbottom,
            brightness=0.03, auto_write=False)
        self.pixel_framebuf_top = PixelFramebuffer(
            top_pixels,
            self.pixel_height,
            self.pixel_height,
            rotation=1,
            alternating=False,
        )

        # side pixels
        self.side_pixels = adafruit_dotstar.DotStar(
            side_panels_cin, side_panels_din, self.num_pixels,
            brightness=0.03, auto_write=False)
        self.pixel_framebuf_sides = PixelFramebuffer(
            self.side_pixels,
            self.pixel_height,
            self.pixel_width,
            rotation=1,
            alternating=False,
            reverse_y=True,
            reverse_x=False
        )
        self.rainbow_sides = RainbowChase(
            self.side_pixels, speed=0.1, size=3, spacing=6)

        # bottom pixels
        pixels_bottom = adafruit_dotstar.DotStar(
            bottom_cin, bottom_din, self.num_pixels_topbottom,
            brightness=0.03, auto_write=False)
        self.pixel_framebuf_bottom = PixelFramebuffer(
            pixels_bottom,
            self.pixel_height,
            self.pixel_height,
            rotation=0,
            alternating=False,
            reverse_y=False,
            reverse_x=True
        )

        # scrolling word state vars
        self.last_color_time = -1
        self.color_wait = 1
        self.current_scroll_word = ''
        self.total_scroll_len = 0
        self.scroll_x_pos = -self.pixel_width
        self.color_idx = 0
        self.color_list = [AMBER, JADE, CYAN, PINK, GOLD]
        self.done_scrolling = False

        # whether or not the cube is already clear
        self.clear = False

        # top pixel vars
        self.top_pixel_coords = []
        self.top_pixel_color = CYAN

        # upside down mode
        self.bottom_last = -1
        self.bottom_wait = 1
        self.bottom_squares = [[0, 0, 8, 8], [
            1, 1, 6, 6], [2, 2, 4, 4], [3, 3, 2, 2]]
        self.bottom_squares_idx = 0

    def update(self, word, color, coords):
        self.word = word
        self.total_scroll_len = (len(self.word) * 5) + len(self.word)
        self.top_pixel_coords = coords
        self.top_pixel_color = color

    def scroll_word_and_update_top(self):
        if self.scroll_x_pos >= self.total_scroll_len:
            self.scroll_x_pos = -self.pixel_width
            self.clear_cube()
            self.done_scrolling = True
        else:
            self.done_scrolling = False
            self.clear = False

        self.__scroll_framebuf(self.word, self.scroll_x_pos, 0)
        self.__display_top_pixels()
        self.scroll_x_pos = self.scroll_x_pos + 1

    def clear_cube(self, clearTop=False):
        if not self.clear:
            self.pixel_framebuf_sides.fill(0)
            self.pixel_framebuf_sides.display()
            self.side_pixels.fill(0)
            self.side_pixels.show()
            self.pixel_framebuf_bottom.fill(0)
            self.pixel_framebuf_bottom.display()
            if (clearTop):
                self.pixel_framebuf_top.fill(0)
                self.pixel_framebuf_top.display()
            self.clear = True

    def upside_down_mode(self):
        self.clear_cube(True)
        self.rainbow_sides.animate()
        now = time.monotonic()
        self.__bottom_square_animation(now)

    def waiting_mode(self):
        self.pixel_framebuf_top.pixel(3, 3, self.__convert_to_hex(CYAN))
        self.pixel_framebuf_top.pixel(4, 4, self.__convert_to_hex(PINK))
        self.pixel_framebuf_top.display()

    def __bottom_square_animation(self, now):
        self.pixel_framebuf_bottom.fill(0)
        color_int = self.__convert_to_hex(CYAN)
        if now > self.bottom_last + self.bottom_wait:
            self.__coord_wrap()
            self.bottom_last = now
            x, y, w, h = self.bottom_squares[self.bottom_squares_idx]
            self.pixel_framebuf_bottom.rect(x, y, w, h, color_int)
            self.pixel_framebuf_bottom.display()

    def __coord_wrap(self):
        self.bottom_squares_idx = self.bottom_squares_idx + 1
        if self.bottom_squares_idx >= len(self.bottom_squares):
            self.bottom_squares_idx = 0

    def __display_top_pixels(self):
        self.pixel_framebuf_top.fill(0)
        color_int = self.__convert_to_hex(self.top_pixel_color)

        for coord in self.top_pixel_coords:
            x, y = coord.split(":")
            self.pixel_framebuf_top.pixel(int(x), int(y), color_int)
        self.pixel_framebuf_top.display()

    def __scroll_framebuf(self, word, shift_x, shift_y):
        self.pixel_framebuf_sides.fill(0)

        color = self.__next_color()
        color_int = self.__convert_to_hex(color)

        # negate x so that the word can be shown from left to right
        self.pixel_framebuf_sides.text(word, -shift_x, shift_y, color_int)
        self.pixel_framebuf_sides.display()

    def __next_color(self):
        if self.color_idx >= len(self.color_list):
            self.color_idx = 0

        result = self.color_list[self.color_idx]
        now = time.monotonic()
        if now >= self.last_color_time + self.color_wait:
            self.color_idx = self.color_idx + 1
            self.last_color_time = now

        return result

    def __convert_to_hex(self, color):
        return int('0x%02x%02x%02x' % color, 16)
