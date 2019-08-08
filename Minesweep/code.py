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
import audioio
import adafruit_imageload
import adafruit_touchscreen
from random import seed, randint

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
BOMBREVEALED = 14
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


def check_for_win():
    """Check for a complete, winning game. That's one with all squares uncovered
    and all bombs correctly flagged, with no non-bomb squares flaged.
    """
    for x in range(20):
        for y in range(15):
            visible = tilegrid[x, y]
            under = get_data(x, y)
            if visible == BLANK:
                print('Found a unexplored square at (%d, %d)' % (x, y))
                return False               #still covewred squares, not done
            elif visible == BOMBFLAGGED and under != BOMB:
                print('Found misflagged bomb at (%d, %d)' % (x, y))
                return False               #misflagged bombs, not done
        return True
# comment or remove if not using screenshots ######################
#pylint:disable=global-statement
# from adafruit_bitmapsaver import save_pixels                    #
# from adafruit_debouncer import Debouncer                        #
# import busio                                                    #
# import adafruit_sdcard                                          #
# import storage                                                  #
# spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)    #
# cs = digitalio.DigitalInOut(board.SD_CS)                        #
# sdcard = adafruit_sdcard.SDCard(spi, cs)                        #
# vfs = storage.VfsFat(sdcard)                                    #
# storage.mount(vfs, "/sd")                                       #
# snapshot_switch = digitalio.DigitalInOut(board.D4)              #
# snapshot_switch.direction = digitalio.Direction.INPUT           #
# snapshot_switch.pull= digitalio.Pull.UP                         #
# snapshot = Debouncer(snapshot_switch)                           #
# screenshot_number = 1                                           #
#                                                                 #
# def make_new_screenshot():                                      #
#     global screenshot_number                                    #
#     print('Taking /sd/screenshot_%d.bmp' % (screenshot_number)) #
#     save_pixels('/sd/screenshot_%d.bmp' % (screenshot_number))  #
#     print('Finished taking scheenshot.')                        #
#     screenshot_number += 1                                      #
#pylint:enable=global-statement
###################################################################

def play_a_game():
    number_uncovered = 0
    touch_x = -1
    touch_y = -1
    touch_time = 0
    wait_for_release = False
    while True:
        now = time.monotonic()
        # snapshot.update()
        # if snapshot.fell:
        #     make_new_screenshot()
        #     continue
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
                print('Touched (%d, %d)' % (touch_x, touch_y))
                if tilegrid[touch_x, touch_y] == BLANK:
                    tilegrid[touch_x, touch_y] = BOMBFLAGGED
                elif tilegrid[touch_x, touch_y] == BOMBFLAGGED:
                    under_the_tile = get_data(touch_x, touch_y)
                    if under_the_tile == 14:
                        reveal()
                        tilegrid[touch_x, touch_y] = BOMBDEATH
                        return False          #lost
                    elif under_the_tile > OPEN0 and under_the_tile <= OPEN8:
                        tilegrid[touch_x, touch_y] = under_the_tile
                    elif under_the_tile == OPEN0:
                        tilegrid[touch_x, touch_y] = BLANK
                        number_uncovered += expand_uncovered(touch_x, touch_y)
                    else:
                        print('Unexpected value on board')
                        return None           #something bad happened
            if check_for_win():
                return True           #won

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
    wavedata = audioio.WaveFile(wavfile)
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
    # make_new_screenshot()
    wait_for_sound_and_cleanup(play_sound('win.wav'))

def loose():
    print('You lost')
    # make_new_screenshot()
    wavfile = play_sound('loose.wav')
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
        loose()
    time.sleep(5.0)
