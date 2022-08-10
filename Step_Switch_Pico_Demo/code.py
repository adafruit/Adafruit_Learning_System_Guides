# SPDX-FileCopyrightText: 2022 john park for Adafruit Industries
# SPDX-License-Identifier: MIT
# Pico Four Step Switch Keypad Demo
import time
import board
from digitalio import Direction, DigitalInOut, Pull
from adafruit_debouncer import Debouncer

board_led = DigitalInOut(board.LED)
board_led.direction = Direction.OUTPUT
board_led.value = True

switch_pins = (board.GP6, board.GP7, board.GP8, board.GP9)
step_switches = []
for switch_pin in switch_pins:
    tmp_switch_pin = DigitalInOut(switch_pin)
    tmp_switch_pin.pull = Pull.UP
    step_switches.append(Debouncer(tmp_switch_pin))

led_pins = (board.GP2, board.GP3, board.GP4, board.GP5)
leds = []
for led_pin in led_pins:
    tmp_led_pin = DigitalInOut(led_pin)
    tmp_led_pin.direction = Direction.OUTPUT
    tmp_led_pin.value = False
    leds.append(tmp_led_pin)

def blink_led(led_num, pause, repeat):
    for __ in range(repeat * 2):
        leds[led_num].value = not leds[led_num].value
        time.sleep(pause)

def blink_all_leds(pause, repeat):
    for __ in range(repeat * 2):
        for led in leds:
            led.value = not led.value
        time.sleep(pause)

blink_all_leds(0.1, 4)


mode_picked = False  # state of mode selection
mode_choice = 0  # MIDI mode, desk switcher mode, etc.
modes = (0, 1, 2, 3)
mode_names = ("MIDI", "DESK", "SELECTOR", "COPY-PASTE")

print("Select the mode by pressing a button...")
while not mode_picked:  # program waits for a mode to be picked
    for i in range(len(step_switches)):
        step_switches[i].update()
        if step_switches[i].fell:
            mode_choice = i
            print(mode_names[mode_choice], "mode")
            mode_picked = True

if mode_choice == 0:  # MIDI mode
    import usb_midi
    import adafruit_midi
    from adafruit_midi.control_change import ControlChange
    midi = adafruit_midi.MIDI(
                            midi_in=usb_midi.ports[0],
                            in_channel=0,
                            midi_out=usb_midi.ports[1],
                            out_channel=0
    )
    cc_num = [16, 17, 18, 19]
    cc_state = [False, False, False, False]

else:  # HID modes
    import usb_hid
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode

if mode_choice == 1:  # Mac Desktop switcher mode
    kpd = Keyboard(usb_hid.devices)
    MODIFIER = Keycode.CONTROL
    KEYMAP = (
        ("Desktop 1", [MODIFIER, Keycode.ONE]),
        ("Desktop 2", [MODIFIER, Keycode.TWO]),
        ("Desktop 3", [MODIFIER, Keycode.THREE]),
        ("Desktop 4", [MODIFIER, Keycode.FOUR]),
    )

if mode_choice == 2:  # SELECTOR mode for game weapon slot, Wirecast, etc.
    kpd = Keyboard(usb_hid.devices)
    MODIFIER = Keycode.SHIFT
    KEYMAP = (
        ("Selector 1", [MODIFIER, Keycode.ONE]),
        ("Selector 2", [MODIFIER, Keycode.TWO]),
        ("Selector 3", [MODIFIER, Keycode.THREE]),
        ("Selector 4", [MODIFIER, Keycode.FOUR]),
    )

if mode_choice == 3:  # Copy/Paste mode
    kpd = Keyboard(usb_hid.devices)
    # Choose the correct modifier key for Windows or Mac.
    # MODIFIER = Keycode.CONTROL  # For Windows
    MODIFIER = Keycode.COMMAND
    KEYMAP = (
        ("wire 1", [MODIFIER, Keycode.A]),  # select all
        ("wire 2", [MODIFIER, Keycode.X]),  # cut
        ("wire 3", [MODIFIER, Keycode.C]),  # copy
        ("wire 4", [MODIFIER, Keycode.V]),  # paste
    )

blink_led(mode_choice, 0.1, 3)


while True:
    for i in range(len(step_switches)):
        step_switches[i].update()
        if step_switches[i].fell:
            print(i, "pressed")
            if mode_choice == 0:
                leds[i].value = not leds[i].value
                if cc_state[i] is False:
                    midi.send(ControlChange(cc_num[i], 127))
                    cc_state[i] = True
                else:
                    midi.send(ControlChange(cc_num[i], 0))
                    cc_state[i] = False
            else:
                print(KEYMAP[i][0])
                kpd.send(*KEYMAP[i][1])
                for switch_led in leds:  # blank the LEDs first
                    switch_led.value = False
                leds[i].value = True  # light selected switch LED
