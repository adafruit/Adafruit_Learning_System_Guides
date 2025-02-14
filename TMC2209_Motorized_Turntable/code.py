# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import asyncio
import board
import displayio
import adafruit_imageload
from digitalio import DigitalInOut, Direction
from adafruit_seesaw import seesaw, rotaryio, digitalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_displayio_ssd1306

# rotary encoder
i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, addr=0x36)
encoder = rotaryio.IncrementalEncoder(seesaw)
pos = -encoder.position
last_pos = pos
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button = digitalio.DigitalIO(seesaw, 24)
button_state = False

#display setup
displayio.release_displays()

# oled
oled_reset = board.D9
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)
WIDTH = 128
HEIGHT = 64
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)
# icon sprite sheet
bitmap, palette = adafruit_imageload.load("/icons.bmp",
                                          bitmap=displayio.Bitmap,
                                          palette=displayio.Palette)

icons_grid = displayio.TileGrid(bitmap, pixel_shader=palette,
                                 tile_height=38, tile_width=38,
                                 x=int((display.width / 2)-(38/2)), y=display.height-38)
# text at top of screen
font = bitmap_font.load_font('/Arial-14.bdf')
main_area = label.Label(
    font, text=" ", color=0xFFFFFF)
main_area.anchor_point = (0.5, 0.0)
main_area.anchored_position = (display.width / 2, 0)

splash = displayio.Group()
splash.append(icons_grid)
splash.append(main_area)
display.root_group = splash

# direction and step pins
DIR = DigitalInOut(board.D5)
DIR.direction = Direction.OUTPUT
STEP = DigitalInOut(board.D6)
STEP.direction = Direction.OUTPUT

# enable pin, default off
EN = DigitalInOut(board.D4)
EN.direction = Direction.OUTPUT
EN.value = True

# stepper pins, default 32
MS2 = DigitalInOut(board.D3)
MS2.direction = Direction.OUTPUT
MS2.value = True
MS1 = DigitalInOut(board.D2)
MS1.direction = Direction.OUTPUT
MS1.value = False

# speed dictionaries
speed1 = {
    "micro" : 16,
    "ms1" : True,
    "ms2" : True,
    "icon" : 2,
    "label" : "FAST"
  }
speed2 = {
    "micro" : 32,
    "ms1" : True,
    "ms2" : False,
    "icon" : 1,
    "label" : "MEDIUM"
  }
speed3 = {
    "micro" : 64,
    "ms1" : False,
    "ms2" : True,
    "icon" : 0,
    "label" : "SLOW"
  }
speeds = [speed3, speed2, speed1]

def change_speed(speed):
    MS1.value = speeds[speed]["ms1"]
    MS2.value = speeds[speed]["ms2"]
    icons_grid[0] = speeds[speed]["icon"]
    main_area.text = speeds[speed]["label"]

# enable dictionaries
on = {
    "en" : False,
    "icon" : 6,
    "label" : "ON"
  }

off = {
    "en" : True,
    "icon" : 5,
    "label" : "OFF"
  }

onDict = [on, off]

def onOff(go):
    EN.value = onDict[go]["en"]
    icons_grid[0] = onDict[go]["icon"]
    main_area.text = onDict[go]["label"]

# direction dictionaries
clock = {
    "dir" : True,
    "icon" : 3,
    "label" : "CLOCK"
  }
counter = {
    "dir" : False,
    "icon" : 4,
    "label" : "COUNTER"
  }

directions = [clock, counter]

def changeDirection(direct):
    DIR.value = directions[direct]["dir"]
    icons_grid[0] = directions[direct]["icon"]
    main_area.text = directions[direct]["label"]

# menu states
states = ["SPEED", "ON/OFF", "DIRECTION", "scroll"]
state_icons = [2, 6, 3]

class GUI_Attributes:
    def __init__(self):
        self.menu = 0
        self.index = 0
        self.state = states[3]
        self.current_speed = 1

async def step():
    while True:
        if EN.value is False:
            STEP.value = not STEP.value
        await asyncio.sleep(0)

async def read_encoder(p, last_p, choice):
    while True:
        p = encoder.position
        if p != last_p:
            if p > last_p:
                if choice.state is states[0]:
                    choice.index = (choice.index + 1) % 3
                    change_speed(choice.index)
                    choice.current_speed = choice.index
                if choice.state is states[1]:
                    choice.index = (choice.index + 1) % 2
                    onOff(choice.index)
                if choice.state is states[2]:
                    choice.index = (choice.index + 1) % 2
                    changeDirection(choice.index)
                if choice.state is states[3]:
                    choice.menu = (choice.menu + 1) % 3
                    main_area.text = states[choice.menu]
                    icons_grid[0] = state_icons[choice.menu]
            else:
                if choice.state is states[0]:
                    choice.index = (choice.index - 1) % 3
                    change_speed(choice.index)
                    choice.current_speed = choice.index
                if choice.state is states[1]:
                    choice.index = (choice.index - 1) % 2
                    onOff(choice.index)
                if choice.state is states[2]:
                    choice.index = (choice.index - 1) % 2
                    changeDirection(choice.index)
                if choice.state is states[3]:
                    choice.menu = (choice.menu - 1) % 3
                    main_area.text = states[choice.menu]
                    icons_grid[0] = state_icons[choice.menu]
            print(choice.menu)
            last_p = p
        await asyncio.sleep(0.1)

async def read_button(choice, b_state):
    while True:
        if not button.value and not b_state:
            if choice.state == states[3]:
                choice.state = states[choice.menu]
                if choice.state == states[0]:
                    choice.index = choice.current_speed
                    change_speed(choice.index)
                if choice.state == states[1]:
                    choice.index = EN.value
                    onOff(choice.index)
                if choice.state == states[2]:
                    choice.index = DIR.value
                    changeDirection(choice.index)
            else:
                choice.state = states[3]
                main_area.text = states[choice.menu]
            b_state = True
        if button.value and b_state:
            b_state = False
        await asyncio.sleep(0.1)

async def main():
    choice = GUI_Attributes()
    step_task = asyncio.create_task(step())
    enc_task = asyncio.create_task(read_encoder(pos, last_pos, choice))
    button_task = asyncio.create_task(read_button(choice, button_state))
    main_area.text = states[choice.menu]
    icons_grid[0] = state_icons[choice.menu]
    await asyncio.gather(step_task, enc_task, button_task)

asyncio.run(main())
