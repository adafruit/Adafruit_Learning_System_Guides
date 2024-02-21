# SPDX-FileCopyrightText: 2020 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Basic NeoPixel LED animations for the QT Py."""
import time
import board
from rainbowio import colorwheel
import neopixel

# Update this to match the pin to which you connected the NeoPixels
pixel_pin = board.A3
# Update this to match the number of NeoPixels connected
num_pixels = 30

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, auto_write=False)
# Set to 0-1 to change the brightness of the NeoPixels
pixels.brightness = 0.2


def blink(color, wait):
    """Blink animation. Blinks all pixels."""
    pixels.fill(color)
    pixels.show()
    time.sleep(wait)
    pixels.fill((0, 0, 0))
    pixels.show()
    time.sleep(wait)


def chase(color, spacing=3, iteration_step=1):
    """Theatre chase animation. Chases across all pixels."""
    if spacing < 2:
        raise ValueError("Spacing must be greater than 1 to show chase pattern.")

    # Use modulo division to create the spacing between pixels.
    chase_pixel = iteration_step % spacing
    # Loop over pixels and turn on expected pixels to provided color.
    for pixel in range(0, len(pixels), spacing):
        # If the pixel is outside the total pixel range, break.
        if pixel + chase_pixel > len(pixels) - 1:
            break
        pixels[pixel + chase_pixel] = color
    pixels.show()

    # Loop over pixels and turn off expected pixels.
    for pixel in range(0, len(pixels), spacing):
        # If the pixel is outside the total pixel range, break.
        if pixel + chase_pixel > len(pixels) - 1:
            break
        pixels[pixel + chase_pixel] = (0, 0, 0)


def color_wipe(color, wait):
    """Color wipe animation. Wipes across all pixels."""
    for pixel in range(num_pixels):
        pixels[pixel] = color
        time.sleep(wait)
        pixels.show()
    time.sleep(0.5)


def rainbow_cycle(wait):
    """Rainbow cycle animation. Cycles across all pixels."""
    for color_index in range(255):
        for pixel in range(num_pixels):
            pixel_index = (pixel * 256 // num_pixels) + color_index
            pixels[pixel] = colorwheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)


RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)

while True:
    # Blink 5 times. Increase or decrease the range for more or less blinking.
    for blinks in range(5):
        blink(RED, 0.5)  # Increase number to slow down blinking, decrease to speed up.

    # Chase. Increase or decrease the range for longer or shorter chase animation.
    for step in range(50):
        chase(PURPLE, spacing=4, iteration_step=step)
        time.sleep(0.05)

    # Fill all pixels.
    pixels.fill(RED)
    pixels.show()
    # Increase or decrease the time to change the speed of the solid color change in seconds.
    time.sleep(0.5)
    pixels.fill(GREEN)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(BLUE)
    pixels.show()
    time.sleep(0.5)

    # Color wipe.
    color_wipe(YELLOW, 0.01)  # Increase the number to slow down the color chase.
    color_wipe(CYAN, 0.01)
    color_wipe(PURPLE, 0.01)

    # Rainbow cycle.
    rainbow_cycle(0)  # Increase the number to slow down the rainbow.
