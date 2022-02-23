# SPDX-FileCopyrightText: 2019 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio

# set up motion sensor
pir_sensor = digitalio.DigitalInOut(board.D18)
pir_sensor.direction = digitalio.Direction.INPUT

# set up door sensor
door_sensor = digitalio.DigitalInOut(board.D23)
door_sensor.direction = digitalio.Direction.INPUT
door_sensor.pull = digitalio.Pull.UP

while True:

    if pir_sensor.value:
        print("PIR ALARM!")

    if door_sensor.value:
        print("DOOR ALARM!")

    time.sleep(0.5)
