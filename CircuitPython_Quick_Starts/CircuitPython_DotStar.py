# CircuitPython demo - Dotstar

import time
import board
import adafruit_dotstar

num_pixels = 72
pixels = adafruit_dotstar.DotStar(board.A1, board.A2, num_pixels, brightness=0.1, auto_write=True)


def slice_alternating(wait):
    pixels[::2] = [RED] * (num_pixels // 2)
    time.sleep(wait)
    pixels[1::2] = [ORANGE] * (num_pixels // 2)
    time.sleep(wait)
    pixels[::2] = [YELLOW] * (num_pixels // 2)
    time.sleep(wait)
    pixels[1::2] = [GREEN] * (num_pixels // 2)
    time.sleep(wait)
    pixels[::2] = [TEAL] * (num_pixels // 2)
    time.sleep(wait)
    pixels[1::2] = [CYAN] * (num_pixels // 2)
    time.sleep(wait)
    pixels[::2] = [BLUE] * (num_pixels // 2)
    time.sleep(wait)
    pixels[1::2] = [PURPLE] * (num_pixels // 2)
    time.sleep(wait)
    pixels[::2] = [MAGENTA] * (num_pixels // 2)
    time.sleep(wait)
    pixels[1::2] = [WHITE] * (num_pixels // 2)
    time.sleep(wait)


def slice_rainbow(wait):
    pixels[::6] = [RED] * (num_pixels // 6)
    time.sleep(wait)
    pixels[1::6] = [ORANGE] * (num_pixels // 6)
    time.sleep(wait)
    pixels[2::6] = [YELLOW] * (num_pixels // 6)
    time.sleep(wait)
    pixels[3::6] = [GREEN] * (num_pixels // 6)
    time.sleep(wait)
    pixels[4::6] = [BLUE] * (num_pixels // 6)
    time.sleep(wait)
    pixels[5::6] = [PURPLE] * (num_pixels // 6)
    time.sleep(wait)


RED = (255, 0, 0)
YELLOW = (255, 150, 0)
ORANGE = (255, 40, 0)
GREEN = (0, 255, 0)
TEAL = (0, 255, 120)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
MAGENTA = (255, 0, 20)
WHITE = (255, 255, 255)

while True:
    pixels.fill(RED)
    time.sleep(0.5)  # Change this number to change how long it stays on each solid color.
    pixels.fill(ORANGE)
    time.sleep(0.5)
    pixels.fill(YELLOW)
    time.sleep(0.5)
    pixels.fill(GREEN)
    time.sleep(0.5)
    pixels.fill(TEAL)
    time.sleep(0.5)
    pixels.fill(CYAN)
    time.sleep(0.5)
    pixels.fill(BLUE)
    time.sleep(0.5)
    pixels.fill(PURPLE)
    time.sleep(0.5)
    pixels.fill(MAGENTA)
    time.sleep(0.5)
    pixels.fill(WHITE)
    time.sleep(0.5)

    slice_alternating(0.1)  # Increase or decrease this to speed up or slow down the animation.

    pixels.fill(WHITE)
    time.sleep(0.5)

    slice_rainbow(0.1)  # Increase or decrease this to speed up or slow down the animation.

    time.sleep(0.5)
