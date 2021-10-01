# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython ANO Rotary Encoder and NeoPixel Ring example.
"""
import board
import digitalio
import rotaryio
import neopixel

# The pin assignments for the breakout pins. Update this is you are not using a Feather.
ENCA = board.D13
ENCB = board.D12
COMA = board.D11
SW1 = board.D10
SW2 = board.D9
SW3 = board.D6
SW4 = board.D5
SW5 = board.SCL
COMB = board.SDA

# Rotary encoder setup
encoder = rotaryio.IncrementalEncoder(ENCA, ENCB)
last_position = None

# NeoPixel ring setup. Update num_pixels if using a different ring.
num_pixels = 12
pixels = neopixel.NeoPixel(board.A0, num_pixels, auto_write=False)

# Set the COMA and COMB pins LOW. This is only necessary when using the direct-to-Feather or other
# GPIO-based wiring method. If connecting COMA and COMB to ground, you do not need to include this.
com_a = digitalio.DigitalInOut(COMA)
com_a.switch_to_output()
com_a = False
com_b = digitalio.DigitalInOut(COMB)
com_b.switch_to_output()
com_b = False

# Button pin setup
button_pins = (SW1, SW2, SW3, SW4, SW5)
buttons = []
for button_pin in button_pins:
    pin = digitalio.DigitalInOut(button_pin)
    pin.switch_to_input(digitalio.Pull.UP)
    buttons.append(pin)

while True:
    position = encoder.position
    if last_position is None or position != last_position:
        print("Position: {}".format(position))
        last_position = position

    pixels.fill((0, 0, 0))
    pixels[position % num_pixels] = (0, 150, 0)

    if not buttons[0].value:
        print("Center button!")
        pixels.fill((100, 100, 100))

    if not buttons[1].value:
        print("Up button!")
        pixels[0] = (150, 0 ,0)

    if not buttons[2].value:
        print("Left button!")
        pixels[3] = (150, 0, 0)

    if not buttons[3].value:
        print("Down button!")
        pixels[6] = (150, 0, 0)

    if not buttons[4].value:
        print("Right button!")
        pixels[9] = (150, 0, 0)

    pixels.show()
