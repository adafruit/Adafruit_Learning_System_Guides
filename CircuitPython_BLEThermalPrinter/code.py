import seekablebitmap

import gc
import os
import struct
import time

import board
import digitalio
import keypad
import ulab.numpy as np

import adafruit_ble
from adafruit_ble import BLERadio
from adafruit_ble.advertising import Advertisement

from thermalprinter import CatPrinter
from seekablebitmap import imageopen

ble = BLERadio()  # pylint: disable=no-member

buttons = keypad.Keys([board.BUTTON_A, board.BUTTON_B], value_when_pressed=False)

def pnmopen(filename):
    """
    Scan for netpbm format info, skip over comments, and read header data.

    Return the format, header, and the opened file positioned at the start of
    the bitmap data.
    """
    # pylint: disable=too-many-branches
    image_file = open(filename, "rb")
    magic_number = image_file.read(2)
    image_file.seek(2)
    pnm_header = []
    next_value = bytearray()
    while True:
        # We have all we need at length 3 for formats P2, P3, P5, P6
        if len(pnm_header) == 3:
            return image_file, magic_number, pnm_header

        if len(pnm_header) == 2 and magic_number in [b"P1", b"P4"]:
            return image_file, magic_number, pnm_header

        next_byte = image_file.read(1)
        if next_byte == b"":
            raise RuntimeError("Unsupported image format {}".format(magic_number))
        if next_byte == b"#":  # comment found, seek until a newline or EOF is found
            while image_file.read(1) not in [b"", b"\n"]:  # EOF or NL
                pass
        elif not next_byte.isdigit():  # boundary found in header data
            if next_value:
                # pull values until space is found
                pnm_header.append(int("".join(["%c" % char for char in next_value])))
                next_value = bytearray()  # reset the byte array
        else:
            next_value += next_byte  # push the digit into the byte array

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
            complete_name = getattr(adv, 'complete_name')
            if complete_name is not None:
                print(f"Saw {complete_name}")
            if complete_name == 'GB02':
                radio.stop_scan()
                return radio.connect(adv, timeout=10)[CatPrinter]

image_files = [i for i in os.listdir('/') if i.lower().endswith(".pbm") or i.lower().endswith(".bmp")]
image_files.sort(key=lambda filename: filename.lower())

def select_image():
    i = 0
    while True:
        show(f"Select image file\nA: next image\nB: print this image\n\n{image_files[i]}")
        event = wait_for_press(buttons)
        if event.key_number == 0: # button "A"
            i = (i + 1) % len(image_files)
        if event.key_number == 1: # button "B"
            return image_files[i]
    
printer = find_cat_printer(ble)

while True:
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
            printer.print_bitmap_row(b'\0' * 48)

    except Exception as e:
        show_error(str(e))
        image_files.remove(filename)
        continue
