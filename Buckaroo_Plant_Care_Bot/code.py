# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Bonsai Buckaroo + CLUE Plant Care Bot

import time
import board
from digitalio import DigitalInOut, Direction
from analogio import AnalogIn
from adafruit_clue import clue
from adafruit_display_text import label
import displayio
import terminalio
import pwmio

moist_level = 50  # adjust this value as needed for your plant

board.DISPLAY.brightness = 0.8
clue.pixel.fill(0)  # turn off NeoPixel

clue_display = displayio.Group()

# draw the dry plant
dry_plant_file = open("dry.bmp", "rb")
dry_plant_bmp = displayio.OnDiskBitmap(dry_plant_file)
# CircuitPython 6 & 7 compatible
dry_plant_sprite = displayio.TileGrid(
    dry_plant_bmp,
    pixel_shader=getattr(dry_plant_bmp, "pixel_shader", displayio.ColorConverter()),
)
# CircuitPython 7 compatible
# dry_plant_sprite = displayio.TileGrid(
#     dry_plant_bmp, pixel_shader=dry_plant_bmp.pixel_shader
# )
clue_display.append(dry_plant_sprite)

# draw the happy plant on top (so it can be moved out of the way when needed)
happy_plant_file = open("happy.bmp", "rb")
happy_plant_bmp = displayio.OnDiskBitmap(happy_plant_file)
# CircuitPython 6 & 7 compatible
happy_plant_sprite = displayio.TileGrid(
    happy_plant_bmp,
    pixel_shader=getattr(happy_plant_bmp, "pixel_shader", displayio.ColorConverter()),
)
# CircuitPython 7 compatible
# happy_plant_sprite = displayio.TileGrid(
#     happy_plant_bmp, pixel_shader=happy_plant_bmp.pixel_shader
# )
clue_display.append(happy_plant_sprite)

# Create text
# first create the group
text_group = displayio.Group(scale=3)
# Make a label
title_label = label.Label(terminalio.FONT, text="CLUE Plant", color=0x00FF22)
# Position the label
title_label.x = 10
title_label.y = 4
# Append label to group
text_group.append(title_label)

soil_label = label.Label(terminalio.FONT, text="Soil: ", color=0xFFAA88)
soil_label.x = 4
soil_label.y = 64
text_group.append(soil_label)

motor_label = label.Label(terminalio.FONT, text="Motor off", color=0xFF0000)
motor_label.x = 4
motor_label.y = 74
text_group.append(motor_label)

clue_display.append(text_group)
board.DISPLAY.root_group = clue_display

motor = DigitalInOut(board.P2)
motor.direction = Direction.OUTPUT

buzzer = pwmio.PWMOut(board.SPEAKER, variable_frequency=True)
buzzer.frequency = 1000

sense_pin = board.P1
analog = AnalogIn(board.P1)


def read_and_average(ain, times, wait):
    asum = 0
    for _ in range(times):
        asum += ain.value
        time.sleep(wait)
    return asum / times


time.sleep(5)

while True:
    # take 100 readings and average them
    aval = read_and_average(analog, 100, 0.01)
    # calculate a percentage (aval ranges from 0 to 65535)
    aperc = aval / 65535 * 100
    # display the percentage
    soil_label.text = "Soil: {} %".format(int(aperc))
    print((aval, aperc))

    if aperc < moist_level:
        happy_plant_sprite.x = 300  # move the happy sprite away
        time.sleep(1)
        motor.value = True
        motor_label.text = "Motor ON"
        motor_label.color = 0x00FF00
        buzzer.duty_cycle = 2 ** 15
        time.sleep(0.5)

    # always turn off quickly
    motor.value = False
    motor_label.text = "Motor off"
    motor_label.color = 0xFF0000
    buzzer.duty_cycle = 0

    if aperc >= moist_level:
        happy_plant_sprite.x = 0  # bring back the happy sprite
