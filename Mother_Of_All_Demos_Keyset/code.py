# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import keypad
import supervisor
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

# Dictionary of macros for single keys and combinations
macros = {
    # Single key macros
    (0,): "good",
    (1,): "great",
    (2,): "nice",
    (3,): "awesome",
    (4,): "cool",

    # Combination macros
    (0, 2, 4): "looks good to me",
    (0, 2): "be right back",
    (2, 4): "see you soon",
    (1, 3): "sounds good",
}

KEY_PINS = (
    board.A1,
    board.A2,
    board.A3,
    board.MISO,
    board.MOSI,
)

keys = keypad.Keys(
    KEY_PINS,
    value_when_pressed=False,
    pull=True,
    interval=0.01,
    max_events=64,
    debounce_threshold=3
)

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)

# need to wait longer for 3 key combos
LARGER_COMBOS = {
    (0, 2): (0, 2, 4),
    (2, 4): (0, 2, 4),
}

# How long to wait for possible additional keys in a combo (ms)
COMBO_WAIT_TIME = 150  # Wait 150ms to see if more keys are coming

# How long to wait for a single key before executing (ms)
SINGLE_KEY_TIMEOUT_MS = 80

# Minimum time between macro executions (ms)
MACRO_COOLDOWN_MS = 300

# Store the current state of all keys
key_states = {i: False for i in range(len(KEY_PINS))}

# Create a reusable Event object to avoid memory allocations
reusable_event = keypad.Event()

# Track timing and state
last_macro_time = 0
key_combo_start_time = 0
waiting_for_combo = False
last_executed_combo = None

while True:
    # Process all events in the queue
    keys_changed = False

    while keys.events:
        if keys.events.get_into(reusable_event):
            # Check if key state actually changed
            old_state = key_states[reusable_event.key_number]
            key_states[reusable_event.key_number] = reusable_event.pressed

            if old_state != reusable_event.pressed:
                print(f"Key {reusable_event.key_number} " +
                f"{'pressed' if reusable_event.pressed else 'released'}")
                keys_changed = True

    # Get currently pressed keys as a sorted tuple
    current_pressed_keys = tuple(sorted(k for k, v in key_states.items() if v))
    current_time = supervisor.ticks_ms()

    # When all keys are released, reset tracking
    if not current_pressed_keys:
        waiting_for_combo = False
        last_executed_combo = None
        time.sleep(0.01)
        continue

    # If this is a new key pattern or we just started
    if keys_changed:
        # If we weren't tracking before, start now
        if not waiting_for_combo:
            key_combo_start_time = current_time
            waiting_for_combo = True

        # If the pressed keys have changed, update the timer
        if current_pressed_keys != last_executed_combo:
            key_combo_start_time = current_time

    # Skip if we've already executed this exact combination
    if current_pressed_keys == last_executed_combo:
        time.sleep(0.01)
        continue

    # Determine if we should execute a macro now
    should_execute = False
    wait_more = False

    # If this is a potential part of a larger combo, wait longer
    if current_pressed_keys in LARGER_COMBOS:
        # Only wait if we've been waiting less than the combo wait time
        if (current_time - key_combo_start_time) < COMBO_WAIT_TIME:
            wait_more = True
        else:
            # We've waited long enough, go ahead and execute
            should_execute = True
    # Immediate execution for multi-key combinations that aren't potential parts of larger combos
    elif len(current_pressed_keys) > 1:
        should_execute = True
    # Execute single key after timeout
    elif waiting_for_combo and (current_time - key_combo_start_time) >= SINGLE_KEY_TIMEOUT_MS:
        should_execute = True

    # If we need to wait more, skip to the next iteration
    if wait_more:
        time.sleep(0.01)
        continue

    # Execute the macro if conditions are met
    if should_execute and current_pressed_keys in macros:
        # Only execute if cooldown period has passed
        if current_time - last_macro_time >= MACRO_COOLDOWN_MS:
            print(f"MACRO: {macros[current_pressed_keys]}")
            keyboard_layout.write(macros[current_pressed_keys])
            last_macro_time = current_time
            last_executed_combo = current_pressed_keys

    time.sleep(0.01)
