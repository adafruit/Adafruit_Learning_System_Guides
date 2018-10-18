"""
Main signal generator code.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import rotaryio
import board
import digitalio
from display import Display
from debouncer import Debouncer
from generator import Generator
import shapes




def change_frequency(frequency, delta):
    return min(20000, max(150, frequency + delta))


def change_shape(shape):
    return (shape + 1) % shapes.NUMBER_OF_SHAPES


def get_encoder_change(encoder, pos):
    new_position = encoder.position
    if pos is None:
        return (new_position, 0)
    else:
        return (new_position, new_position - pos)


def run():
    display = Display()
    generator = Generator()
    button_a = Debouncer(board.D9, digitalio.Pull.UP, 0.01)
    button_b = Debouncer(board.D6, digitalio.Pull.UP, 0.01)
    button_c = Debouncer(board.D5, digitalio.Pull.UP, 0.01)
    encoder_button = Debouncer(board.D12, digitalio.Pull.UP, 0.01)
    encoder = rotaryio.IncrementalEncoder(board.D10, board.D11)

    current_position = None               # current encoder position
    change = 0                            # the change in encoder position
    delta = 0                             # how much to change the frequency by
    shape = shapes.SINE                          # the active waveform
    frequency = 440                       # the current frequency

    display.update_shape(shape)           # initialize the display contents
    display.update_frequency(frequency)

    while True:
        encoder_button.update()
        button_a.update()
        button_b.update()
        button_c.update()
        current_position, change = get_encoder_change(encoder, current_position)

        if change != 0:
            if not button_a.value:
                delta = change * 1000
            elif not button_b.value:
                delta = change * 100
            elif not button_c.value:
                delta = change * 10
            else:
                delta = change
            frequency = change_frequency(frequency, delta)

        if encoder_button.fell:
            shape = change_shape(shape)

        display.update_shape(shape)
        display.update_frequency(frequency)
        generator.update(shape, frequency)


run()
