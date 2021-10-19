# SPDX-FileCopyrightText: 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import subprocess
import random
import json
import re
from datetime import datetime
import board
import displayio
import adafruit_dotstar
from adafruit_st7789 import ST7789

IMAGE_FOLDER = "images"

listen_command = "/usr/bin/voice2json transcribe-stream | /usr/bin/voice2json recognize-intent"
speak_command = "/usr/bin/voice2json speak-sentence '{}'"
pattern = re.compile(r'(?<!^)(?=[A-Z])')

dots = adafruit_dotstar.DotStar(board.D6, board.D5, 3, brightness=0.2, pixel_order=adafruit_dotstar.RBG)
dots.fill(0)

colors = {
    'red': 0xff0000,
    'green': 0x00ff00,
    'blue': 0x0000ff,
    'yellow': 0xffff00,
    'orange': 0xff8800,
    'purple': 0x8800ff,
    'white': 0xffffff,
    'off': 0
}

lights = ['left', 'middle', 'right']

def get_time():
    now = datetime.now()
    speak("The time is {}".format(now.strftime("%-I:%M %p")))

def display_picture(category):
    path = os.getcwd() + "/" + IMAGE_FOLDER + "/" + category
    print("Showing a random image from {}".format(category))
    load_image(path + "/" + get_random_file(path))

def get_random_file(folder):
    filenames = []
    for item in os.listdir(folder):
        if os.path.isfile(os.path.join(folder, item)) and item.endswith((".jpg", ".bmp", ".gif")):
            filenames.append(item)
    if len(filenames):
        return filenames[random.randrange(len(filenames))]
    return None

def load_image(path):
    "Load an image from the path"
    if len(splash):
        splash.pop()
    # CircuitPython 6 & 7 compatible
    bitmap = displayio.OnDiskBitmap(open(path, "rb"))
    sprite = displayio.TileGrid(bitmap, pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter()))

    # # CircuitPython 7+ compatible
    # bitmap = displayio.OnDiskBitmap(path)
    # sprite = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)

    splash.append(sprite)

def change_light_color(lightname, color):
    dotstar_number = lights.index(lightname)
    dots[dotstar_number] = colors[color]
    print("Setting Dotstar {} to 0x{:06X}".format(dotstar_number, colors[color]))

def speak(sentence):
    for output_line in shell_command(speak_command.format(sentence)):
        print(output_line, end='')

def shell_command(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def process_output(line):
    data = json.loads(line)
    if not data['timeout'] and data['intent']['name']:
        func_name = pattern.sub('_', data['intent']['name']).lower()
        if func_name in globals():
            globals()[func_name](**data['slots'])

displayio.release_displays()
spi = board.SPI()
tft_cs = board.CE0
tft_dc = board.D25
tft_lite = board.D26

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)

display = ST7789(
    display_bus,
    width=240,
    height=240,
    rowstart=80,
    rotation=180,
    backlight_pin=tft_lite,
)

splash = displayio.Group()
display.show(splash)

for output_line in shell_command(listen_command):
    process_output(output_line)
