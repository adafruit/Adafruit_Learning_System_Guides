# CircuitPython demo - NeoPixel

import time
import board
import neopixel

pixel_pin = board.A1
num_pixels = 8

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, bpp=4, brightness=0.3)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0, 0
    if pos < 85:
        return int(255 - pos*3), int(pos*3), 0, 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos*3), int(pos*3), 0
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos*3)), 0


def color_chase(wait):
    for i in range(num_pixels):
        pixels[i] = RED
        time.sleep(wait)
    time.sleep(0.5)

    for i in range(num_pixels):
        pixels[i] = YELLOW
        time.sleep(wait)
    time.sleep(0.5)

    for i in range(num_pixels):
        pixels[i] = GREEN
        time.sleep(wait)
    time.sleep(0.5)

    for i in range(num_pixels):
        pixels[i] = CYAN
        time.sleep(wait)
    time.sleep(0.5)

    for i in range(num_pixels):
        pixels[i] = BLUE
        time.sleep(wait)
    time.sleep(0.5)

    for i in range(num_pixels):
        pixels[i] = PURPLE
        time.sleep(wait)
    time.sleep(0.5)


def rainbow_cycle(wait):
    for j in range(255):
        rc_i = j % num_pixels
        rc_index = int((rc_i * 256 / num_pixels) + j)
        pixels[rc_i] = wheel(rc_index & 255)
        time.sleep(wait)


RED = (255, 0, 0, 0)
YELLOW = (255, 150, 0, 0)
GREEN = (0, 255, 0, 0)
CYAN = (0, 255, 255, 0)
BLUE = (0, 0, 255, 0)
PURPLE = (180, 0, 255, 0)

while True:
    pixels.fill(RED)
    time.sleep(1)  # Increase or decrease to change the speed of the solid color change.
    pixels.fill(GREEN)
    time.sleep(1)
    pixels.fill(BLUE)
    time.sleep(1)

    color_chase(0.1)  # Increase the number to slow down the color chase

    rainbow_cycle(0)  # Increase the number to slow down the rainbow
