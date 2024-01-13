# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This example acts as a BLE HID keyboard to peer devices.
Attach five buttons with pullup resistors to Feather nRF52840
  each button will send a configurable keycode to mobile device or computer
"""
import time
import board
from digitalio import DigitalInOut, Direction, Pull

import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

button_1 = DigitalInOut(board.D11)
button_2 = DigitalInOut(board.D10)
button_3 = DigitalInOut(board.D9)
button_4 = DigitalInOut(board.D6)
button_5 = DigitalInOut(board.D5)

button_1.direction = Direction.INPUT
button_2.direction = Direction.INPUT
button_3.direction = Direction.INPUT
button_4.direction = Direction.INPUT
button_5.direction = Direction.INPUT

# NOTE: If you are not using buttons with built-in pullups, uncomment the five lines below.
# button_1.pull = Pull.UP
# button_2.pull = Pull.UP
# button_3.pull = Pull.UP
# button_4.pull = Pull.UP
# button_5.pull = Pull.UP

hid = HIDService()

device_info = DeviceInfoService(software_revision=adafruit_ble.__version__,
                                manufacturer="Adafruit Industries")
advertisement = ProvideServicesAdvertisement(hid)
advertisement.appearance = 961
scan_response = Advertisement()
scan_response.complete_name = "CircuitPython HID"

ble = adafruit_ble.BLERadio()
if not ble.connected:
    print("advertising")
    ble.start_advertising(advertisement, scan_response)
else:
    print("already connected")
    print(ble.connections)

k = Keyboard(hid.devices)
kl = KeyboardLayoutUS(k)
while True:
    while not ble.connected:
        pass
    print("Start typing:")

    while ble.connected:
        if not button_1.value:  # pull up logic means button low when pressed
            #print("back")  # for debug in REPL
            k.send(Keycode.BACKSPACE)
            time.sleep(0.1)

        if not button_2.value:
            kl.write("Bluefruit")  # use keyboard_layout for words
            time.sleep(0.4)

        if not button_3.value:
            k.send(Keycode.SHIFT, Keycode.L)  # add shift modifier
            time.sleep(0.4)

        if not button_4.value:
            kl.write("e")
            time.sleep(0.4)

        if not button_5.value:
            k.send(Keycode.ENTER)
            time.sleep(0.4)

    ble.start_advertising(advertisement)
