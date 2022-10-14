# SPDX-FileCopyrightText: Copyright (c) 2022 John Park & Tod Kurt for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Ortho split keyboard
import time
import board
from adafruit_tca8418 import TCA8418
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from keymaps import layer_keymaps # keymaps are saved in keymaps.py file

kbd = Keyboard(usb_hid.devices)
num_layers = len(layer_keymaps)
current_layer = 1

i2c_left = board.STEMMA_I2C()  # uses QT Py RP2040 STEMMA QT port
i2c_right = board.I2C()  # I2C channel on the QT Py RP2040 pads broken out on board
tca_left = TCA8418(i2c_left)
tca_right = TCA8418(i2c_right)

tcas = (tca_left, tca_right)  # put the TCA objects in a list for easy iteration later

# set up a R0-R7 pins and C0-C4 pins as keypads
KEYPADPINS = (
                TCA8418.R0, TCA8418.R1, TCA8418.R2, TCA8418.R3, TCA8418.R4,
                TCA8418.C0, TCA8418.C1, TCA8418.C2, TCA8418.C3, TCA8418.C4, TCA8418.C5
)

for tca in tcas:
    for pin in KEYPADPINS:
        tca.keypad_mode[pin] = True
        tca.enable_int[pin] = True
        tca.event_mode_fifo[pin] = True
    tca.key_intenable = True

print("Ortho Split Keyboard")


while True:
    for i in range(len(tcas)):
        tca = tcas[i]  # get the TCA we're working with
        keymap = layer_keymaps[current_layer][i]  # get the corresponding keymap for it
        if tca.key_int:
            events = tca.events_count
            for _ in range(events):
                keyevent = tca.next_event
                keymap_number = (keyevent & 0x7F)
                (modifier, keycode) = keymap[keymap_number]  # get keycode & modifer from keymap
                #  print("\tKey event: 0x%02X - key #%d " % (keyevent, keyevent & 0x7F))
                if keycode is None:
                    pass

                else:
                    if keyevent & 0x80:  # if key is pressed
                        if modifier == 0:  # normal keypress
                            kbd.press(keycode)
                        elif modifier == 1:  # lower
                            current_layer = min(max((current_layer-1), 0), num_layers-1)
                        elif modifier == 2:  # raise
                            current_layer = min(max((current_layer+1), 0), num_layers-1)
                        elif modifier == 7:  # cap mod
                            kbd.press(Keycode.SHIFT, keycode)

                    else:  # key released
                        if modifier == 7:  # capped shifted key requires special handling
                            kbd.release(Keycode.SHIFT, keycode)
                        else:
                            kbd.release(keycode)

            tca.key_int = True  # clear the IRQ by writing 1 to it
            time.sleep(0.01)
