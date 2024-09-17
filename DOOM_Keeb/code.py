# SPDX-FileCopyrightText: 2024 John Park & Tyeth Gundry for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
DOOM launch for Windows
'zdoom.exe' for Windows https://zdoom.org/downloads must be in CIRCUITPY/zdoom directory.
extract https://github.com/fragglet/squashware/releases squashware-1.1.zip, rename to 'doom1.wad',
place in same CIRCUITPY/zdoom directory as the .exe.
'''

import time
import board
from digitalio import DigitalInOut, Direction
import keypad
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

keys = keypad.Keys((board.A1,), value_when_pressed=False, pull=True)  # set up NeoKey launch button

kbd = Keyboard(usb_hid.devices)  # create keyboard object
layout = KeyboardLayoutUS(kbd)

led = DigitalInOut(board.D13)  # on-board LED
led.direction = Direction.OUTPUT
led.value = True

pixel = neopixel.NeoPixel(board.A2, 1, auto_write=False, brightness=1.0)  # NeoKey LED
pixel.fill(0x440000)
pixel.show()

def launch_terminal():  # function for launching local DOOM
    kbd.send(Keycode.GUI, Keycode.R) # open run cmd
    time.sleep(0.25)
    # pylint: disable=line-too-long
    layout.write("powershell -c \"& { gwmi win32_logicaldisk -f 'DriveType=2' | % { try { $p = $_.DeviceID + 'zdoom\\zdoom.exe'; if (Test-Path $p) { Start-Process $p; break } } catch {} } }\"")
    time.sleep(0.25)
    kbd.send(Keycode.ENTER)
    time.sleep(2)

while True:
    event = keys.events.get()  # check for keypress
    if event:
        if event.pressed:
            pixel.fill(0xff0000)  # brighten LED
            pixel.show()
            launch_terminal()  # launch DOOM
        if event.released:
            pixel.fill(0x440000)  # dim LED
            pixel.show()
