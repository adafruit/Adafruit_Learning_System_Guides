"""
'colorful_light.py'.

=================================================
RGB LED control with circuitpython
"""

import board
import digitalio

RED = [True, False, False]
GREEN = [False, True, False]
BLUE = [False, False, True]
YELLOW = [True, True, False]
CYAN = [False, True, True]
MAGENTA = [True, False, True]
WHITE = [True, True, True]
BLACK = [False, False, False]
color_array = [RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, WHITE, BLACK]

red_led = digitalio.DigitalInOut(board.D9)
green_led = digitalio.DigitalInOut(board.D10)
blue_led = digitalio.DigitalInOut(board.D11)

rgb_led = [red_led, green_led, blue_led]


for led in rgb_led:
    led.switch_to_output()


def set_color(color):
    """sets the rgb led's cathode value."""
    rgb_led[0].value = not color[0]
    rgb_led[1].value = not color[1]
    rgb_led[2].value = not color[2]


while True:
    set_color(GREEN)
