# SPDX-FileCopyrightText: 2022 Tod Kurt & John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Rotary phone USB keypad

import time
import board
import digitalio
import microcontroller
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_debouncer import Debouncer
import neopixel


dial_in = digitalio.DigitalInOut(board.RX)  # normally closed pulse dial switch
dial_in.pull = digitalio.Pull.UP
dial = Debouncer(dial_in)

receiver_in = digitalio.DigitalInOut(board.D2)  # normally open receiver switch
receiver_in.pull = digitalio.Pull.UP
receiver = Debouncer(receiver_in)


# check if usb_hid has been enabled in boot.py
if len(usb_hid.devices) == 0:
    on_hook = True
    print("on hook")
else:
    kbd = Keyboard(usb_hid.devices)
    on_hook = False
    print("off hook")

keymap = [
          Keycode.ONE,
          Keycode.TWO,
          Keycode.THREE,
          Keycode.FOUR,
          Keycode.FIVE,
          Keycode.SIX,
          Keycode.SEVEN,
          Keycode.EIGHT,
          Keycode.NINE,
          Keycode.ZERO
]

def read_rotary_dial_pulses(timeout=0.2):  # 0.2 is proper timing for pulses
    dial.update()
    if not dial.rose:  # NC dial pin is pulled low normally, high when open
        return 0
    pulse_count = 1
    last_pulse_time = time.monotonic()

    while time.monotonic() - last_pulse_time < timeout:  # count pulses that are within 0.2sec
        dial.update()
        if dial.rose:
            pulse_count = pulse_count+1
            last_pulse_time = time.monotonic()

    return pulse_count

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)


print("Rotary phone USB keypad")


while True:
    receiver.update()
    if receiver.fell:  # only dial when receiver is off hook
        print("Off hook")
        pixel[0] = 0x00ff00
        microcontroller.reset()  # the boot.py enables usb_hid if off hook

    if receiver.rose:
        print("On hook")
        pixel[0] = 0xff0000
        microcontroller.reset()  # the boot.py disables usb_hid if on hook

    # if not on_hook:
    num_pulses = read_rotary_dial_pulses()
    if num_pulses:
        print("pulse count:", num_pulses)
        if not on_hook:
            kbd.send(keymap[num_pulses-1])
