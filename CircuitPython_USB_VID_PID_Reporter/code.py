# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
CircuitPython USB VID/PID Reporter
Feather RP2040 USB Host with OLED FeatherWing

"""

import usb.core
import keypad
import board
import displayio
import terminalio

from adafruit_display_text import label
from i2cdisplaybus import I2CDisplayBus

import adafruit_displayio_sh1107

displayio.release_displays()

# init display
i2c = board.I2C()
display_bus = I2CDisplayBus(i2c, device_address=0x3C)
display = adafruit_displayio_sh1107.SH1107(display_bus, width=128, height=64)

# text groups
main = displayio.Group()
extra_info = displayio.Group()
groups = [main, extra_info]
display.root_group = main

# text objects for title, VID and PID
title_text = label.Label(terminalio.FONT, text="USB VID/PID Reporter", color=0xFFFFFF, x=5, y=15)
main.append(title_text)
vid_text = label.Label(terminalio.FONT, text="VID:", color=0xFFFFFF, x=5, y=35)
main.append(vid_text)
pid_text = label.Label(terminalio.FONT, text="PID:", color=0xFFFFFF, x=5, y=50)
main.append(pid_text)

# text objects for manufacturer and product info
# added to secondary group
man_header = label.Label(terminalio.FONT, text="Manufacturer:", color=0xFFFFFF, x=5, y=10)
extra_info.append(man_header)
man_text = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF, x=5, y=25)
extra_info.append(man_text)
prod_header = label.Label(terminalio.FONT, text="Product:", color=0xFFFFFF, x=5, y=40)
extra_info.append(prod_header)
prod_text = label.Label(terminalio.FONT, text=" ", color=0xFFFFFF, x=5, y=55)
extra_info.append(prod_text)

# init A, B and C buttons on FeatherWing as keypad keys
keys = keypad.Keys((board.D5,board.D6,board.D9,), value_when_pressed=False, pull=True)

# variables
last_pid = 0x0000 # store last PID
last_vid = 0x0000 # store last VID
usb_dev = False # is there a USB device?
first_run = True # first run through loop
group_index = 0 # display group index
while True:
    event = keys.events.get()
    if event:
        # if any button is pressed, toggle graphics group
        if event.pressed:
            group_index = (group_index + 1) % 2
            display.root_group = groups[group_index]
    # find connected devices
    devices = list(usb.core.find(find_all=True))
    # if no device, reset states and text objects
    if not devices and usb_dev or first_run:
        print("no device")
        pid_text.text = "PID:"
        vid_text.text = "VID:"
        man_text.text = " "
        prod_text.text = " "
        usb_dev = False
        first_run = False
    else:
        if not usb_dev:
            first_run = False
            for device in devices:
                try:
                    # if its the same device, don't scan again
                    if (last_pid == hex(device.idProduct) and
                        last_vid == hex(device.idVendor) and usb_dev):
                        break
                    # new device!
                    usb_dev = True
                    # get PID, VID, manufacturer and product
                    # update text elements
                    print("pid", hex(device.idProduct))
                    last_pid = hex(device.idProduct)
                    pid_text.text = f"PID: {last_pid}"
                    print("vid", hex(device.idVendor))
                    last_vid = hex(device.idVendor)
                    vid_text.text = f"VID: {last_vid}"
                    print("man", device.manufacturer)
                    # only update manufacturer and product if info is known
                    if device.manufacturer is not None:
                        man_text.text = device.manufacturer
                    print("product", device.product)
                    if device.product is not None:
                        prod_text.text = device.product
                    print()
                # if there's any error reading info from a USB device, continue
                except usb.core.USBError:
                    print("got an error, continuing..")
                    continue
