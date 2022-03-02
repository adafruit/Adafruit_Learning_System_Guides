# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
NeoKey 4x2 Ortho Snap-Apart simple key press NeoPixel demo.
"""
import board
import keypad
import neopixel

COLUMNS = 2
ROWS = 4

pixels = neopixel.NeoPixel(board.D5, 30, brightness=0.3)

keys = keypad.KeyMatrix(
    row_pins=(board.D4, board.A3, board.A2, board.A1),
    column_pins=(board.D13, board.D12),
    columns_to_anodes=False,
)


def key_to_pixel_map(key_number):
    row = key_number // COLUMNS
    column = (key_number % COLUMNS)
    if row % 2 == 1:
        column = COLUMNS - column - 1
    return row * COLUMNS + column


pixels.fill((0, 0, 0))  # Begin with pixels off.
while True:
    key_event = keys.events.get()
    if key_event:
        print(key_event)
        if key_event.pressed:
            pixels[key_to_pixel_map(key_event.key_number)] = (255, 0, 0)
        else:
            pixels.fill((0, 0, 0))
