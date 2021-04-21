# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams & John Park for Adafruit
#
# SPDX-License-Identifier: MIT

import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_funhouse import FunHouse
from adafruit_debouncer import Debouncer


RED = 0x200000
GREEN = 0x002000

funhouse = FunHouse(default_bg=None)
funhouse.peripherals.dotstars.fill(RED)

switch_pin = DigitalInOut(board.A1)
switch_pin.direction = Direction.INPUT
switch_pin.pull = Pull.UP
switch = Debouncer(switch_pin)


def send_io_data(door_value):
    funhouse.peripherals.led = True
    print("Sending data to adafruit IO!")
    funhouse.network.push_to_io("door", door_value)
    funhouse.peripherals.led = False


send_io_data(0)

while True:

    switch.update()
    if switch.rose:
        print("Door is open")
        funhouse.peripherals.play_tone(2000, 0.25)
        funhouse.peripherals.dotstars.fill(RED)
        send_io_data(0)

    if switch.fell:
        print("Door is closed")
        funhouse.peripherals.play_tone(800, 0.25)
        funhouse.peripherals.dotstars.fill(GREEN)
        send_io_data(1)
