# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''MagicBand+ BLE remote for the Adafruit CLUE (nRF52840).

Broadcasts Disney MagicBand+ BLE commands using the 0x0183 manufacturer
identifier. Grid of category tiles on startup; A/B navigate, double-tap B
opens the selected category. In the list view, A/B scroll, double-tap A
fires the highlighted command, double-tap B returns to grid, and a long
press on B fires the OFF command to cancel a running animation. Shake the
CLUE to pick a random command; confirm with double-tap A or cancel with B.
'''
# Target: Adafruit CLUE (nRF52840) - the BLE remote
import gc
import os
import random
import time

import _bleio
import alarm
import board
import digitalio
import microcontroller
import neopixel
import pwmio
import supervisor
from adafruit_debouncer import Button

import ble_transmitter
import command_library
import ui

_STATE_GRID = 0
_STATE_LIST = 1
_STATE_CONFIRM = 2

_SHAKE_THRESHOLD = 32.0       # m/s^2 magnitude (higher = harder shake needed)
_SHAKE_COOLDOWN = 1.5         # seconds between shake triggers
_PALETTE = command_library.CATEGORIES

# Disney-style ascending chime played on the onboard piezo after each fire.
_CHIME = ((523, 0.08), (659, 0.08), (784, 0.14))

# Direct hardware access - skips loading adafruit_clue's full sensor suite.
i2c = board.I2C()
try:
    from adafruit_lsm6ds.lsm6ds33 import LSM6DS33
    accel = LSM6DS33(i2c)
except (OSError, RuntimeError, ImportError):
    from adafruit_lsm6ds.lsm6ds3trc import LSM6DS3TRC
    accel = LSM6DS3TRC(i2c)

display = board.DISPLAY
DISPLAY_ACTIVE_BRIGHTNESS = 0.8
DISPLAY_SLEEP_TIMEOUT_S = 30.0  # sleep TFT backlight after this many idle seconds
display.brightness = DISPLAY_ACTIVE_BRIGHTNESS

# Battery voltage monitoring intentionally not implemented on the CLUE.
# Unlike the Feather Sense which has a hardwired voltage divider from the
# LIPO rail, the CLUE has no such divider exposed on CircuitPython's board
# module. Pin-probing testing reads unconnected floating values.
#
# For power awareness, rely on the display auto-sleep feature which is the
# larger power saver anyway (~25-35mA savings when backlight is off).

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
pixel.fill((0, 0, 0))

# PWM-driven speaker avoids per-note audio buffer allocations.
speaker = pwmio.PWMOut(board.SPEAKER, variable_frequency=True, duty_cycle=0)

btn_a_io = digitalio.DigitalInOut(board.BUTTON_A)
btn_a_io.switch_to_input(pull=digitalio.Pull.UP)
btn_b_io = digitalio.DigitalInOut(board.BUTTON_B)
btn_b_io.switch_to_input(pull=digitalio.Pull.UP)

gc.collect()

grid_view = ui.GridView(_PALETTE)
list_view = ui.ListView()
confirm_view = ui.ConfirmView()
listen_view = ui.ListenView()

display.root_group = grid_view.group

button_a = Button(btn_a_io, value_when_pressed=False,
                  short_duration_ms=250, long_duration_ms=600)
button_b = Button(btn_b_io, value_when_pressed=False,
                  short_duration_ms=250, long_duration_ms=600)


def play_chime():
    '''Play the Disney-style confirmation chime via hardware PWM.

    Respects silent mode - skip playback when _silent_mode is on.
    '''
    if _silent_mode[0]:
        return
    for freq, dur in _CHIME:
        speaker.frequency = int(freq)
        speaker.duty_cycle = 0x8000
        time.sleep(dur)
        speaker.duty_cycle = 0


def pulse_pixel_and_fire(payload, display_color=(80, 0, 160)):
    '''Light the onboard NeoPixel while broadcasting, then fade.'''
    pixel.fill(display_color)
    ble_transmitter.broadcast(payload)
    pixel.fill((0, 0, 0))


def fire_command(command, status_setter):
    '''Broadcast a single command or play a multi-step sequence.

    command is a (name, payload, needs_ping) tuple. Payload can be a raw
    bytes packet for single commands or a tuple of step-tuples for shows.
    When needs_ping is True, a short CC03 wake ping is broadcast first to
    prime the band's receiver before the actual command.
    '''
    gc.collect()
    name, payload, needs_ping = command[0], command[1], command[2]

    # Intercept the listen-mode sentinel: instead of broadcasting, this
    # transitions to packet capture mode for protocol research.
    if payload == b"LISTEN":
        run_listen_mode()
        return

    if isinstance(payload, bytes):
        status_setter(f"Firing: {name}", 0x00FF00)
        play_chime()
        if needs_ping:
            pixel.fill((30, 30, 30))
            ble_transmitter.broadcast(
                command_library.PING_PAYLOAD, duration=0.5,
            )
        pulse_pixel_and_fire(payload)
    else:
        status_setter(f"Playing: {name}", 0x00FFFF)
        play_chime()
        if needs_ping:
            pixel.fill((30, 30, 30))
            ble_transmitter.broadcast(
                command_library.PING_PAYLOAD, duration=0.5,
            )
        total = len(payload)
        for i, step in enumerate(payload):
            step_bytes, hold, color = step
            status_setter(f"{name}  {i + 1}/{total}", 0x00FFFF)
            pixel.fill(color)
            ble_transmitter.broadcast(step_bytes, duration=hold)
        pixel.fill((0, 0, 0))
    status_setter("Ready", 0x404040)


def _listen_capture_loop(seen):
    '''BLE scanning loop for run_listen_mode. Returns when user holds B.

    seen: dict[bytes, list] mapping payload to [first_seen, count, rssi].
    Mutates seen in place. Returns total elapsed seconds.
    '''
    total_count = 0
    last_rssi = None
    start_time = time.monotonic()
    last_ui_update = 0.0
    adapter = _bleio.adapter
    if not adapter.enabled:
        adapter.enabled = True

    while True:
        button_b.update()
        button_a.update()
        # Require a long-press to exit listening mode, so accidental
        # B taps during a show don't end recording.
        if button_b.long_press:
            break
        try:
            for entry in adapter.start_scan(
                    interval=0.04, window=0.04,
                    minimum_rssi=-100, timeout=0.2,
                    extended=False, active=False):
                payload = _extract_disney_payload(entry.advertisement_bytes)
                if payload is None:
                    continue
                total_count += 1
                last_rssi = entry.rssi
                key = bytes(payload)
                if key in seen:
                    seen[key][1] += 1
                    seen[key][2] = entry.rssi
                else:
                    seen[key] = [time.monotonic() - start_time, 1, entry.rssi]
        finally:
            adapter.stop_scan()
        # Throttle UI updates to once per second to limit bitmap
        # reallocation churn (memory is tight on the CLUE).
        now = time.monotonic()
        if now - last_ui_update >= 1.0:
            last_ui_update = now
            listen_view.update_stats(now - start_time, total_count,
                                     len(seen), last_rssi)
    return time.monotonic() - start_time


def _save_capture_with_fallback(seen, elapsed):
    '''Try to save. If FS is read-only, set NVM flag for next-boot retry.'''
    try:
        path = _save_capture(seen, elapsed)
        short = path.split("/")[-1]
        listen_view.set_status(f"Saved: {short}  B", 0x00FF00)
    except OSError as err:
        # Filesystem is read-only - host has ownership. Set NVM flag
        # so next reset auto-creates the marker and enters capture mode.
        try:
            microcontroller.nvm[0] = 1
            listen_view.set_status("Reset to enable save  B", 0xFF8000)
        except (AttributeError, ImportError):
            listen_view.set_status(f"Save fail: {err}  B", 0xFF0000)


def _wait_for_dismiss_press():
    '''Wait for the next short B-press to dismiss the save confirmation.

    The user was holding B to stop capture, so adafruit_debouncer.Button
    has already emitted a long_press for that hold. We just need to wait
    for the next short_count tick - the debouncer handles release-detect
    and debounce timing internally.
    '''
    while True:
        button_b.update()
        if button_b.short_count > 0:
            return


def run_listen_mode():
    '''Enter BLE listening mode - capture unique 0x0183 packets to file.

    Stops broadcasting, starts BLE scanning, transitions UI to the
    listen view. User holds B to stop and save the capture.
    '''
    # Aggressively free memory before allocating capture state.
    gc.collect()
    display.root_group = listen_view.group
    note_activity()
    if supervisor.runtime.usb_connected:
        listen_view.set_status("USB - hold B to stop", 0xFF8000)
    else:
        listen_view.set_status("Hold B to stop")

    seen = {}  # payload bytes -> [first_seen_time, count, last_rssi]
    elapsed = _listen_capture_loop(seen)

    listen_view.set_status("Saving...", 0x00FFFF)
    _save_capture_with_fallback(seen, elapsed)
    _wait_for_dismiss_press()
    enter_grid()
    gc.collect()


def _extract_disney_payload(ad_bytes):
    '''Walk a BLE advert and extract the 0x0183 manufacturer payload.'''
    DISNEY_CID = 0x0183
    i = 0
    while i < len(ad_bytes):
        length = ad_bytes[i]
        if length == 0 or i + 1 + length > len(ad_bytes):
            break
        ad_type = ad_bytes[i + 1]
        if ad_type == 0xFF and length >= 3:
            cid = ad_bytes[i + 2] | (ad_bytes[i + 3] << 8)
            if cid == DISNEY_CID:
                return bytes(ad_bytes[i + 4:i + 1 + length])
        i += 1 + length
    return None


def _save_capture(seen, total_elapsed):
    '''Write captured packets to /captures/listen_NNN.txt.

    Returns the file path on success. Raises OSError if the filesystem
    is not writable (e.g., USB host has ownership of the drive).
    '''
    # Find next available sequence number
    base_dir = "/captures"
    try:
        os.mkdir(base_dir)
    except OSError:
        pass  # already exists
    existing = []
    try:
        existing = os.listdir(base_dir)
    except OSError:
        pass
    seq = 0
    while f"listen_{seq:03d}.txt" in existing:
        seq += 1
    path = f"{base_dir}/listen_{seq:03d}.txt"
    with open(path, "w", encoding="utf-8") as out:
        out.write(f"# Listen capture, total elapsed {total_elapsed:.1f}s\n")
        out.write(f"# {len(seen)} unique packets captured\n")
        out.write("# format: first_seen_s rssi count hex\n")
        # Sort by first_seen for readable chronological log
        items = sorted(seen.items(), key=lambda kv: kv[1][0])
        for payload, info in items:
            first_seen, count, rssi = info
            out.write(f"{first_seen:.3f} {rssi:>4} {count:>4} {payload.hex()}\n")
    return path


def fire_off(status_setter):
    '''Shortcut to broadcast the OFF command with distinct visual feedback.'''
    _, payload, _ = command_library.OFF_COMMAND
    gc.collect()
    status_setter("Off", 0xFF4040)
    play_chime()
    pixel.fill((40, 40, 40))
    ble_transmitter.broadcast(payload, duration=1.5)
    pixel.fill((0, 0, 0))
    status_setter("Ready", 0x404040)


# Precompute the pool of commands eligible for shake-random firing.
# Excluded:
#   - Custom sub-protocol commands (Ears Battery, Ears Brightness) -
#     payload starts with 0xAA. These only affect the QT Py ears, not
#     bands/wands, and would feel arbitrary as a random selection.
#   - The LISTEN sentinel - it triggers BLE capture mode, not a fire.
# Otherwise we include all commands. needs_ping=True commands still get
# their wake-ping when fired (handled by fire_command).
_RELIABLE_COMMANDS = []
for _cat_idx, (_, _commands) in enumerate(_PALETTE):
    for _cmd in _commands:
        _payload = _cmd[1]
        # Skip sentinel command
        if _payload == b"LISTEN":
            continue
        # Skip our custom sub-protocol packets (start with 0xAA)
        if (isinstance(_payload, bytes) and len(_payload) > 0
                and _payload[0] == 0xAA):
            continue
        # Sequences (tuple of step tuples) are kept - their first step's
        # bytes are the command marker. Sequences don't use the AA prefix.
        _RELIABLE_COMMANDS.append((_cat_idx, _cmd))

# Silent mode mutes the CLUE's piezo chime. Toggled with a long press on A.
# Stored in a single-element list so button handlers can mutate without
# needing `global`.
_silent_mode = [False]


def toggle_silent(status_setter):
    '''Flip silent mode and show brief confirmation in the status bar.'''
    _silent_mode[0] = not _silent_mode[0]
    if _silent_mode[0]:
        status_setter("Silent ON", 0xFFAA00)
    else:
        status_setter("Silent OFF", 0x40C0FF)


# --- Display sleep management ---
# When no buttons have been pressed or commands fired within
# DISPLAY_SLEEP_TIMEOUT_S, the TFT backlight turns off to save power.
# Any button press wakes it immediately.
#
# Primary mechanism: display.brightness = 0.0, which on the CLUE drives
# the backlight PWM pin to 0% duty cycle.
_last_activity_time = [time.monotonic()]
_display_sleeping = [False]


def note_activity():
    '''Mark the current moment as user-active - wake display if sleeping.'''
    _last_activity_time[0] = time.monotonic()
    if _display_sleeping[0]:
        display.brightness = DISPLAY_ACTIVE_BRIGHTNESS
        _display_sleeping[0] = False
        print(f"[DISPLAY] wake at t={time.monotonic():.1f}s")


def check_display_sleep():
    '''Called every loop iteration - put display to sleep if idle too long.'''
    if _display_sleeping[0]:
        return
    idle_s = time.monotonic() - _last_activity_time[0]
    if idle_s >= DISPLAY_SLEEP_TIMEOUT_S:
        display.brightness = 0.0
        _display_sleeping[0] = True
        print(f"[DISPLAY] sleep at t={time.monotonic():.1f}s"
              f" (idle for {idle_s:.0f}s)")


def enter_light_sleep():
    '''Put the CLUE into light sleep. Wakes on A or B button press.

    Light sleep suspends the running program until an alarm fires.
    Unlike deep sleep, Python state is preserved - selected category,
    silent mode, etc. all stay in RAM. We use light sleep (not deep
    sleep) because CP 10.1.4 deep sleep on nRF52 has known reliability
    issues; light sleep works correctly and gives meaningful power
    savings for wearable-scale sessions.

    Returns the two new PinAlarm objects so the caller can deinit them
    and re-setup button handling after wake. This function does NOT
    reinit the buttons itself (doing so requires module-scope
    reassignment which complicates the function signature).
    '''
    # Fade out chime speaker if it was running (shouldn't be, but safe)
    speaker.duty_cycle = 0
    # Turn off onboard status pixel
    pixel.fill((0, 0, 0))
    # Turn off display backlight
    display.brightness = 0.0

    # Release the digital pins before setting up PinAlarm on the same
    # pins. The adafruit_debouncer.Button wrapper doesn't have deinit()
    # itself - we only need to release the underlying DigitalInOut
    # objects (btn_a_io and btn_b_io).
    btn_a_io.deinit()
    btn_b_io.deinit()

    # Wait for both buttons to actually be released before arming the
    # PinAlarms. Without this pause, the still-held state of the triggering
    # buttons would fire the wake alarm immediately (level-triggered alarms
    # fire as soon as they see the "pressed" state, which is what started
    # the sleep in the first place).
    # Brief temporary reads to detect release
    _wait_release_a = digitalio.DigitalInOut(board.BUTTON_A)
    _wait_release_a.switch_to_input(pull=digitalio.Pull.UP)
    _wait_release_b = digitalio.DigitalInOut(board.BUTTON_B)
    _wait_release_b.switch_to_input(pull=digitalio.Pull.UP)
    # Buttons are active-low: .value == True means released
    _release_deadline = time.monotonic() + 3.0  # safety cap
    while time.monotonic() < _release_deadline:
        if _wait_release_a.value and _wait_release_b.value:
            break
        time.sleep(0.05)
    _wait_release_a.deinit()
    _wait_release_b.deinit()

    # Configure pin alarms on both buttons. NRF requires level-triggered
    # (edge=False) with value=False (active low since buttons pull to
    # ground when pressed) and pull=True (enable internal pull-up).
    pin_alarm_a = alarm.pin.PinAlarm(
        pin=board.BUTTON_A, value=False, pull=True)
    pin_alarm_b = alarm.pin.PinAlarm(
        pin=board.BUTTON_B, value=False, pull=True)

    print("[LIGHT SLEEP] entering")
    # Blocks here until an alarm fires. On wake, execution resumes.
    alarm.light_sleep_until_alarms(pin_alarm_a, pin_alarm_b)
    print("[LIGHT SLEEP] woken")

    # PinAlarm objects don't expose deinit() - they release their pins
    # when garbage collected. Drop the references and force a gc pass
    # so the pins are available for DigitalInOut recreation by the
    # caller.
    del pin_alarm_a
    del pin_alarm_b
    gc.collect()


def pick_random_command():
    '''Pick a random reliable command from the no-ping-needed pool.

    Falls back to the full library if nothing is marked reliable.
    '''
    if _RELIABLE_COMMANDS:
        return _RELIABLE_COMMANDS[random.randint(0, len(_RELIABLE_COMMANDS) - 1)]
    cat_idx = random.randint(0, len(_PALETTE) - 1)
    commands = _PALETTE[cat_idx][1]
    command = commands[random.randint(0, len(commands) - 1)]
    return cat_idx, command


def shake_magnitude():
    '''Return the current accelerometer magnitude in m/s^2.'''
    a_x, a_y, a_z = accel.acceleration
    return (a_x * a_x + a_y * a_y + a_z * a_z) ** 0.5


def enter_list(cat_idx):
    '''Switch to list view for the given category index.'''
    gc.collect()
    name, commands = _PALETTE[cat_idx]
    list_view.load_category(cat_idx, name, commands)
    display.root_group = list_view.group


def enter_grid():
    '''Switch back to the grid view.'''
    display.root_group = grid_view.group


def enter_confirm(name):
    '''Switch to the confirm modal for a random-picked command.'''
    confirm_view.set_command(name)
    display.root_group = confirm_view.group


def handle_grid(last_shake_time):
    '''Input handling while the grid view is active.'''
    if button_b.long_press:
        fire_off(grid_view.set_status)
        return _STATE_GRID, last_shake_time, None, None
    if button_a.short_count == 3:
        toggle_silent(grid_view.set_status)
        return _STATE_GRID, last_shake_time, None, None
    if button_a.short_count == 2:
        enter_list(grid_view.selected)
        return _STATE_LIST, last_shake_time, None, None
    if button_a.short_count == 1:
        grid_view.prev_tile()
    if button_b.short_count == 1:
        grid_view.next_tile()
    now = time.monotonic()
    if shake_magnitude() > _SHAKE_THRESHOLD and now - last_shake_time > _SHAKE_COOLDOWN:
        cat_idx, command = pick_random_command()
        grid_view.set_tile(cat_idx)
        enter_confirm(command[0])
        return _STATE_CONFIRM, now, command, _STATE_GRID
    return _STATE_GRID, last_shake_time, None, None


def handle_list(last_shake_time):
    '''Input handling while the list view is active.

    Single-exit cascade: each branch sets `result`, then returns at the
    bottom. Keeps return count under the lint limit while preserving
    the early-exit semantics via `done`.
    '''
    result = (_STATE_LIST, last_shake_time, None, None)
    done = False
    if button_b.long_press:
        fire_off(list_view.set_status)
        done = True
    elif button_a.short_count == 3:
        toggle_silent(list_view.set_status)
        done = True
    elif button_a.short_count == 2:
        command = list_view.selected_command
        if command is not None:
            fire_command(command, list_view.set_status)
            # Listen mode sentinel - run_listen_mode() has already
            # swapped the display to grid_view, so update state too.
            if command[1] == b"LISTEN":
                result = (_STATE_GRID, last_shake_time, None, None)
        done = True
    elif button_b.short_count == 2:
        enter_grid()
        result = (_STATE_GRID, last_shake_time, None, None)
        done = True
    if not done:
        if button_a.short_count == 1:
            list_view.scroll_up()
        if button_b.short_count == 1:
            list_view.scroll_down()
        now = time.monotonic()
        if (shake_magnitude() > _SHAKE_THRESHOLD
                and now - last_shake_time > _SHAKE_COOLDOWN):
            _cat_idx, command = pick_random_command()
            enter_confirm(command[0])
            result = (_STATE_CONFIRM, now, command, _STATE_LIST)
    return result

def handle_confirm(pending, return_state, last_shake_time):
    '''Input handling while the confirm modal is active.'''
    if button_a.short_count == 2:
        setter = list_view.set_status if return_state == _STATE_LIST else grid_view.set_status
        if return_state == _STATE_LIST:
            display.root_group = list_view.group
        else:
            display.root_group = grid_view.group
        fire_command(pending, setter)
        return return_state, last_shake_time, None, None
    if button_b.short_count == 1:
        if return_state == _STATE_LIST:
            display.root_group = list_view.group
        else:
            display.root_group = grid_view.group
        return return_state, last_shake_time, None, None
    return _STATE_CONFIRM, last_shake_time, pending, return_state


state = _STATE_GRID
last_shake = 0.0
pending_command = None
pending_return = None

# Track when both A and B are pressed simultaneously for light sleep
# trigger. Requires a minimum hold time (~0.8s) so incidental button
# combos during normal use don't accidentally sleep the device.
_DUAL_HOLD_TRIGGER_S = 0.8
_dual_pressed_since = None

while True:
    button_a.update()
    button_b.update()

    # Detect A+B held for deep sleep. Uses .value (stable debounced state)
    # not .pressed (one-shot event). Hold both for _DUAL_HOLD_TRIGGER_S
    # to commit the sleep action.
    both_held = (not button_a.value) and (not button_b.value)
    if both_held:
        if _dual_pressed_since is None:
            _dual_pressed_since = time.monotonic()
        elif time.monotonic() - _dual_pressed_since >= _DUAL_HOLD_TRIGGER_S:
            grid_view.set_status("Sleep...", 0xFF4080)
            list_view.set_status("Sleep...", 0xFF4080)
            # Wait for user to release BOTH buttons before starting
            # light sleep. If we sleep while buttons are still held,
            # the PinAlarm (level-triggered on value=False) would
            # immediately fire and wake us right back up.
            while not button_a.value or not button_b.value:
                button_a.update()
                button_b.update()
                time.sleep(0.02)
            time.sleep(0.15)  # settle time to avoid bounce
            enter_light_sleep()
            # After wake, the button IO pins were deinit'd for PinAlarm
            # and need to be re-established for normal polling.
            btn_a_io = digitalio.DigitalInOut(board.BUTTON_A)
            btn_a_io.switch_to_input(pull=digitalio.Pull.UP)
            btn_b_io = digitalio.DigitalInOut(board.BUTTON_B)
            btn_b_io.switch_to_input(pull=digitalio.Pull.UP)
            button_a = Button(btn_a_io, value_when_pressed=False,
                              short_duration_ms=200, long_duration_ms=800)
            button_b = Button(btn_b_io, value_when_pressed=False,
                              short_duration_ms=200, long_duration_ms=800)
            # Restore the display and reset activity timer
            display.brightness = DISPLAY_ACTIVE_BRIGHTNESS
            _last_activity_time[0] = time.monotonic()
            _display_sleeping[0] = False
            grid_view.set_status("Awake!", 0x40C0FF)
            list_view.set_status("Awake!", 0x40C0FF)
            _dual_pressed_since = None
            # Skip the rest of this frame so handlers don't see stale
            # button state from the wake press
            continue
        # While both are held (but not yet DUAL_HOLD threshold), skip
        # individual button handlers so they don't fire silent-toggle
        # or similar from the collateral press.
        check_display_sleep()
        time.sleep(0.02)
        continue
    _dual_pressed_since = None

    # Wake display on any button activity
    if (button_a.short_count > 0 or button_b.short_count > 0
            or button_a.long_press or button_b.long_press):
        note_activity()

    if state == _STATE_GRID:
        state, last_shake, pending_command, pending_return = handle_grid(last_shake)
    elif state == _STATE_LIST:
        state, last_shake, pending_command, pending_return = handle_list(last_shake)
    else:
        state, last_shake, pending_command, pending_return = handle_confirm(
            pending_command, pending_return, last_shake,
        )
    check_display_sleep()
    time.sleep(0.02)
