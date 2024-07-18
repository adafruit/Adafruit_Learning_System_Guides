# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import keypad
import rotaryio
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# neopixel colors
RED = (255, 0, 0)
ORANGE = (255, 127, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
AQUA = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (127, 0, 255)
PINK = (255, 0, 255)
OFF = (0, 0, 0)
# axis states selected with keys 9-11
axis_states = [0, "x", "y", "z"]
state = axis_states[0]
# keymap for key matrix
keymap = {
    (0): (axis_states[0], [Keycode.HOME], RED), # HOME X/Y
    (1): (axis_states[0], [Keycode.END], ORANGE), # HOME Z
    (2): (axis_states[0], (Keycode.HOME, Keycode.END), YELLOW), # HOME ALL

    (3): (axis_states[0], (Keycode.SHIFT, Keycode.A), GREEN), # SHORTCUT A
    (4): (axis_states[0], (Keycode.SHIFT, Keycode.B), AQUA), # SHORTCUT B
    (5): (axis_states[0], (Keycode.SHIFT, Keycode.C), BLUE), # SHORTCUT C

    (6): (axis_states[0], [Keycode.TWO], AQUA), # SET STEPS 1MM
    (7): (axis_states[0], [Keycode.THREE], PURPLE), # SET STEPS 10MM
    (8): (axis_states[0], [Keycode.FOUR], PINK), # SET STEPS 100MM

    (9): (axis_states[1], None, RED), # SET X-AXIS STATE
    (10): (axis_states[2], None, GREEN), # SET Y-AXIS STATE
    (11): (axis_states[3], None, BLUE),  # SET Z-AXIS STATE
}
# keymap for encoder based on state; pos = [0], neg = [1]
encoder_map = {
    ("x"): ([Keycode.RIGHT_ARROW], [Keycode.LEFT_ARROW]),
    ("y"): ([Keycode.UP_ARROW], [Keycode.DOWN_ARROW]),
    ("z"): ([Keycode.W], [Keycode.S]),
}
# make a keyboard
kbd = Keyboard(usb_hid.devices)
# key matrix
COLUMNS = 3
ROWS = 4
keys = keypad.KeyMatrix(
    row_pins=(board.D12, board.D11, board.D10, board.D9),
    column_pins=(board.A0, board.A1, board.A2),
    columns_to_anodes=False,
)
# neopixels and key num to pixel function
pixels = neopixel.NeoPixel(board.D5, 12, brightness=0.3)
def key_to_pixel_map(key_number):
    row = key_number // COLUMNS
    column = key_number % COLUMNS
    if row % 2 == 1:
        column = COLUMNS - column - 1
    return row * COLUMNS + column
pixels.fill(OFF)  # Begin with pixels off.

# make an encoder
encoder = rotaryio.IncrementalEncoder(board.A3, board.A4)
last_position = 0

while True:
    # poll for key event
    key_event = keys.events.get()
    # get position of encoder
    position = encoder.position
    # if position changes..
    if position != last_position:
        # ..and it increases..
        if position > last_position:
            # ..and state is x:
            if state is axis_states[1]:
                kbd.press(*encoder_map[state][0])
            # ..and state is y:
            if state is axis_states[2]:
                kbd.press(*encoder_map[state][0])
            # ..and state is z:
            if state is axis_states[3]:
                kbd.press(*encoder_map[state][0])
        # ..and it decreases..
        if position < last_position:
            # ..and state is x:
            if state is axis_states[1]:
                kbd.press(*encoder_map[state][1])
            # ..and state is y:
            if state is axis_states[2]:
                kbd.press(*encoder_map[state][1])
            # ..and state is z:
            if state is axis_states[3]:
                kbd.press(*encoder_map[state][1])
        # print(position)
        # release all keys
        kbd.release_all()
    # update last_position
    last_position = position
    # if a key event..
    if key_event:
        # print(key_event)
        # ..and it's pressed..
        if key_event.pressed:
            # ..and it's keys 0-8, send key presses from keymap:
            if keymap[key_event.key_number][0] is axis_states[0]:
                state = axis_states[0]
                kbd.press(*keymap[key_event.key_number][1])
            # ..and it's key 9, set state to x
            if keymap[key_event.key_number][0] is axis_states[1]:
                state = axis_states[1]
                pixels[key_to_pixel_map(10)] = OFF
                pixels[key_to_pixel_map(11)] = OFF
            # ..and it's key 10, set state to y
            if keymap[key_event.key_number][0] is axis_states[2]:
                state = axis_states[2]
                pixels[key_to_pixel_map(9)] = OFF
                pixels[key_to_pixel_map(11)] = OFF
            # ..and it's key 11, set state to z
            if keymap[key_event.key_number][0] is axis_states[3]:
                state = axis_states[3]
                pixels[key_to_pixel_map(9)] = OFF
                pixels[key_to_pixel_map(10)] = OFF
            # turn on neopixel for key with color from keymap
            pixels[key_to_pixel_map(key_event.key_number)] = keymap[key_event.key_number][2]
        # ..and it's released..
        if key_event.released:
            # if it's key 0-8, release the key press and turn off neopixel
            if keymap[key_event.key_number][0] is axis_states[0]:
                kbd.release(*keymap[key_event.key_number][1])
                pixels.fill(OFF)
