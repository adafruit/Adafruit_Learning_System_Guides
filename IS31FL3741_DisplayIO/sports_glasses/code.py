# SPDX-FileCopyrightText: 2022 Mark Komus
#
# SPDX-License-Identifier: MIT

import random
import time
import board
import busio
import digitalio
import displayio
import framebufferio
import is31fl3741
from adafruit_is31fl3741.is31fl3741_PixelBuf import IS31FL3741_PixelBuf
from adafruit_is31fl3741.led_glasses_map import (
    glassesmatrix_ledmap_no_ring,
    left_ring_map_no_inner,
    right_ring_map_no_inner,
)
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_led_animation.animation.chase import Chase
from adafruit_debouncer import Debouncer

# List of possible messages to display. Randomly chosen
MESSAGES = (
    "GO TEAM GO",
    "WE ARE NUMBER 1",
    "I LIKE THE HALFTIME SHOW",
)

# Colors used for the text and ring lights
BLUE_TEXT = (0, 20, 255)
BLUE_RING = (0, 10, 120)
YELLOW_TEXT = (220, 210, 0)
YELLOW_RING = (150, 140, 0)


def ScrollMessage(text, color, repeat):
    """Scroll a message across the eyeglasses a set number of times"""
    text_area.text = text
    text_area.color = color

    # Start the message just off the side of the glasses
    x = display.width
    text_area.x = x

    # Determine the width of the message to scroll
    width = text_area.bounding_box[2]

    for _ in range(repeat):
        while x != -width:
            x = x - 1
            text_area.x = x

            # Update the switch and if it has been pressed abort scrolling this message
            switch.update()
            if switch.value is False:
                return

            time.sleep(0.025) # adjust to change scrolling speed
        x = display.width


def Score(text, color, ring_color, repeat):
    """Show a scrolling text message and animated effects on the eye rings.
    The messages scrolls left to right, then right to left while the eye rings
    are animated using the adafruit_led_animation library."""

    # Set up a led animation chase sequence for both eyelights
    chase_left = Chase(left_eye, speed=0.11, color=ring_color, size=8, spacing=4)
    chase_right = Chase(right_eye, speed=0.07, color=ring_color, size=8, spacing=4)

    text_area.text = text
    text_area.color = color

    x = display.width
    text_area.x = x

    width = text_area.bounding_box[2]

    for _ in range(repeat):
        # Scroll the text left and animate the eyes
        while x != -width:
            x = x - 1
            text_area.x = x
            chase_left.animate()
            chase_right.animate()
            time.sleep(0.008) # adjust to change scrolling speed
        # Scroll the text right and animate the eyes
        while x != display.width:
            x = x + 1
            text_area.x = x
            chase_left.animate()
            chase_right.animate()
            time.sleep(0.008) # adjust to change scrolling speed


# Remove any existing displays
displayio.release_displays()

# Set up the top button used to trigger a special message when pressed
switch_pin = digitalio.DigitalInOut(board.SWITCH)
switch_pin.direction = digitalio.Direction.INPUT
switch_pin.pull = digitalio.Pull.UP
switch = Debouncer(switch_pin)

# Initialize the LED Glasses
#
# In this example scale is set to True. When True the logical display is
# three times the physical display size and scaled down to allow text to
# look more natural for small display sizes. Hence the display is created
# as 54x15 when the physical display is 18x5.
#
i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)
is31 = is31fl3741.IS31FL3741(i2c=i2c)
is31_framebuffer = is31fl3741.IS31FL3741_FrameBuffer(
    is31, 54, 15, glassesmatrix_ledmap_no_ring, scale=True, gamma=True
)
display = framebufferio.FramebufferDisplay(is31_framebuffer, auto_refresh=True)

# Set up the left and right eyelight rings
# init is set to False as the IS31FL3741_FrameBuffer has already initialized the IS31FL3741 driver
left_eye = IS31FL3741_PixelBuf(
    is31, left_ring_map_no_inner, init=False, auto_write=False
)
right_eye = IS31FL3741_PixelBuf(
    is31, right_ring_map_no_inner, init=False, auto_write=False
)

# Dim the display. Full brightness is BRIGHT
is31_framebuffer.brightness = 0.2

# Load the font to be used - scrolly only has upper case letters
font = bitmap_font.load_font("scrolly.bdf")

# Set up the display elements
text_area = label.Label(font, text="", color=(0, 0, 0))
text_area.y = 8
group = displayio.Group()
group.append(text_area)
display.show(group)

while True:
    # Run the debouncer code to get the updated switch value
    switch.update()

    # If the switch has been pressed interrupt start a special message
    if switch.value is False:  # False means the switch has been pressed
        Score("SCORE!", YELLOW_TEXT, BLUE_RING, 2)

    # If the switch is not pressed pick a random message and scroll it
    left_eye.fill(BLUE_RING)
    right_eye.fill(BLUE_RING)
    left_eye.show()
    right_eye.show()
    ScrollMessage(random.choice(MESSAGES), YELLOW_TEXT, 2)
