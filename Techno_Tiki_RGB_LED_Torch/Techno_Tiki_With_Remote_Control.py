# Techno-Tiki RGB LED Torch with IR Remote Control
# Created by Tony DiCola for Arduino
# Ported to CircuitPython by Mikey Sklar
#
# See guide at: https://learn.adafruit.com/techno-tiki-rgb-led-torch/overview
#
# Released under a MIT license: http://opensource.org/licenses/MIT

import time
import board
import neopixel

pixel_pin = board.D1    # Pin where NeoPixels are connected

pixel_count = 6         # Number of NeoPixels

speed = .1              # Animation speed (in seconds).
                        # This is how long to spend in a single animation frame.
                        # Higher values are slower.
                        # Good values to try are 400, 200, 100, 50, 25, etc.

animation = 0           # Type of animation, can be one of these values:
                        # 0 - Solid color pulse
                        # 1 - Moving color pulse


brightness = 1.0        # 0-1, higher number is brighter

ir_pin = board.D2

# Adafruit IR Remote Codes:
# Button       Code         Button  Code
# -----------  ------       ------  -----
# VOL-:        [255, 2, 255, 0]		0/10+:	0x000C
# Play/Pause:  [255, 2, 127, 128]	1:	0x0010
# VOL+:        [255, 2, 191, 64]	2:	0x0011
# SETUP:       [255, 2, 223, 32]	3:	0x0012
# STOP/MODE:   [255, 2, 159, 96]	4:	0x0014
# UP:          [255, 2, 95, 160]	5:      0x0015
# DOWN:        0x000D       6:      0x0016
# LEFT:        0x0008       7:      0x0018
# RIGHT:       0x000A       8:      0x0019
# ENTER/SAVE:  0x0009       9:      0x001A
# Back:        0x000E

color_change = 0x000A		# Button that cycles through color animations.
animation_change = 0x0008	# Button that cycles through animation types (only two supported).
speed_change = 0x0005		# Button that cycles through speed choices.
power_off = 0x0000		# Button that turns off/sleeps the pixels.
power_on = 0x0002		# Button that turns on the pixels.  Must be pressed twice to register!


# Build lookup table/palette for the color animations so they aren't computed at runtime.
# The colorPalette two-dimensional array below has a row for each color animation and a column
# for each step within the animation.  Each value is a 24-bit RGB color.  By looping through
# the columns of a row the colors of pixels will animate.
color_steps = 8         # Number of steps in the animation.
color_count = 25 	# number of columns/steps

color_palette = [
# Complimentary colors
([255, 0, 0], [218, 36, 36], [182, 72, 72], [145, 109, 109], [109, 145, 145], [72, 182, 182], [36, 218, 218], [0, 255, 255]), # red cyan
([255, 255, 0], [218, 218, 36], [182, 182, 72], [145, 145, 109], [109, 109, 145], [72, 72, 182], [36, 36, 218], [0, 0, 255]), # yellow blue
([0, 255, 0], [36, 218, 36], [72, 182, 72], [109, 145, 109], [145, 109, 145], [182, 72, 182], [218, 36, 218], [255, 0, 255]), # green magenta
]

# Adjacent colors (on color wheel).
#
# yello green
# ([255, 255, 0], [218, 255, 0], [182, 255, 0], [145, 255, 0], [109, 255, 0], [72, 255, 0], [36, 255, 0], [0, 255, 0])

# green cyan
# ([0, 255, 0], [0, 255, 36], [0, 255, 72], [0, 255, 109], [0, 255, 145], [0, 255, 182], [0, 255, 218], [0, 255, 255])

# cyan blue
# ([0, 255, 255], [0, 218, 255], [0, 182, 255], [0, 145, 255], [0, 109, 255], [0, 72, 255], [0, 36, 255], [0, 0, 255])

# blue magenta
# ([0, 0, 255], [36, 0, 255], [72, 0, 255], [109, 0, 255], [145, 0, 255], [182, 0, 255], [218, 0, 255], [255, 0, 255])

# magenta red
# ([255, 0, 255], [255, 0, 218], [255, 0, 182], [255, 0, 145], [255, 0, 109], [255, 0, 72], [255, 0, 36], [255, 0, 0])

# Other combos
#
# red green
# ([255, 0, 0], [218, 36, 0], [182, 72, 0], [145, 109, 0],  [109, 145, 0], [72, 182, 0], [36, 218, 0], [0, 255, 0])

# yellow cyan
# ([255, 255, 0], [218, 255, 36], [182, 255, 72], [145, 255, 109], [109, 255, 145], [72, 255, 182], [36, 255, 218], [0, 255, 255]) 

# green blue
# ([0, 255, 0], [0, 218, 36], [0, 182, 72], [0, 145, 109],  [0, 109, 145], [0, 72, 182], [0, 36, 218], [0, 0, 255])

# cyan magenta
# ([0, 255, 255], [36, 218, 255], [72, 182, 255], [109, 145, 255],  [145, 109, 255], [182, 72, 255], [218, 36, 255], [255, 0, 255])

# blue red
# ([0, 0, 255], [36, 0, 218], [72, 0, 182], [109, 0, 145], [145, 0, 109], [182, 0, 72], [218, 0, 36], [255, 0, 0])

# magenta yellow
# ([255, 0, 255], [255, 36, 218], [255, 72, 182], [255, 109, 145], [255, 145, 109], [255, 182, 72], [255, 218, 36], [255, 255, 0])

# Solid colors fading to dark.
#
# red
# ([255, 0, 0], [223, 0, 0], [191, 0, 0], [159, 0, 0], [127, 0, 0], [95, 0, 0], [63, 0, 0], [31, 0, 0])

# orange
# ([255, 153, 0], [223, 133, 0], [191, 114, 0], [159, 95, 0], [127, 76, 0], [95, 57, 0], [63, 38, 0], [31, 19, 0])

# yellow
# ([255, 255, 0], [223, 223, 0], [191, 191, 0], [159, 159, 0], [127, 127, 0], [95, 95, 0], [63, 63, 0], [31, 31, 0])

# green
# ([0, 255, 0], [0, 223, 0], [0, 191, 0], [0, 159, 0], [0, 127, 0], [0, 95, 0], [0, 63, 0], [0, 31, 0])

# blue
# ([0, 0, 255], [0, 0, 223], [0, 0, 191], [0, 0, 159], [0, 0, 127], [0, 0, 95], [0, 0, 63], [0, 0, 31])

# indigo
# ([75, 0, 130], [65, 0, 113], [56, 0, 97], [46, 0, 81], [37, 0, 65], [28, 0, 48], [18, 0, 32], [9, 0, 16])

# violet
# ([139, 0, 255], [121, 0, 223], [104, 0, 191], [86, 0, 159], [69, 0, 127], [52, 0, 95], [34, 0, 63], [17, 0, 31])

# white
# ([255, 255, 255], [223, 223, 223], [191, 191, 191], [159, 159, 159], [127, 127, 127], [95, 95, 95], [63, 63, 63], [31, 31, 31])

# rainbow colors
# ([255, 0, 0], [255, 153, 0], [255, 255, 0], [0, 255, 0], [0, 0, 255], [75, 0, 130], [139, 0, 255], [255, 255, 255])

# List of animations speeds (in seconds).  This is how long an animation spends before
# changing to the next step.  Higher values are slower.
speeds = [.4, .2, .1, .05, .025]

# Global state used by the sketch
strip = neopixel.NeoPixel(pixel_pin, pixel_count, brightness=brightness, auto_write=False)
receiver_fell = False
color_index = 0
animation_index = 0
speed_index = 2

def handle_remote():
# Check if an IR remote code was received and perform the appropriate action.
# First read a code.


def readNEC(result) {
# Check if a NEC IR remote command can be read and decoded from the IR receiver.
# If the command is decoded then the result is stored in the provided pointer and
# true is returned.  Otherwise if the command was not decoded then false is returned.
# First check that a falling signal was detected and start reading pulses.
 
 


while True:  # Loop forever...

    # Main loop will update all the pixels based on the animation.
    for i in range(pixel_count):

        # Animation 0, solid color pulse of all pixels.
        if animation_index == 0:
            current_step = (time.monotonic() / speed) % (color_steps * 2 - 2)
            if current_step >= color_steps:
                current_step = color_steps - (current_step - (color_steps - 2))

        # Animation 1, moving color pulse.  Use position to change brightness.
        elif animation == 1:
            current_step = (time.monotonic() / speed + i) % (color_steps * 2 - 2);
            if current_step >= color_steps:
                current_step = color_steps - (current_step - (color_steps - 2))

        strip[i] = color_animation[int(current_step)]

	# Next check for any IR remote commands.
	handle_remote()
    # Show the updated pixels.
    strip.show()
	# Next check for any IR remote commands.
	handle_remote()
