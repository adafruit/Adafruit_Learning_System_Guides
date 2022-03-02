# SPDX-FileCopyrightText: 2020 Erin St Blaine for Adafruit Industries
# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Bottle Piano with Capacitive Touch
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Melissa LeBlanc, Erin St Blaine & Limor Fried for Adafruit Industries
Copyright (c) 2019-2020 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

import time
import digitalio
import board
import neopixel
import busio
import adafruit_mpr121
from audiocore import WaveFile
from audiopwmio import PWMAudioOut as AudioOut
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import (
    BLACK,
    RED,
    ORANGE,
    YELLOW,
    GREEN,
    BLUE,
    MAGENTA,
    PURPLE,
    AMBER,
    TEAL,
)
from adafruit_debouncer import Debouncer

# pylint: disable=global-statement

# NeoPixel strip setup -- set your total number of pixels here  -----------------
PIXEL_NUM = 200
pixel_pin = board.A1
pixels = neopixel.NeoPixel(pixel_pin, PIXEL_NUM, brightness=1, auto_write=False)
LAST_BUTTON = None

'''
Customize your light strip for individual notes. Each line represents a bottle.
Change the numbers to reflect the first and last pixel in each ring. You can also
change the colors assigned to each bottle here.
'''

bottle_lights = (
    (0, 10, RED),
    (15, 30, ORANGE),
    (31, 52, AMBER),
    (53, 72, YELLOW),
    (77, 96, GREEN),
    (98, 119, TEAL),
    (120, 145, BLUE),
    (150, 173, PURPLE),
    (180, 200, MAGENTA),
)

# Cap touch board setup   ------------------------------------------------------
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Demo MODE LED Animations  ------------------------------------------------------
rainbow = Rainbow(pixels, speed=0, period=10, name="rainbow", step=1)
rainbow_chase = RainbowChase(pixels, speed=0, size=5, spacing=10)
chase = Chase(pixels, speed=0.1, color=RED, size=1, spacing=6)
rainbow_comet = RainbowComet(pixels, speed=0.01, tail_length=60, bounce=True)

# Animation Sequence Playlist -- rearrange to change the order of animations

animations = AnimationSequence(
    rainbow_chase,
    chase,
    rainbow_comet,
    auto_clear=True,
    auto_reset=True,
)

def go_dark():
    '''set all pixels to black'''
    pixels.fill(BLACK)
    pixels.show()


# Debouncer ------------------------------------------------------

buttons = [Debouncer(mpr121[i]) for i in range(12)]


# Audio Setup ------------------------------------------------------

spkr_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
spkr_enable.direction = digitalio.Direction.OUTPUT
spkr_enable.value = True

audio = AudioOut(board.SPEAKER)

tracks = (
    WaveFile(open("sounds/F2.wav", "rb")),  # 0
    WaveFile(open("sounds/G2.wav", "rb")),  # 1
    WaveFile(open("sounds/A2.wav", "rb")),  # 2
    WaveFile(open("sounds/Bb2.wav", "rb")),  # 3
    WaveFile(open("sounds/C2.wav", "rb")),  # 4
    WaveFile(open("sounds/D3.wav", "rb")),  # 5
    WaveFile(open("sounds/E3.wav", "rb")),  # 6
    WaveFile(open("sounds/F3.wav", "rb")),  # 7
    WaveFile(open("sounds/F1.wav", "rb")),  # 7
    WaveFile(open("sounds/G1.wav", "rb")),  # 8
    WaveFile(open("sounds/A1.wav", "rb")),  # 9
    WaveFile(open("sounds/Bb1.wav", "rb")),  # 10
    WaveFile(open("sounds/C1.wav", "rb")),  # 11
    WaveFile(open("sounds/D2.wav", "rb")),  # 12
    WaveFile(open("sounds/E2.wav", "rb")),  # 13
    WaveFile(open("sounds/F2.wav", "rb")),  # 13
)

# Add or change song track names here. They will play in the order listed.
demo_tracks = (
    WaveFile(open("sounds/undersea.wav", "rb")),
    WaveFile(open("sounds/tequila.wav", "rb")),
    WaveFile(open("sounds/lion.wav", "rb")),
)

MODE = 0  # Initial mode = OFF
SONG = 0




def light_up(bottle):
    '''light up the bottles'''
    lights = bottle_lights[bottle]
    for pixel_id in range(lights[0], lights[1]):
        pixels[pixel_id] = lights[2]


def play_bottle(bottle_id, is_octave):
    ''' play audio tracks and light up bottles'''
    global MODE
    go_dark()
    light_up(bottle_id)
    if is_octave:
        audio.play(tracks[bottle_id + 7])  # Start playing sound
        light_up(8)
    else:
        audio.play(tracks[bottle_id])  # Start playing sound
    pixels.show()
    MODE = 2


def check_buttons(touched):
    ''' check to see if buttons have been pressed'''
    global MODE, LAST_BUTTON
    octave = touched[11]
    off = touched[9]
    if octave:
        light_up(8)
    for pad in range(1, 9):
        if LAST_BUTTON is not None and not touched[LAST_BUTTON]:
            LAST_BUTTON = None
        if pad != LAST_BUTTON and touched[pad]:
            LAST_BUTTON = pad
            play_bottle(pad - 1, octave)
    if off:
        MODE = 9
        go_dark()
    if touched[10]:
        go_dark()
        audio.play(demo_tracks[SONG])
        while audio.playing:
            animations.animate()

        MODE = 3


while True:
    # Idle mode: Play a Rainbow animation when nothing's being touched
    if MODE == 0:
        pixels.brightness = 0.3  #rainbow mode is much brighter than the other modes, so adjust here
        rainbow.animate()
        for button in buttons:
            button.update()
        check_buttons(mpr121.touched_pins)
        time.sleep(0.1)
        for i in range(12):
            if buttons[i].fell:
                MODE = 1
    # If not idle mode
    if MODE >= 1:
        pixels.brightness = 1
        check_buttons(mpr121.touched_pins)
        time.sleep(0.1)
        if MODE == 2:  # mode 2 is individual notes
            if audio.playing:
                pixels.show()
                while audio.playing:
                    check_buttons(mpr121.touched_pins)
                    time.sleep(0.07)
            else:
                MODE = 0  # Return to idle mode
        if MODE == 3:
            SONG = SONG + 1
            animations.next()
            if SONG == 3:
                MODE = 0
                SONG = 0

            else:
                MODE = 0  # Return to idle mode
        if MODE == 9:  # MODE 9 is "off" mode, listening for a new button press to wake up.
#             for button in buttons:
#                 button.update()
            for i in range(12):
                if buttons[i].fell:
                    MODE = 1
