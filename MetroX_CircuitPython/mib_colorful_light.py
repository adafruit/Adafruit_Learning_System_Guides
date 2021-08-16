"""
'mib_colorful_light.py'.

=================================================
random RGB LED color selection with pulseio

requires:
-simpleio
"""

import time
import random
import board
import pwmio
from simpleio import map_range

RED = [100, 0, 0]
ORANGE = [50, 5, 0]
YELLOW = [100, 100, 0]
GREEN = [0, 100, 0]
TEAL = [0, 50, 5]
CYAN = [0, 100, 100]
BLUE = [0, 0, 100]
MAGENTA = [100, 0, 100]
WHITE = [100, 100, 100]
BLACK = [0, 0, 0]
color_array = [RED, ORANGE, YELLOW, GREEN, TEAL, BLUE, CYAN, MAGENTA, WHITE, BLACK]

red_led = pwmio.PWMOut(board.D9)
green_led = pwmio.PWMOut(board.D10)
blue_led = pwmio.PWMOut(board.D11)

rgb_led_array = [red_led, green_led, blue_led]

def set_color(color):
    """sets the rgb led's cathodes."""
    print("Setting (%0.2f, %0.2f, %0.2f)" % (color[0], color[1], color[2]))
    rgb_led_array[0].duty_cycle = int(map_range(color[0], 0, 100, 65535, 0))
    rgb_led_array[1].duty_cycle = int(map_range(color[1], 0, 100, 65535, 0))
    rgb_led_array[2].duty_cycle = int(map_range(color[2], 0, 100, 65535, 0))


def random_color():
    """generates a random color."""
    rnd_color = random.randrange(len(color_array))
    set_color(color_array[rnd_color])

while True:
    random_color()
    time.sleep(2)
