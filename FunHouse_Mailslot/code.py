# SPDX-FileCopyrightText: Copyright (c) 2021 John Park for Adafruit
#
# SPDX-License-Identifier: MIT
# FunHouse Mail Slot Detector

import board
from adafruit_debouncer import Debouncer
from digitalio import DigitalInOut, Pull
from adafruit_funhouse import FunHouse

beam_sense_pin = DigitalInOut(board.A0)  # defaults to input
beam_sense_pin.pull = Pull.UP  # turn on internal pull-up resistor
beam_sensor = Debouncer(beam_sense_pin)

AMBER = 0xF0D000
BLUE = 0x00D0F0
RED = 0xFF0000
WHITE = 0xFFFFFF
GRAY = 0x606060

funhouse = FunHouse(default_bg=None, scale=3)
funhouse.peripherals.dotstars.brightness = 0.05
funhouse.peripherals.dotstars.fill(AMBER)

# Create the labels
funhouse.display.root_group = None
mail_label = funhouse.add_text(
    text="No Mail yet", text_position=(4, 14), text_color=AMBER
)
reset_label = funhouse.add_text(text="reset", text_position=(3, 70), text_color=GRAY)

funhouse.display.root_group = funhouse.splash


def send_io_data(mail_value):
    funhouse.peripherals.led = True
    funhouse.network.push_to_io("mail", mail_value)
    funhouse.peripherals.led = False


send_io_data(1)

while True:
    beam_sensor.update()

    if beam_sensor.fell:
        funhouse.peripherals.set_dotstars(RED, WHITE, BLUE, WHITE, RED)
        funhouse.peripherals.play_tone(2000, 0.25)
        funhouse.set_text("Mail is here!", mail_label)
        funhouse.set_text_color(BLUE, mail_label)
        send_io_data(0)

    if funhouse.peripherals.button_down:
        funhouse.peripherals.dotstars.fill(AMBER)
        funhouse.set_text("No Mail yet", mail_label)
        funhouse.set_text_color(AMBER, mail_label)
        send_io_data(1)
