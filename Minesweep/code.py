"""
PyPortal MineSweeper

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
from random import seed, randint
import board
import digitalio
import displayio
import audioio
try:
    from audioio import WaveFile
except ImportError:
    from audiocore import WaveFile

import adafruit_imageload
import adafruit_touchscreen

seed(int(time.monotonic()))

# Set up audio
speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.switch_to_output(False)
if hasattr(board, 'AUDIO_OUT'):
    audio = audioio.AudioOut(board.AUDIO_OUT)
elif hasattr(board, 'SPEAKER'):
    audio = audioio.AudioOut(board.SPEAKER)
else:
    raise AttributeError('Board does not have a builtin speaker!')


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
BOMB = 14

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
            if tilegrid[x, y] == BOMBFLAGGED and get_data(x, y) != BOMB:
                tilegrid[x, y] = BOMBMISFLAGGED
            else:
                tilegrid[x, y] = get_data(x, y)

#pylint:disable=too-many-nested-blocks
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
#pylint:enable=too-many-nested-blocks

def check_for_win():
    """Check for a complete, winning game. That's one with all squares uncovered
    and all bombs correctly flagged, with no non-bomb squares flaged.
    """
    # first make sure everything has been explored and decided
    for x in range(20):
        for y in range(15):
            if tilegrid[x, y] == BLANK or tilegrid[x, y] == BOMBQUESTION:
                return None               #still ignored or question squares
    # then check for mistagged bombs
    for x in range(20):
        for y in range(15):
            if tilegrid[x, y] == BOMBFLAGGED and get_data(x, y) != BOMB:
                return False               #misflagged bombs, not done
    return True               #nothing unexplored, and no misflagged bombs

#pylint:disable=too-many-branches
# This could be broken apart but I think it's more understandable
# with it all in one place
def play_a_game():
    number_uncovered = 0
    touch_x = -1
    touch_y = -1
    touch_time = 0
    wait_for_release = False
    while True:
        now = time.monotonic()
        if now >= touch_time:
            touch_time = now + 0.2
            # process touch
            touch_at = touchscreen.touch_point
            if touch_at is None:
                wait_for_release = False
            else:
                if wait_for_release:
                    continue
                wait_for_release = True
                touch_x = max(min([touch_at[0] // 16, 19]), 0)
                touch_y = max(min([touch_at[1] // 16, 14]), 0)
                if tilegrid[touch_x, touch_y] == BLANK:
                    tilegrid[touch_x, touch_y] = BOMBQUESTION
                elif tilegrid[touch_x, touch_y] == BOMBQUESTION:
                    tilegrid[touch_x, touch_y] = BOMBFLAGGED
                elif tilegrid[touch_x, touch_y] == BOMBFLAGGED:
                    under_the_tile = get_data(touch_x, touch_y)
                    if under_the_tile == 14:
                        set_data(touch_x, touch_y, BOMBDEATH) #reveal a red bomb
                        tilegrid[touch_x, touch_y] = BOMBDEATH
                        return False          #lost
                    elif under_the_tile > OPEN0 and under_the_tile <= OPEN8:
                        tilegrid[touch_x, touch_y] = under_the_tile
                    elif under_the_tile == OPEN0:
                        tilegrid[touch_x, touch_y] = BLANK
                        number_uncovered += expand_uncovered(touch_x, touch_y)
                    else:                    #something bad happened
                        raise ValueError('Unexpected value on board')
            status = check_for_win()
            if status is None:
                continue
            return status
#pylint:enable=too-many-branches

def reset_board():
    for x in range(20):
        for y in range(15):
            tilegrid[x, y] = BLANK
            set_data(x, y, 0)
    seed_bombs(NUMBER_OF_BOMBS)
    compute_counts()

def play_sound(file_name):
    board.DISPLAY.wait_for_frame()
    wavfile = open(file_name, "rb")
    wavedata = WaveFile(wavfile)
    speaker_enable.value = True
    audio.play(wavedata)
    return wavfile

def wait_for_sound_and_cleanup(wavfile):
    while audio.playing:
        pass
    wavfile.close()
    speaker_enable.value = False

def win():
    print('You won')
    wait_for_sound_and_cleanup(play_sound('win.wav'))

def lose():
    print('You lost')
    wavfile = play_sound('lose.wav')
    for _ in range(10):
        tilegrid.x = randint(-2, 2)
        tilegrid.y = randint(-2, 2)
        display.refresh_soon()
        display.wait_for_frame()
    tilegrid.x = 0
    tilegrid.y = 0
    wait_for_sound_and_cleanup(wavfile)

while True:
    reset_board()
    if play_a_game():
        win()
    else:
        reveal()
        lose()
    time.sleep(5.0)
