# SPDX-FileCopyrightText: 2018 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Simple example of sending MIDI via UART to classic DIN-5 (not USB) synth

import adafruit_trellism4
from rainbowio import colorwheel
import board
import busio
midiuart = busio.UART(board.SDA, board.SCL, baudrate=31250, timeout=0.001)
print("MIDI UART EXAMPLE")

trellis = adafruit_trellism4.TrellisM4Express()


for x in range(trellis.pixels.width):
    for y in range(trellis.pixels.height):
        pixel_index = (((y * 8) + x) * 256 // 2)
        trellis.pixels[x, y] = colorwheel(pixel_index & 255)

current_press = set()

while True:
    pressed = set(trellis.pressed_keys)

    for press in pressed - current_press:
        x, y = press
        print("Pressed:", press)
        noteval = 36 + x + (y * 8)
        midiuart.write(bytes([0x90, noteval, 100]))

    for release in current_press - pressed:
        x, y = release
        print("Released:", release)
        noteval = 36 + x + (y * 8)
        midiuart.write(bytes([0x90, noteval, 0]))  # note off

    current_press = pressed
