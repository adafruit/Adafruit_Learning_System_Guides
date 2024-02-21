# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Pathfinder Auto Mode
# automatically advances to new image/sound
# press and hold the touch screen to toggle sound on and off
# by John Park for Adafruit and Sugru
# MIT License
import time
import board
import displayio
import neopixel
from adafruit_pyportal import PyPortal

# ===========User Settings=============
sound_mode = 1  # 0 is silent, 1 is normal
eye_mode = 1  # 0 is always red, 1 changes per emote
slide_speed = 1.0  # number of seconds to pause, 0 will go as fast as it can
# =======end User Settings=============

i = 0  # emote image index
display = board.DISPLAY

pixel = neopixel.NeoPixel(board.D4, 1, brightness=0.2, auto_write=False)
PINK = (200, 0, 50)
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
ORANGE = (255, 75, 0)
WHITE = (100, 100, 100)
CYAN = (0, 255, 255)
GREEN = (0, 235, 20)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
BLACK = (0, 0, 0)
GREY = (10, 10, 10)

if eye_mode != 0:
    colors = [PINK, RED, ORANGE, CYAN, YELLOW, GREEN, WHITE, RED, PURPLE, GREEN, GREY]
else:
    colors = [RED, RED, RED, RED, RED, RED, RED, RED, RED, RED, RED]

pixel.fill(colors[0])
pixel.show()

emote_img = [
    "/emotes/01_love.bmp",
    "/emotes/02_anger.bmp",
    "/emotes/03_KO.bmp",
    "/emotes/04_sad.bmp",
    "/emotes/05_happy.bmp",
    "/emotes/06_bang.bmp",
    "/emotes/07_sick.bmp",
    "/emotes/08_thumbsup.bmp",
    "/emotes/09_question.bmp",
    "/emotes/10_glitch.bmp",
    "/emotes/11_static.bmp",
]

vo_sound = [
    "/vo/pathfnd_45.wav",
    "/vo/pathfnd_46.wav",
    "/vo/pathfnd_47.wav",
    "/vo/pathfnd_48.wav",
    "/vo/pathfnd_49.wav",
    "/vo/pathfnd_51.wav",
    "/vo/pathfnd_52.wav",
    "/vo/pathfnd_53.wav",
    "/vo/pathfnd_54.wav",
    "/vo/pathfnd_55.wav",
    "/vo/pathfnd_56.wav",
]

pyportal = PyPortal(status_neopixel=board.NEOPIXEL)

# Open the file
with open(emote_img[0], "rb") as bitmap_file:
    # Setup the file as the bitmap data source
    bitmap = displayio.OnDiskBitmap(bitmap_file)
    # Create a TileGrid to hold the bitmap
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=getattr(bitmap,
                                                                'pixel_shader',
                                                                displayio.ColorConverter()))
    # Create a Group to hold the TileGrid
    group = displayio.Group()
    # Add the TileGrid to the Group
    group.append(tile_grid)
    # Add the Group to the Display
    display.root_group = group
    if sound_mode != 0:
        # play a sound file
        pyportal.play_file(vo_sound[10])
    else:
        pyportal.play_file("/vo/pathfnd_silent.wav")  # hack to deal w no mute method


# Loop forever so you can enjoy your image
while True:
    if pyportal.touchscreen.touch_point:
        if sound_mode == 0:
            sound_mode = 1
        else:
            sound_mode = 0

    i = (i + 1) % 11
    pixel.fill(colors[i])
    pixel.show()
    time.sleep(1)

    # CircuitPython 7+ compatible
    bitmap = displayio.OnDiskBitmap(emote_img[i])
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
    group = displayio.Group()
    group.append(tile_grid)
    display.root_group = group

    if sound_mode != 0:
        # play a sound file
        pyportal.play_file(vo_sound[i])
    else:
        pyportal.play_file("/vo/pathfnd_silent.wav")

    time.sleep(slide_speed)
