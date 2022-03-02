# SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os

import board
import keypad
import ulab.numpy as np

from adafruit_ble import BLERadio
from adafruit_ble.advertising import Advertisement

from thermalprinter import CatPrinter
from seekablebitmap import imageopen

ble = BLERadio()  # pylint: disable=no-member

buttons = keypad.Keys([board.BUTTON_A, board.BUTTON_B], value_when_pressed=False)

def wait_for_press(kbd):
    """
    Wait for a keypress and return the event
    """
    while True:
        event = kbd.events.get()
        if event and event.pressed:
            return event


def show(s):
    """
    Display a message on the screen
    """
    board.DISPLAY.auto_refresh = False
    print("\n" * 24)
    print(s)
    board.DISPLAY.auto_refresh = True


def show_error(s):
    """
    Display a message on the screen and wait for a button press
    """
    show(s + "\nPress a button to continue")
    wait_for_press(buttons)


def find_cat_printer(radio):
    """
    Connect to the cat printer device using BLE
    """
    while True:
        show("Scanning for GB02 device...")
        for adv in radio.start_scan(Advertisement):
            complete_name = getattr(adv, "complete_name")
            if complete_name is not None:
                print(f"Saw {complete_name}")
            if complete_name == "GB02":
                radio.stop_scan()
                return radio.connect(adv, timeout=10)[CatPrinter]


image_files = [
    i
    for i in os.listdir("/")
    if i.lower().endswith(".pbm") or i.lower().endswith(".bmp")
]
image_files.sort(key=lambda filename: filename.lower())


def select_image():
    i = 0
    while True:
        show(
            f"Select image file\nA: next image\nB: print this image\n\n{image_files[i]}"
        )
        event = wait_for_press(buttons)
        if event.key_number == 0:  # button "A"
            i = (i + 1) % len(image_files)
        if event.key_number == 1:  # button "B"
            return image_files[i]


printer = find_cat_printer(ble)

def main():
    try:
        filename = select_image()

        show(f"Loading {filename}")

        image = imageopen(filename)
        if image.width != 384:
            raise ValueError("Invalid image.  Must be 384 pixels wide")
        if image.bits_per_pixel != 1:
            raise ValueError("Invalid image.  Must be 1 bit per pixel (black & white)")

        invert_image = image.palette and image.palette[0] == 0

        show(f"Printing {filename}")

        for i in range(image.height):
            row_data = image.get_row(i)
            if invert_image:
                row_data = ~np.frombuffer(row_data, dtype=np.uint8)
            printer.print_bitmap_row(row_data)

        # Print blank lines until the paper can be torn off
        for i in range(80):
            printer.print_bitmap_row(b"\0" * 48)

    except Exception as e: # pylint: disable=broad-except
        show_error(str(e))
        image_files.remove(filename)

while True:
    main()
