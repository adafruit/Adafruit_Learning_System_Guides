"""
PyPortal based countdown of days until Halloween.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import board
import digitalio
import displayio
import adafruit_imageload
import adafruit_touchscreen
from random import seed, randint
from adafruit_bitmapsaver import save_pixels
from adafruit_debouncer import Debouncer

seed(int(time.monotonic()))

NUMBER_OF_BOMBS = 15

# Board pieces

OPEN0 = 0
OPEN1 = 1
OPEN2 = 2
OPEN3 = 3
OPEN4 = 4
OPEN5 = 5
OPEN6 = 6
OPEN7 = 7
OPEN8 = 8
BLANK = 9
BOMBDEATH = 10
BOMBFLAGGED = 11
BOMBMISFLAGGED = 12
BOMBQUESTION = 13
BOMBREVEALED = 14
BOMB = 14

snapshot = Debouncer(digitalio.DigitalInOut(board.D4))

sprite_sheet, palette = adafruit_imageload.load("/SpriteSheet.bmp",
                                                bitmap=displayio.Bitmap,
                                                palette=displayio.Palette)

display = board.DISPLAY
group = displayio.Group(scale=1, max_size=5)
touchscreen = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                               board.TOUCH_YD, board.TOUCH_YU,
                                               calibration=((9000, 59000),
                                                            (8000, 57000)),
                                               size=(display.width, display.height))
tilegrid = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                              width=20, height=15,
                              tile_height=16, tile_width=16,
                              default_tile=BLANK)
group.append(tilegrid)
display.show(group)

DATA_BOMB = -1

board_data = bytearray(b'\x00' * 300)

#pylint:disable=redefined-outer-name
def get_data(x, y):
    return board_data[y * 20 + x]

def set_data(x, y, value):
    board_data[y * 20 + x] = value
#pylint:disable=redefined-outer-name


def seed_bombs(how_many):
    for _ in range(how_many):
        while True:
            bomb_x = randint(0, 19)
            bomb_y = randint(0, 14)
            if get_data(bomb_x, bomb_y) == 0:
                set_data(bomb_x, bomb_y, 14)
                break


def compute_counts():
    """For each bomb, increment the count in each non-bomb square around it"""
    for y in range(15):
        for x in range(20):
            if get_data(x, y) != 14:
                continue                  # keep looking for bombs
            print('found bomb at %d, %d' % (x, y))
            for dx in (-1, 0, 1):
                if x + dx < 0 or x + dx >= 20:
                    continue              # off screen
                for dy in (-1, 0, 1):
                    if y + dy < 0 or y + dy >= 15:
                        continue          # off screen
                    count = get_data(x + dx, y + dy)
                    if count == 14:
                        continue          # don't process bombs
                    set_data(x + dx, y + dy, count + 1)


def reveal():
    for x in range(20):
        for y in range(15):
            tilegrid[x, y] = get_data(x, y)


def expand_uncovered(start_x, start_y):
    number_uncovered = 1
    stack = [(start_x, start_y)]
    while len(stack) > 0:
        x, y = stack.pop()
        if tilegrid[x, y] == BLANK:
            under_the_tile = get_data(x, y)
            if under_the_tile <= OPEN8:
                tilegrid[x, y] = under_the_tile
                number_uncovered += 1
                if under_the_tile == OPEN0:
                    for dx in (-1, 0, 1):
                        if x + dx < 0 or x + dx >= 20:
                            continue              # off screen
                        for dy in (-1, 0, 1):
                            if y + dy < 0 or y + dy >= 15:
                                continue          # off screen
                            if dx == 0 and dy == 0:
                                continue          # don't process where the bomb
                            stack.append((x + dx, y + dy))
    return number_uncovered


def play_a_game():
    number_uncovered = 0
    touch_x = -1
    touch_y = -1
    last_x = -1
    last_y = -1
    hold_count = 0
    press = 0
    touch_time = 0
    while True:
        now = time/monotonic()
        snapshot.update()
        # if snapshot.fell:
        #     save_pixels()
        #     continue
        if now >= touch_time:
            touch_time = now + 0.1
            touch_at = touchscreen.touch_point
            if touch_at is not None:
                touch_x = max(min([touch_at[0] // 16, 19]), 0)
                touch_y = max(min([touch_at[1] // 16, 14]), 0)
                if touch_x == last_x and touch_y == last_y:
                    hold_count += 1
            else:
                if hold_count > 5:
                    press = 2
                elif hold_count > 1:
            elif tilegrid[touch_x, touch_y] == BLANK:
                under_the_tile = get_data(touch_x, touch_y)
                if under_the_tile == 14:
                    reveal()
                    tilegrid[touch_x, touch_y] = BOMBDEATH
                    time.sleep(10.0)
                    return False          #lost
                elif under_the_tile > OPEN0 and under_the_tile <= OPEN8:
                    tilegrid[touch_x, touch_y] = under_the_tile
                elif under_the_tile == OPEN0:
                    number_uncovered += expand_uncovered(touch_x, touch_y)
                else:
                    print('Unexpected value on board')
                    return None           #something bad happened
                continue
            if number_uncovered == 300:
                return True           #won

def reset_board():
    for x in range(20):
        for y in range(15):
            tilegrid[x, y] = BLANK
            set_data(x, y, 0)
    seed_bombs(NUMBER_OF_BOMBS)
    compute_counts()

def play_won_sound():
    pass

def play_lost_sound():
    pass

while True:
    reset_board()
    result = play_a_game()
    if result is None:
        pass
    elif result:
        play_won_sound()
    else:
        play_lost_sound()
