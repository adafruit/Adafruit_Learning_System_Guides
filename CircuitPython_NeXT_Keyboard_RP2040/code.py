# SPDX-FileCopyrightText: 2022 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT
import array
import time

import board
import rp2pio
import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.keyboard import Keyboard
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

NEXT_SERIAL_BUS_FREQUENCY = (
    18958  # 455kHz/24 https://journal.spencerwnelson.com/entries/nextkb.html
)

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


QUERY = pack_message_str("000001000", 1)
RESET = pack_message_str("0111101111110000000000")

BIT_BREAK = 1 << 11
BIT_MOD = 1


def is_make(report):
    return not bool(report & BIT_BREAK)


def is_mod_report(report):
    return not bool(report & BIT_MOD)


# keycode bits are backwards compared to other information sources
# (bit 0 is first)
def keycode(report):
    b = f"{report >> 12:07b}"
    b = "".join(reversed(b))
    return int(b, 2)


def modifiers(report):
    return (report >> 1) & 0x7F


sm = rp2pio.StateMachine(
    pio_program.assembled,
    first_sideset_pin=board.D11,
    first_in_pin=board.D12,
    pull_in_pin_up=1,
    first_set_pin=board.D13,
    set_pin_count=1,
    first_out_pin=board.D13,
    out_pin_count=1,
    frequency=16 * NEXT_SERIAL_BUS_FREQUENCY,
    in_shift_right=False,
    wait_for_txstall=False,
    out_shift_right=False,
    **pio_program.pio_kwargs,
)


class KeyboardHandler:
    def __init__(self):
        self.old_modifiers = 0
        self.cc = ConsumerControl(usb_hid.devices)
        self.kbd = Keyboard(usb_hid.devices)

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
finally:  # Release all keys before e.g., code is reloaded
    handler.kbd.release_all()
