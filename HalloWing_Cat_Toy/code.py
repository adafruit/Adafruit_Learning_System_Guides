"""
HalloWing Interactive Cat Toy

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=global-statement

import time
from random import randrange
import board
import displayio
import digitalio
import touchio
import audioio
import neopixel
# import busio
# import adafruit_lis3dh

#-------------------------------------------------------------------------------
# Setup hardware

pir = digitalio.DigitalInOut(board.SENSE)
pir.direction = digitalio.Direction.INPUT

touch_1 = touchio.TouchIn(board.TOUCH1)
touch_4 = touchio.TouchIn(board.TOUCH4)

audio = audioio.AudioOut(board.A0)

backlight = digitalio.DigitalInOut(board.TFT_BACKLIGHT)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = False

splash = displayio.Group()
board.DISPLAY.show(splash)


# setup neopixel ring
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXEL, 24, brightness=.2)
pixels.fill((0, 0, 0))
pixels.show()

# setup accelerometer
# i2c = busio.I2C(board.SCL, board.SDA)
# lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)


#-------------------------------------------------------------------------------
# Play a wav file

def play_wave(filename):
    wave_file = open(filename, "rb")
    wave = audioio.WaveFile(wave_file)
    audio.play(wave)
    while audio.playing:
        pass
    wave_file.close()


#-------------------------------------------------------------------------------
# Display an image on the HalloWing TFT screen

def show_image(filename):
    image_file = open(filename, "rb")
    odb = displayio.OnDiskBitmap(image_file)
    face = displayio.Sprite(odb, pixel_shader=displayio.ColorConverter(), position=(0, 0))
    backlight.value = False
    splash.append(face)
    board.DISPLAY.wait_for_frame()
    backlight.value = True


#-------------------------------------------------------------------------------
# Neopixel routines

def random_colour():
    return (randrange(255), randrange(255), randrange(255))

# Set 6 random pixels to random colours.
# Keep track of which are lit so they can be turned off next time

twinkle_indecies = [0 ,0, 0, 0, 0, 0]

def twinkle():
    for p in range(6):
        pixels[twinkle_indecies[p]] = (0,0,0)
        twinkle_indecies[p] = randrange(len(pixels))
        pixels[twinkle_indecies[p]] = random_colour()
    pixels.show()


# Fill the ring with a random colour

def solid():
    pixels.fill(random_colour())
    pixels.show()


#-------------------------------------------------------------------------------
# The state machine

ARMED_STATE = 0
ATTRACT_STATE = 1
PLAY_STATE = 2
TOUCHED_STATE = 3
MOVED_STATE = 4
ROCKED_STATE = 5

TIMEOUT_EVENT = 0
MOVE_EVENT = 1
TOUCH_EVENT = 2
ROCK_EVENT = 3

TIMEOUT = 60

timeout_time = 0
current_state = -1
update_function = None
update_time = 0
update_interval = 0


def reset_timeout():
    global timeout_time
    timeout_time = time.monotonic() + TIMEOUT

def set_update(interval, func):
    global update_interval, update_time, update_function
    update_function = func
    update_interval = interval
    update_time = time.monotonic() + interval


def enter_state(state):
    global current_state, timeout_time, update_time
#    print("Entering state {0}".format(state))
    current_state = state

    if state == ARMED_STATE:
        timeout_time = 0
        update_time = 0
        backlight.value = False
        pixels.fill((0,0,0))
        pixels.show()

    elif state == ATTRACT_STATE:
        splash.pop()
        show_image(images[1])                 # here kitty
        reset_timeout()
        set_update(0.1, twinkle)

    elif state == PLAY_STATE:
        splash.pop()
        show_image(images[2])         # good kitty
        set_update(2.0, solid)

    elif state == TOUCHED_STATE:
        reset_timeout()
        update_time = 0
        pixels.fill((128, 0, 0))
        pixels.show()
        play_wave(sounds[randrange(len(sounds))])
        enter_state(PLAY_STATE)

    elif state == MOVED_STATE:
        enter_state(PLAY_STATE)

    elif state == ROCKED_STATE:
        reset_timeout()
        enter_state(PLAY_STATE)


def handle_event(event):
#    print("Handling event {0}".format(event))
    if event == TIMEOUT_EVENT:
        enter_state(ARMED_STATE)

    elif event == MOVE_EVENT:
        if current_state == ARMED_STATE:
            enter_state(ATTRACT_STATE)
        elif current_state == PLAY_STATE:
            enter_state(MOVED_STATE)

    elif event == TOUCH_EVENT:
        if current_state in [ARMED_STATE, ATTRACT_STATE, PLAY_STATE]:
            enter_state(TOUCHED_STATE)

    elif event == ROCK_EVENT:
        if current_state in [ARMED_STATE, ATTRACT_STATE, PLAY_STATE]:
            enter_state(ROCKED_STATE)



#-------------------------------------------------------------------------------
# Check for event triggers

was_moving = False

def started_moving():
    global was_moving
    started = False
    moving_now = pir.value
    if moving_now:
        started = not was_moving
    was_moving = moving_now
    return started


was_touching = False

def started_touching():
    global was_touching
    started = False
    touching_now = touch_1.value or touch_4.value
    if touching_now:
        started = not was_touching
    was_touching = touching_now
    return started


def started_rocking():
    return False


#-------------------------------------------------------------------------------
# Image and sound filenames

images = ["please_standby.bmp", "here_kitty.bmp", "good_kitty.bmp"]
sounds = ["Cat_Meow_2.wav", "Cat_Meowing.wav", "kitten3.wav", "kitten4.wav"]


#-------------------------------------------------------------------------------
# Get started and loop, looking for and handling events

show_image(images[0])                    # waiting display
time.sleep(3)
arm_time = 0
armed = True

enter_state(ARMED_STATE)

while True:
    now = time.monotonic()

    if update_time > 0 and now > update_time:
        update_time += update_interval
        update_function()

    if timeout_time > 0 and now > timeout_time:
        handle_event(TIMEOUT_EVENT)

    elif started_moving():
        handle_event(MOVE_EVENT)

    elif started_touching():
        handle_event(TOUCH_EVENT)

    elif started_rocking():
        handle_event(ROCK_EVENT)
