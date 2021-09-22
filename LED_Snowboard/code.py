"""
LED Snowboard with Feather M4 and PropMaker Wing
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Erin St Blaine & Limor Fried for Adafruit Industries
Copyright (c) 2020-2021 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.



"""
# pylint: disable=import-error
# pylint: disable=no-member
import time
import board
import digitalio
from digitalio import DigitalInOut, Direction, Pull
from rainbowio import colorwheel
import adafruit_lis3dh
import neopixel
from adafruit_led_animation.helper import PixelMap
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.color import (
    BLACK,
    RED,
    GREEN,
    ORANGE,
    BLUE,
    PURPLE,
    WHITE,
)

btn = DigitalInOut(board.A1)
btn.direction = Direction.INPUT
btn.pull = Pull.UP

prev_state = btn.value

THRESHOLD = -1 #shake threshold
CARVE_THRESHOLD = 5

# Set to the length in seconds for the animations
POWER_ON_DURATION = 2

NUM_PIXELS = 211  # Number of pixels used in project
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10

enable = digitalio.DigitalInOut(POWER_PIN)
enable.direction = digitalio.Direction.OUTPUT
enable.value = False


# Set up accelerometer on I2C bus, 4G range:
i2c = board.I2C()
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G
accel.set_tap(2, 15)

pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
pixels.fill(0)  # NeoPixels off ASAP on startup
pixels.show()


#PIXEL MAPS: Used for reordering pixels so the animations can run in different configurations.
#My LED strips inside the neck are accidentally swapped left-right,
#so these maps also correct for that


#Bottom up along both sides at once
pixel_map_right = PixelMap(pixels, [
    150, 151, 152, 149, 148, 147, 146, 145, 144, 143, 142,
    141, 140, 139, 138, 137, 136, 135, 134, 133, 132, 131,
    130, 129, 128, 127, 126, 125, 124, 123, 122, 121, 120,
    119, 118, 117, 116, 115, 114, 113, 112, 111, 110, 109,
    108, 107, 106, 105, 104, 103, 102, 101, 100, 99, 98, 97,
    96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83,
    82, 81, 80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 69,
    68, 67, 66, 65, 64, 63, 62, 61, 60, 59, 58, 57, 56, 55,
    54, 53, 52, 51, 50, 49, 48, 47, 46,
    ], individual_pixels=True)

#Starts at the bottom and goes around clockwise
pixel_map_left = PixelMap(pixels, [
    153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164,
    165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176,
    177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189,
    190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202,
    203, 204, 205, 206, 207, 208, 209, 210, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45,
    ], individual_pixels=True)

#Radiates from the center outwards like a starburst
pixel_map_radiate = PixelMap(pixels, [
    206, 98, 205, 99, 207, 97, 204, 100, 208, 96, 203, 101, 209,
    95, 202, 102, 210, 94, 0, 93, 92, 201, 103, 1, 91, 200, 104,
    2, 90, 199, 105, 3, 89, 198, 106, 4, 88, 197, 107, 5, 87, 196,
    108, 6, 86, 195, 109, 7, 85, 194, 110, 8, 84, 193, 111, 9, 83,
    192, 112, 10, 82, 191, 113, 11, 81, 190, 114, 12, 80, 189, 115,
    13, 79, 188, 116, 14, 78, 187, 117, 15, 77, 186, 118, 16, 76, 185,
    119, 17, 75, 184, 120, 18, 74, 183, 121, 19, 73, 182, 122, 20, 72,
    181, 123, 21, 71, 180, 124, 22, 70, 179, 125, 23, 69, 178, 126, 24,
    68, 177, 127, 25, 67, 176, 128, 26, 66, 175, 129, 27, 65, 174, 130,
    28, 64, 173, 131, 29, 63, 172, 132, 30, 62, 171, 133, 31, 61, 170, 134, 32,
    60, 169, 135, 33, 69, 168, 136, 34, 58, 167, 137, 35, 57, 166, 138, 36, 56,
    165, 139, 37, 55, 164, 140, 38, 54, 163, 141, 39, 53, 162, 142, 40, 52, 161,
    143, 41, 51, 160, 144, 42, 50, 159, 145, 43, 49, 158, 146, 44, 48, 157, 147,
    45, 47, 156, 148, 46, 46, 155, 149, 47, 154, 149, 153, 150, 152, 151,
    ], individual_pixels=True)

#Top down along both sides at once
pixel_map_sweep = PixelMap(pixels, [
    151, 152, 150, 153, 149, 154, 148, 155, 147, 156, 146, 157, 145, 158,
    144, 159, 143, 160, 142, 161, 141, 162, 140, 163, 139, 164, 138, 165,
    137, 166, 136, 167, 135, 168, 134, 169, 133, 170, 132, 171, 131, 172,
    130, 173, 129, 174, 128, 175, 127, 176, 126, 177, 125, 178, 124, 179,
    123, 180, 122, 181, 121, 182, 120, 183, 119, 184, 118, 185, 117, 186,
    116, 187, 115, 188, 114, 189, 113, 190, 112, 191, 111, 192, 110, 193,
    109, 194, 108, 195, 107, 196, 106, 197, 105, 198, 104, 199, 103, 200,
    102, 201, 101, 202, 100, 203, 99, 204, 98, 205, 97, 206, 96, 207, 95,
    208, 94, 209, 93, 210, 92, 91, 0, 90, 1, 89, 2, 88, 3, 87, 4, 86, 5, 85,
    6, 84, 7, 83, 8, 82, 9, 81, 10, 80, 11, 79, 12, 78, 13, 77, 14, 76, 15,
    75, 16, 74, 17, 73, 18, 72, 19, 71, 20, 70, 21, 69, 22, 68, 23, 67, 24,
    66, 25, 65, 24, 64, 25, 63, 26, 62, 27, 61, 28, 60, 29, 59, 30, 58, 31,
    57, 32, 56, 33, 55, 34, 54, 35, 53, 36, 52, 37, 51, 38, 50, 39, 49, 40,
    48, 41, 47, 42, 46, 43, 45, 44,
    ], individual_pixels=True)

pixel_map_tail = PixelMap(pixels, [
    15, 75, 16, 74, 17, 73, 18, 72, 19, 71, 20, 70, 21, 69, 22, 68, 23, 67,
    24, 66, 25, 65, 24, 64, 25, 63, 26, 62, 27, 61, 28, 60, 29, 59, 30, 58,
    31, 57, 32, 56, 33, 55, 34, 54, 35, 53, 36, 52, 37, 51, 38, 50, 39, 49,
    40, 48, 41, 47, 42, 46, 43, 45, 44,
    ], individual_pixels=True)

pixel_map = [
    pixel_map_right,
    pixel_map_left,
    pixel_map_radiate,
    pixel_map_sweep,
    pixel_map_tail,
]


def power_on(duration):
    """
    Animate NeoPixels for power on.
    """
    start_time = time.monotonic()  # Save start time
    while True:
        elapsed = time.monotonic() - start_time  # Time spent
        if elapsed > duration:  # Past duration?
            break  # Stop animating
        powerup.animate()


# Cusomize LED Animations  ------------------------------------------------------
powerup = RainbowComet(pixel_map[3], speed=0, tail_length=25, bounce=False)
rainbow = Rainbow(pixel_map[2], speed=0, period=6, name="rainbow", step=2.4)
rainbow_chase = RainbowChase(pixels, speed=0, size=6, spacing=15, step=10)
rainbow_chase2 = RainbowChase(pixels, speed=0, size=10, spacing=1, step=18, name="rainbow_chase2")
chase = RainbowChase(pixel_map[3], speed=0, size=20, spacing=20)
chase2 = Chase(pixels, speed=0.1, color=ORANGE, size=6, spacing=6)
rainbow_comet = RainbowComet(pixel_map[2], speed=0, tail_length=200, bounce=True)
rainbow_comet2 = RainbowComet(
    pixels, speed=0, tail_length=104, colorwheel_offset=80, bounce=True
    )
rainbow_comet3 = RainbowComet(
    pixel_map[2], speed=0, tail_length=80, colorwheel_offset=80, step=4, bounce=False
    )
strum = RainbowComet(
    pixel_map[3], speed=0, tail_length=50, bounce=False, colorwheel_offset=50, step=4
    )
fuego = RainbowComet(
    pixel_map[4], speed=0.05, colorwheel_offset=40, step=2, tail_length=40
    )
fuego2 = RainbowComet(
    pixel_map[4], speed=0.02, colorwheel_offset=40, step=2, tail_length=40
    )
lava = Comet(pixel_map[4], speed=0, color=ORANGE, tail_length=40, bounce=False)
sparkle = Sparkle(pixel_map[3], speed=0.05, color=BLUE, num_sparkles=10)
sparkle2 = Sparkle(pixels, speed=0.05, color=PURPLE, num_sparkles=4)
sparkle3 = Sparkle(pixels, speed=0, color=WHITE, num_sparkles=1)
carve_left = Solid(pixel_map[0], color=GREEN)
carve_right = Solid(pixel_map[1], color=RED)
black_left = Solid(pixel_map[0], color=BLACK, name="BLACK")
black_right = Solid(pixel_map[1], color=BLACK)

# Animations Playlist - reorder as desired. AnimationGroups play at the same time
animations = AnimationSequence(
    AnimationGroup(
        fuego,
        fuego2,
        lava,
        sparkle,
        ),
    chase,
    rainbow_chase2,
    rainbow,
    AnimationGroup(
        rainbow_comet,
        sparkle3,
        ),
    AnimationGroup(
        rainbow_comet2,
        sparkle3,
        ),
    AnimationGroup(
        sparkle,
        strum,
        ),
    AnimationGroup(
        sparkle2,
        rainbow_comet3,
        ),
    AnimationGroup(
        black_left,
        black_right,
        ),
    black_left,
    auto_clear=True,
    auto_reset=True,
)


MODE = 0
LASTMODE = 1
i = 0

# Main loop
while True:
    i = (i + 0.5) % 256  # run from 0 to 255
    TILT_COLOR = colorwheel(i)
    if MODE == 0:  # If currently off...
        enable.value = True
        power_on(POWER_ON_DURATION)  # Power up!
        MODE = LASTMODE

    elif MODE >= 1:  # If not OFF MODE...
    # Read button
        cur_state = btn.value
        if cur_state != prev_state:
            if not cur_state:
                animations.next()
                print("BTN is down")
            else:
                print("BTN is up")
        prev_state = cur_state
        # Read accelerometer
        x, y, z = accel.acceleration
        accel_total = z # x=tilt, y=rotate
        accel_total_y = y # x=tilt, y=rotate
        print(accel_total_y)
        if accel_total > THRESHOLD:
            print("THRESHOLD: ", accel_total)
        if MODE == 1:
            animations.animate()
            if animations.current_animation.name == "BLACK":
                MODE = 2
        if MODE == 2:
            if y > CARVE_THRESHOLD:
                black_right.animate()
                carve_left.animate()
            if y < (CARVE_THRESHOLD * -1):
                black_left.animate()
                carve_right.animate()
            #print (MODE)
            cur_state = btn.value
            if cur_state != prev_state:
                if not cur_state:
                    MODE = 1
