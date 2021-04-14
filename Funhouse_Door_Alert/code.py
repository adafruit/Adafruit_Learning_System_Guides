# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams & John Park for Adafruit
#
# SPDX-License-Identifier: MIT

import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_funhouse import FunHouse

i2c = board.I2C()

RED = 0x200000
GREEN = 0x002000

funhouse = FunHouse(default_bg=None)
funhouse.peripherals.set_dotstars(RED, RED, RED, RED, RED)

switch = DigitalInOut(board.A1)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# Initialize a new MQTT Client object
funhouse.network.init_io_mqtt()

print("Connecting to Adafruit IO...")
funhouse.network.mqtt_connect()

last_door = 1


def send_io_data(door_value):
    funhouse.peripherals.led = True
    print("Sending data to adafruit IO!")
    funhouse.network.mqtt_publish("door", door_value)
    funhouse.peripherals.led = False


send_io_data(0)

while True:

    if switch.value and last_door is 0:
        print("Door is open")
        funhouse.peripherals.play_tone(2000, 0.25)
        funhouse.peripherals.dotstars.fill(RED)
        last_door = 1
        send_io_data(0)

    elif not switch.value and last_door is 1:
        print("Door is closed")
        funhouse.peripherals.play_tone(800, 0.25)
        funhouse.peripherals.dotstars.fill(GREEN)
        last_door = 0
        send_io_data(1)
