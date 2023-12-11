# SPDX-FileCopyrightText: 2022 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT
import array
import time

import board
import rp2pio
import usb_hid
from keypad import Keys
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard import Keycode
from adafruit_hid.mouse import Mouse
from adafruit_pioasm import Program
from adafruit_ticks import ticks_add, ticks_less, ticks_ms
from next_keycode import (
    cc_value,
    is_cc,
    next_modifiers,
    next_scancodes,
    shifted_codes,
    shift_modifiers,
)


# Compared to a modern mouse, the DPI of the NeXT mouse is low. Increasing this
# number makes the pointer move further faster, but it also makes moves chunky.
# Customize this number according to the trade-off you want, but also check
# whether your operating system can assign a higher "sensitivity" or
# "acceleration" for the mouse.
MOUSE_SCALE = 8

# Customize the power key's keycode. You can change it to `Keycode.POWER` if
# you really want to accidentally power off your computer!
POWER_KEY_SENDS = Keycode.F1

# according to https://journal.spencerwnelson.com/entries/nextkb.html the
# keyboard's timing source is a 455MHz crystal, and the serial data rate is
# 1/24 the crystal frequency. This differs by a few percent from the "50us" bit
# time reported in other sources.
NEXT_SERIAL_BUS_FREQUENCY = round(455_000 / 24)

pio_program = Program(
    """
top:
    set pins, 1
    pull block             ; wait for send request
    out x, 1               ; trigger receive?
    out y, 7               ; get count of bits to transmit (minus 1)

bitloop:
    out pins, 1        [7] ; send next bit
    jmp y--, bitloop   [7] ; loop if bits left to send

    set pins, 1            ; idle the bus after last bit
    jmp !x, top            ; to top if no scancode expected

    set pins, 1            ; mark bus as idle so keyboard will send
    set y, 19              ; 20 bits to receive

    wait 0, pin 0 [7]      ; wait for falling edge plus half bit time
recvloop:
    in pins, 1 [7]         ; sample in the middle of the bit
    jmp y--, recvloop [7]  ; loop until all bits read

    push                   ; send report to CircuitPython
"""
)


def pack_message(bitcount, data, trigger_receive=False):
    if bitcount > 24:
        raise ValueError("too many bits in message")
    trigger_receive = bool(trigger_receive)
    message = (
        (trigger_receive << 31) | ((bitcount - 1) << 24) | (data << (24 - bitcount))
    )
    return array.array("I", [message])


def pack_message_str(bitstring, trigger_receive=False):
    bitcount = len(bitstring)
    data = int(bitstring, 2)
    return pack_message(bitcount, data, trigger_receive=trigger_receive)


def set_leds(i):
    return pack_message_str(f"0000000001110{i:02b}0000000")


QUERY = pack_message_str("000001000", True)
MOUSEQUERY = pack_message_str("010001000", True)
RESET = pack_message_str("0111101111110000000000")

BIT_BREAK = 1 << 11
BIT_MOD = 1


def is_make(report):
    return not bool(report & BIT_BREAK)


def is_mod_report(report):
    return not bool(report & BIT_MOD)


def extract_bits(report, *positions):
    result = 0
    for p in positions:
        result = (result << 1)
        if report & (1 << p):
            result |= 1
        #result = (result << 1) | bool(report & (1<<p))
    return result

# keycode bits are backwards compared to other information sources
# (bit 0 is first)
def keycode(report):
    return extract_bits(report, 12, 13, 14, 15, 16, 17, 18)


def modifiers(report):
    return (report >> 1) & 0x7F


sm = rp2pio.StateMachine(
    pio_program.assembled,
    first_in_pin=board.MISO,
    pull_in_pin_up=1,
    first_set_pin=board.MOSI,
    set_pin_count=1,
    first_out_pin=board.MOSI,
    out_pin_count=1,
    frequency=16 * NEXT_SERIAL_BUS_FREQUENCY,
    in_shift_right=False,
    wait_for_txstall=False,
    out_shift_right=False,
    **pio_program.pio_kwargs,
)


def signfix(num, sign_pos):
    """Fix a signed number if the bit with weight `sign_pos` is actually the sign bit"""
    if num & sign_pos:
        return num - 2*sign_pos
    return num

class KeyboardHandler:
    def __init__(self):
        self.old_modifiers = 0
        self.cc = ConsumerControl(usb_hid.devices)
        self.kbd = Keyboard(usb_hid.devices)
        self.mouse = Mouse(usb_hid.devices)

    def set_key_state(self, key, state):
        if state:
            if isinstance(key, tuple):
                old_report_modifier = self.kbd.report_modifier[0]
                self.kbd.report_modifier[0] = 0
                self.kbd.press(*key)
                self.kbd.release_all()
                self.kbd.report_modifier[0] = old_report_modifier
            else:
                self.kbd.press(key)
        else:
            if isinstance(key, tuple):
                pass
            else:
                self.kbd.release(key)

    def handle_mouse_report(self, report):
        if report == 1536: # the "nothing happened" report
            return

        dx = extract_bits(report, 11,12,13,14,15,16,17)
        dx = -signfix(dx, 64)
        dy = extract_bits(report, 0,1,2,3,4,5,6)
        dy = -signfix(dy, 64)
        b1 = not extract_bits(report, 18)
        b2 = not extract_bits(report, 7)

        self.mouse.report[0] = (
            Mouse.MIDDLE_BUTTON if (b1 and b2) else
            Mouse.LEFT_BUTTON if b1 else
            Mouse.RIGHT_BUTTON if b2
            else 0)
        if dx or dy:
            self.mouse.move(dx * MOUSE_SCALE, dy * MOUSE_SCALE)
        else:
            self.mouse._send_no_move() # pylint: disable=protected-access

    def handle_report(self, report_value):
        if report_value == 1536: # the "nothing happened" report
            return

        # Handle modifier changes
        mods = modifiers(report_value)
        changes = self.old_modifiers ^ mods
        self.old_modifiers = mods
        for i in range(7):
            bit = 1 << i
            if changes & bit:  # Modifier key pressed or released
                self.set_key_state(next_modifiers[i], mods & bit)

        # Handle key press/release
        code = next_scancodes.get(keycode(report_value))
        if mods & shift_modifiers:
            code = shifted_codes.get(keycode(report_value), code)
        make = is_make(report_value)
        if code:
            if is_cc(code):
                if make:
                    self.cc.send(cc_value(code))
            else:
                self.set_key_state(code, make)

keys = Keys([board.SCK], value_when_pressed=False)

handler = KeyboardHandler()

recv_buf = array.array("I", [0])

time.sleep(0.1)
sm.write(RESET)
time.sleep(0.1)

for _ in range(4):
    sm.write(set_leds(3))
    time.sleep(0.1)
    sm.write(set_leds(0))
    time.sleep(0.1)

print("Keyboard ready!")

try:
    while True:
        if (event := keys.events.get()):
            handler.set_key_state(POWER_KEY_SENDS, event.pressed)

        sm.write(QUERY)
        deadline = ticks_add(ticks_ms(), 100)
        while ticks_less(ticks_ms(), deadline):
            if sm.in_waiting:
                sm.readinto(recv_buf)
                value = recv_buf[0]
                handler.handle_report(value)
                break
        else:
            print("keyboard did not respond - resetting")
            sm.restart()
            sm.write(RESET)
            time.sleep(0.1)

        sm.write(MOUSEQUERY)
        deadline = ticks_add(ticks_ms(), 100)
        while ticks_less(ticks_ms(), deadline):
            if sm.in_waiting:
                sm.readinto(recv_buf)
                value = recv_buf[0]
                handler.handle_mouse_report(value)
                break
        else:
            print("keyboard did not respond - resetting")
            sm.restart()
            sm.write(RESET)
            time.sleep(0.1)
finally:  # Release all keys before e.g., code is reloaded
    handler.kbd.release_all()
