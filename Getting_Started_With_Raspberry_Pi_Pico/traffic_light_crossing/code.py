# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Traffic light with pedestrian crossing simulator example for Pico. Turns on red, amber and green
LEDs in traffic light-like sequence. When button is pressed, upon light sequence completion, the
red LED turns on and the buzzer beeps to indicate pedestrian crossing is active.

REQUIRED HARDWARE:
* Red LED on pin GP11.
* Amber LED on pin GP14.
* Green LED on pin GP13.
* Button switch on pin GP16.
* Piezo buzzer on pin GP13.
"""
import time
import board
import digitalio
import pwmio

red_led = digitalio.DigitalInOut(board.GP11)
red_led.direction = digitalio.Direction.OUTPUT
amber_led = digitalio.DigitalInOut(board.GP14)
amber_led.direction = digitalio.Direction.OUTPUT
green_led = digitalio.DigitalInOut(board.GP13)
green_led.direction = digitalio.Direction.OUTPUT
button = digitalio.DigitalInOut(board.GP16)
button.switch_to_input(pull=digitalio.Pull.DOWN)
buzzer = pwmio.PWMOut(board.GP12, frequency=660, duty_cycle=0, variable_frequency=True)

button_pressed = False


def waiting_for_button(duration):
    global button_pressed  # pylint: disable=global-statement
    end = time.monotonic() + duration
    while time.monotonic() < end:
        if button.value:
            button_pressed = True


while True:
    if button_pressed:
        red_led.value = True
        for _ in range(10):
            buzzer.duty_cycle = 2 ** 15
            waiting_for_button(0.2)
            buzzer.duty_cycle = 0
            waiting_for_button(0.2)
        button_pressed = False
    red_led.value = True
    waiting_for_button(5)
    amber_led.value = True
    waiting_for_button(2)
    red_led.value = False
    amber_led.value = False
    green_led.value = True
    waiting_for_button(5)
    green_led.value = False
    amber_led.value = True
    waiting_for_button(3)
    amber_led.value = False
