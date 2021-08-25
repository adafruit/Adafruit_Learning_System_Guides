# SPDX-FileCopyrightText: 2021 Tod Kurt @todbot and John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# QT Py encoder based on https://github.com/todbot/qtpy-knob
# Retroreflective chromakey light ring
#                 Mount a rotary encoder directly to an Adafruit QT Py,
#                 add some neopixels to get a color/brightness controller
#
import time
import board
from digitalio import DigitalInOut, Direction, Pull
import neopixel
import rotaryio


dim_val = 0.2

NUM_PIX = 24

PIX_TYPE = "RGB"  # RGB or RGBW

if PIX_TYPE == "RGB":
    ORDER = (1, 0, 2)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
else:
    ORDER = (1, 0, 2, 3)
    GREEN = (0, 255, 0, 0)
    BLUE = (0, 0, 255, 0)
    WHITE = (0, 0, 0, 255)
    BLACK = (0, 0, 0, 0)


colors = [GREEN, BLUE, WHITE, BLACK]
current_color = 0


ring = neopixel.NeoPixel(
    board.MISO, NUM_PIX, brightness=0.2, auto_write=False, pixel_order=ORDER
)
ring.fill(colors[current_color])
ring.show()

# button of rotary encoder
button = DigitalInOut(board.MOSI)
button.pull = Pull.UP

# Use pin A2 as a fake ground for the rotary encoder
fakegnd = DigitalInOut(board.A2)
fakegnd.direction = Direction.OUTPUT
fakegnd.value = False

encoder = rotaryio.IncrementalEncoder(board.A3, board.A1)

print("---Chromakey Light Ring---")

last_encoder_val = encoder.position
ring_pos = 0
rainbow_pos = 0
last_time = time.monotonic()
ring_on = True

while True:
    encoder_diff = last_encoder_val - encoder.position  # encoder clicks since last read
    last_encoder_val = encoder.position

    if button.value is False:  # button pressed
        current_color = (current_color + 1) % len(colors)
        ring.fill(colors[current_color])
        ring.show()
        time.sleep(0.5)  # debounce

    else:
        if encoder_diff > 0:
            if dim_val >= 0.01:
                dim_val = (dim_val - 0.01) % 1.0
                ring.brightness = dim_val
                ring.show()
        elif encoder_diff < 0:
            if dim_val <= 0.99:
                dim_val = (dim_val + 0.01) % 1.0
                ring.brightness = dim_val
                ring.show()

        time.sleep(0.01)
