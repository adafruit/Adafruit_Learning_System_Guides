# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Keypad and rotary encoder example for Adafruit MacroPad"""
import board
import digitalio
import rotaryio
import neopixel
import keypad
from rainbowio import colorwheel


key_pins = (board.KEY1, board.KEY2, board.KEY3, board.KEY4, board.KEY5, board.KEY6,
            board.KEY7, board.KEY8, board.KEY9, board.KEY10, board.KEY11, board.KEY12)
keys = keypad.Keys(key_pins, value_when_pressed=False, pull=True)

encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)
button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 12, brightness=0.2)

last_position = None
while True:
    if not button.value:
        pixels.brightness = 1.0
    else:
        pixels.brightness = 0.2

    position = encoder.position
    if last_position is None or position != last_position:
        print("Rotary:", position)
    last_position = position

    color_value = (position * 2) % 255

    event = keys.events.get()
    if event:
        print(event)
        if event.pressed:
            pixels[event.key_number] = colorwheel(color_value)
        else:
            pixels[event.key_number] = 0
