# Simple paint program for Trellis M4 Express
# Press any button it will cycle through a palette of colors!
#
# Mike Barela for Adafruit Industries   November, 2018
#
import time
import adafruit_trellism4

trellis = adafruit_trellism4.TrellisM4Express()

# See https://www.w3schools.com/colors/colors_picker.asp
RED = 0xFF0000
ORANGE = 0xB34700
YELLOW = 0xFFFF00
OLIVE = 0x66DD00
GREEN = 0x008000
AQUA = 0x00FF66
TEAL = 0x00BFFF
BLUE = 0x0080FF
NAVY = 0x000080
MAROON = 0x800000
PURPLE = 0x800080
PINK = 0xFF66B3
WHITE = 0xFFFFFF
BLACK = 0x000000

color_cycle = [BLACK, RED, ORANGE, YELLOW, OLIVE, GREEN, AQUA,
               TEAL, BLUE, NAVY, MAROON, PURPLE, PINK, WHITE]

colors = 13  # Number of colors in color_cycle

key_state = [0 for _ in range(32)]  # All keys are color 0 (BLACK)

trellis.pixels.fill(BLACK)  # Turn off all pixels

current_press = set()
while True:
    pressed = set(trellis.pressed_keys)
    for press in pressed - current_press:
        if press:
            print("Pressed:", press)
            x, y = press
            pixel = (press[1] * 8) + press[0]
            if key_state[pixel] == colors:  # If we're at white
                key_state[pixel] = 0        #  Set back to black
            else:
                key_state[pixel] += 1       # Use next color
            # Change the pushed pixel to the next color
            trellis.pixels[x, y] = color_cycle[key_state[pixel]]

    time.sleep(0.08)
    current_press = pressed
