# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""NeoPixel Tetris on vertical 9x13 grid
Uses the seesaw gamepad for control"""

import time
import random
import board
import neopixel
from displayio import Bitmap
from micropython import const
from digitalio import DigitalInOut, Direction
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label
from adafruit_pixel_framebuf import PixelFramebuffer
from adafruit_seesaw.seesaw import Seesaw
from adafruit_ticks import ticks_ms, ticks_diff, ticks_add

# enable external power pin
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# NeoPixel grid setup with pixelframebuffer
NUMPIXELS = 117
BRIGHTNESS = 1
PIN = board.EXTERNAL_NEOPIXELS
ORDER = neopixel.BGR
pixels = neopixel.NeoPixel(PIN, NUMPIXELS, brightness=BRIGHTNESS,
                           auto_write=False, pixel_order=ORDER)
fb = PixelFramebuffer(
    pixels,
    width=9,
    height=13,
    orientation=0,
    rotation=2,
    alternating=True,
    reverse_x=True
)
grid = [0] * (9 * 13)
# font for scrolling text
font = bitmap_font.load_font("tom-thumb.pcf", Bitmap)

# seesaw gamepad
BUTTON_X = const(6)
BUTTON_Y = const(2)
BUTTON_A = const(5)
BUTTON_B = const(1)
BUTTON_SELECT = const(0)
BUTTON_START = const(16)
button_mask = const(
    (1 << BUTTON_X)
    | (1 << BUTTON_Y)
    | (1 << BUTTON_A)
    | (1 << BUTTON_B)
    | (1 << BUTTON_SELECT)
    | (1 << BUTTON_START)
)
i2c_bus = board.STEMMA_I2C()
seesaw = Seesaw(i2c_bus, addr=0x50)
seesaw.pin_mode_bulk(button_mask, seesaw.INPUT_PULLUP)
JOY_CENTER = 512
JOY_EDGE = 200

# Tetrominoes
o_tetro = [
    [0xFFFF00, 0xFFFF00],
    [0xFFFF00, 0xFFFF00],
]
i_tetro = [
    [0x00FFFF],
    [0x00FFFF],
    [0x00FFFF],
    [0x00FFFF],
]
s_tetro = [
    [0x000000, 0xFF0000, 0xFF0000],
    [0xFF0000, 0xFF0000, 0x000000],
]
z_tetro = [
    [0x00FF00, 0x00FF00, 0x000000],
    [0x000000, 0x00FF00, 0x00FF00],
]
l_tetro = [
    [0xFF5500, 0x000000],
    [0xFF5500, 0x000000],
    [0xFF5500, 0xFF5500],
]
j_tetro = [
    [0x000000, 0xFF00FF],
    [0x000000, 0xFF00FF],
    [0xFF00FF, 0xFF00FF],
]
t_tetro = [
    [0x5500FF, 0x5500FF, 0x5500FF],
    [0x000000, 0x5500FF, 0x000000],
]
tetrominoes = [o_tetro, i_tetro, s_tetro, z_tetro,
               l_tetro, j_tetro, t_tetro]

# sprite class to handle tetrominoes
class Sprite:
    def __init__(self, data, transparent=None, rotation=0):
        if isinstance(data[0], list):
            self.height = len(data)
            self.width = len(data[0])
            self.data = [pixel for row in data for pixel in row]
        else:
            raise ValueError("Sprite data must be a 2D list")
        self.x = 0
        self.y = 0
        self.transparent = transparent
        self.rotation = rotation

    def draw(self, framebuffer = fb, screen_w=9, screen_h=13):
        for row in range(self.height):
            for col in range(self.width):
                color = self.data[row * self.width + col]
                if color == self.transparent:
                    continue
                if self.rotation == 0:
                    px, py = col, row
                elif self.rotation == 1:
                    px, py = self.height - 1 - row, col
                elif self.rotation == 2:
                    px, py = self.width - 1 - col, self.height - 1 - row
                elif self.rotation == 3:
                    px, py = row, self.width - 1 - col
                px += self.x
                py += self.y
                if 0 <= px < screen_w and 0 <= py < screen_h:
                    framebuffer.pixel(px, py, color)

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def rotate(self, can_move_fn):
        new_rot = (self.rotation + 1) % 4
        # try rotation in place with no offset
        if can_move_fn(self, 0, 0, rot=new_rot):
            self.rotation = new_rot
            return True
        # calculate how far out of bounds the rotated piece would be
        old_rot = self.rotation
        self.rotation = new_rot
        new_w = self.draw_width
        new_h = self.draw_height
        self.rotation = old_rot

        kicks = []
        # right edge
        if self.x + new_w > 9:
            kicks.append((9 - self.x - new_w, 0))
        # left edge
        if self.x < 0:
            kicks.append((-self.x, 0))
        # bottom edge
        if self.y + new_h > 13:
            kicks.append((0, 13 - self.y - new_h))

        for dx, dy in kicks:
            old_x, old_y = self.x, self.y
            self.x += dx
            self.y += dy
            if can_move_fn(self, 0, 0, rot=new_rot):
                self.rotation = new_rot
                return True
            self.x = old_x
            self.y = old_y
        return False

    @property
    def draw_width(self):
        return self.width if self.rotation in (0, 2) else self.height

    @property
    def draw_height(self):
        return self.height if self.rotation in (0, 2) else self.width

def grid_get(x, y):
    return grid[y * 9 + x]

def grid_set(x, y, color):
    grid[y * 9 + x] = color

def can_move(s, dx, dy, rot=None):
    check_rot = rot if rot is not None else s.rotation
    px = 0
    py = 0
    for row in range(s.height):
        for col in range(s.width):
            color = s.data[row * s.width + col]
            if color == s.transparent:
                continue
            if check_rot == 0:
                px, py = col, row
            elif check_rot == 1:
                px, py = s.height - 1 - row, col
            elif check_rot == 2:
                px, py = s.width - 1 - col, s.height - 1 - row
            elif check_rot == 3:
                px, py = row, s.width - 1 - col
            nx = s.x + px + dx
            ny = s.y + py + dy
            if nx < 0 or nx >= 9:
                return False
            if ny >= 13:
                return False
            if ny >= 0 and grid_get(nx, ny) != 0:
                return False
    return True

def lock_sprite(s):
    px = 0
    py = 0
    for row in range(s.height):
        for col in range(s.width):
            color = s.data[row * s.width + col]
            if color == s.transparent:
                continue
            if s.rotation == 0:
                px, py = col, row
            elif s.rotation == 1:
                px, py = s.height - 1 - row, col
            elif s.rotation == 2:
                px, py = s.width - 1 - col, s.height - 1 - row
            elif s.rotation == 3:
                px, py = row, s.width - 1 - col
            grid_set(s.x + px, s.y + py, color)

def draw_grid(framebuffer):
    for y in range(13):
        for x in range(9):
            color = grid_get(x, y)
            if color != 0:
                framebuffer.pixel(x, y, color)

def clear_grid():
    for i in range(len(grid)):
        grid[i] = 0

def spawn_piece():
    seed = random.randint(0, 6)
    piece = Sprite(tetrominoes[seed], transparent=0x000000)
    max_x = 9 - piece.draw_width
    piece.x = random.randint(0, max(0, max_x))
    piece.y = -piece.draw_height  # start above the board
    return piece

def clear_rows(framebuffer):
    rows_cleared = 0
    y = 12
    while y >= 0:
        full = True
        for x in range(9):
            if grid_get(x, y) == 0:
                full = False
                break
        if full:
            rows_cleared += 1
            # flash the row white
            for x in range(9):
                grid_set(x, y, 0xFFFFFF)
            framebuffer.fill(0x000000)
            draw_grid(framebuffer)
            framebuffer.display()
            time.sleep(0.3)
            # shift everything down
            for shift_y in range(y, 0, -1):
                for x in range(9):
                    grid_set(x, shift_y, grid_get(x, shift_y - 1))
            for x in range(9):
                grid_set(x, 0, 0)
        else:
            y -= 1
    return rows_cleared

def is_game_over(s):
    py = 0
    for row in range(s.height):
        for col in range(s.width):
            color = s.data[row * s.width + col]
            if color == s.transparent:
                continue
            if s.rotation == 0:
                py = row
            elif s.rotation == 1:
                py = col
            elif s.rotation == 2:
                py = s.height - 1 - row
            elif s.rotation == 3:
                py = s.width - 1 - col
            if s.y + py < 0:
                return True
    return False

def scroll_text(the_bitmap, scroll_x, count = 0, counting = False, framebuffer = fb):
    framebuffer.fill(0x000000)
    for col in range(the_bitmap.width):
        px = 9 - scroll_x + col
        if 0 <= px < 9:
            for row in range(the_bitmap.height):
                if the_bitmap[col, row]:
                    framebuffer.pixel(px, ((13 - the_bitmap.height) // 2) + row, 0xFFFFFF)
    framebuffer.display()
    scroll_x = (scroll_x + 1) % (9 + the_bitmap.width)
    if scroll_x == 0:
        count += 1
    if counting:
        return scroll_x, count
    else:
        return scroll_x

# Input state
joy_moved = False
last_buttons = 0xFFFFFFFF
paused = False
gameplay = False
first_run = True
scroll_label = Label(text="IHTFP", font=font)
scroll_bmp = scroll_label.bitmap
scroll_count = 0
scroll_x_pos = 0
score = 0
sprite = 0
last_fall = ticks_ms()
timer = ticks_ms()
FALL_SPEED = int(0.5 * 1000)

while True:
    if first_run:
        while scroll_count < 2:
            if ticks_diff(ticks_ms(), timer) >= 150:
                scroll_x_pos, scroll_count = scroll_text(scroll_bmp, scroll_x_pos,
                                                         scroll_count, counting = True)
                timer = ticks_add(timer, 150)
        first_run = False
        scroll_count = 0
        scroll_label.text = "START?"
        scroll_bmp = scroll_label.bitmap
    now = ticks_ms()

	# read inputs
    x_joy = 1023 - seesaw.analog_read(14)
    buttons = seesaw.digital_read_bulk(button_mask)
    just_pressed = last_buttons & ~buttons

    if not gameplay:
        if ticks_diff(ticks_ms(), timer) >= 150:
            scroll_x_pos = scroll_text(scroll_bmp, scroll_x_pos)
            timer = ticks_add(timer, 150)
        if just_pressed & (1 << BUTTON_START):
            gameplay = True
            clear_grid()
            sprite = spawn_piece()
            last_fall = ticks_ms()
            scroll_x_pos = 0
            last_buttons = buttons
        continue

	# start button toggles pause
    if just_pressed & (1 << BUTTON_START):
        paused = not paused
        if paused:
            timer = ticks_ms()
            scroll_x_pos = 0
            scroll_label.text = f"PAUSED - {score} ROWS"
            scroll_bmp = scroll_label.bitmap
            fb.fill(0x000000)
            draw_grid(fb)
            fb.display()
        else:
            last_fall = ticks_ms()

    if paused:
        if ticks_diff(ticks_ms(), timer) >= 150:
            scroll_x_pos = scroll_text(scroll_bmp, scroll_x_pos)
            timer = ticks_add(timer, 150)
        last_buttons = buttons
        continue

	# rotate on A button press
    if just_pressed & (1 << BUTTON_A):
        sprite.rotate(can_move)

	# joystick left/right
    if x_joy < JOY_CENTER - JOY_EDGE:
        if not joy_moved:
            if can_move(sprite, -1, 0):
                sprite.move(-1, 0)
            joy_moved = True
    elif x_joy > JOY_CENTER + JOY_EDGE:
        if not joy_moved:
            if can_move(sprite, 1, 0):
                sprite.move(1, 0)
            joy_moved = True
    else:
        joy_moved = False

	# hard drop on b button
    if just_pressed & (1 << BUTTON_B):
        while can_move(sprite, 0, 1):
            sprite.move(0, 1)

    last_buttons = buttons

	# gravity on timer
    if ticks_diff(ticks_ms(), last_fall) >= FALL_SPEED:
        if can_move(sprite, 0, 1):
            sprite.move(0, 1)
        else:
            lock_sprite(sprite)

            fb.fill(0x000000)
            draw_grid(fb)
            fb.display()

            cleared = clear_rows(fb)
            if cleared > 0:
                last_fall = ticks_ms()
                score += cleared
                fb.fill(0x000000)
                draw_grid(fb)
                fb.display()
            if is_game_over(sprite):
                for _ in range(3):
                    fb.fill(0xFFFFFF)
                    fb.display()
                    time.sleep(0.5)
                    fb.fill(0x000000)
                    fb.display()
                    time.sleep(0.5)
                clear_grid()
                timer = ticks_ms()
                scroll_x_pos = 0
                scroll_label.text = f"{score} ROWS CLEARED!"
                scroll_bmp = scroll_label.bitmap
                while scroll_count < 2:
                    if ticks_diff(ticks_ms(), timer) >= 150:
                        scroll_x_pos, scroll_count = scroll_text(scroll_bmp, scroll_x_pos,
                                                                 scroll_count, counting = True)
                        timer = ticks_add(timer, 150)
                scroll_count = 0
                score = 0
                scroll_label.text = "START?"
                scroll_bmp = scroll_label.bitmap
                gameplay = False

            sprite = spawn_piece()
        last_fall = ticks_add(last_fall, FALL_SPEED)

    # draw
    fb.fill(0x000000)
    draw_grid(fb)
    sprite.draw(fb)
    fb.display()
