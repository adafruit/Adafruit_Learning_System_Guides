# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''MagicBand+ Beacon Ears main loop.

Scans for Disney BLE adverts and renders matching commands on stereo
NeoPixel Jewels. Two logical zones (left ear, right ear) are rendered
with stereo phase offsets to give static colors a gentle out-of-phase
breathing animation and rotations a left-leads-right sweep.
'''
# pylint: disable=redefined-outer-name
# Setup and main loop are inlined at module level (no main() wrapper).
# Helper functions defined above take parameters named the same as the
# inlined module-level loop variables (zone, t, etc) - this is expected
# and harmless: helpers and the inline body never share scope at runtime.
# Target: Adafruit QT Py ESP32-S3 - the BLE Beacon Ears
import math
import random
import time

import _bleio
import board
import digitalio
from adafruit_debouncer import Button

import battery as battery_mod
import magicband_protocol
import pixel_zones
import renderer

# 15 fps target -> ~66ms per frame.
_TARGET_FPS = 15
_FRAME_BUDGET_S = 1.0 / _TARGET_FPS

# BLE scan timing.
# interval and window equal means continuous scanning. Each scan burst is
# 40ms long which is our per-frame scan budget, then we render and sleep
# for the rest of the frame. This preserves smooth 15fps animation during
# active commands.
_SCAN_INTERVAL_S = 0.04
_SCAN_WINDOW_S = 0.04

_MIN_RSSI = -90
_DEDUP_WINDOW_S = 2.5

# Custom-protocol triggers (Ears Brightness) are broadcast by the CLUE
# for ~3 seconds per fire. The normal dedup window is 2.5s, so the same
# trigger packet would be accepted a second time near the end of the
# CLUE's broadcast. Use a longer cooldown specifically for these
# packets to guarantee one-fire-per-press behavior.
_TRIGGER_COOLDOWN_S = 4.0

# Disney park location beacons broadcast continuously - not just at the
# Fab 50 statues but also throughout attractions. They blast many packets
# per second per beacon. This long cooldown ensures the swirl animation
# fires only occasionally as you walk through the park, not every few
# seconds.
_STATUE_COOLDOWN_S = 30.0

# NeoPixel brightness presets cycled by a long-press of the BOOT button.
# Index 0 is the default used at startup. Keep presets modest - NeoPixels
# look much brighter on video cameras than to the eye, and at night even
# 0.02 reads clearly on the headband.
_BRIGHTNESS_PRESETS = (0.02, 0.04, 0.08)
# How long the BOOT button must be held to count as a long press.
# Short press cycles brightness preset (the more frequently-used action).
# Long press shows the battery level (less frequent, requires intent).
LONG_PRESS_S = 0.5
_BRIGHTNESS_FLASH_DURATION_S = 0.6

# USB-presence detection threshold (raw QT Py voltage reading).
# When charging via USB, the BFF charger pulls cell voltage up to ~4.20V
# which the QT Py reads as ~4.85V raw (uncalibrated ADC). True battery
# voltage even at 100% charge sits below 4.20V (typically 4.10-4.15V
# rest voltage), so a raw reading > 4.75V is a reliable indicator of
# USB power being present.
#
# We use this to gate the battery display: WS2812 NeoPixel timing gets
# corrupted on battery power (voltage sag during current spikes makes
# green data display as red), so we only show the full battery animation
# when on USB. On battery, BOOT short-press / Ears Battery shows a brief
# yellow flash instead - intuitive "plug in to check" feedback.
_USB_PRESENT_V_RAW = 4.75
_UNAVAILABLE_FLASH_DURATION_S = 0.6
_UNAVAILABLE_FLASH_COLOR = (255, 180, 0)  # yellow - safe color on battery

# On-demand battery display (BOOT short press or CLUE Ears Battery).
# 3-second animated display showing battery level on both jewels.
_BATTERY_DISPLAY_FILL_S = 1.2
_BATTERY_DISPLAY_HOLD_S = 1.5
_BATTERY_DISPLAY_FADE_S = 0.3
_BATTERY_DISPLAY_DURATION_S = (_BATTERY_DISPLAY_FILL_S
                                + _BATTERY_DISPLAY_HOLD_S
                                + _BATTERY_DISPLAY_FADE_S)

# Voltage thresholds tuned to QT Py's RAW (uncalibrated) ADC readings.
# The ESP32-S3 ADC reads ~0.65V higher than actual, so these numbers
# look high relative to true LiPo voltages. They are calibrated to
# match what the QT Py reports when battery is at the corresponding
# real charge level.
#
# QT Py raw reading | Real cell voltage | Visual
# ----------------- | ----------------- | ------
# > 4.85V           | > 4.20V (full)    | 6 green
# > 4.70V           | > 4.05V (~80%)    | 5 green
# > 4.55V           | > 3.92V (~50%)    | 4 yellow
# > 4.40V           | > 3.79V (~30%)    | 3 yellow
# > 4.25V           | > 3.65V (~15%)    | 2 orange
# > 4.10V           | > 3.55V (~5%)     | 1 orange
# below             | < 3.55V critical  | red pulse
#
# The right-hand "real voltage" column was derived from Pedro's
# reference reading (Feather S2 voltage monitor showed 4.17V while
# QT Py raw read 4.83V). This is approximate; real-world calibration
# may shift these thresholds by ~0.05-0.10V.
_BATTERY_LEVELS = (
    (4.85, 6, (0, 180, 0)),     # full green
    (4.70, 5, (0, 180, 0)),     # green
    (4.55, 4, (180, 180, 0)),   # yellow
    (4.40, 3, (180, 180, 0)),   # yellow
    (4.25, 2, (220, 110, 0)),   # orange
    (4.10, 1, (220, 110, 0)),   # orange
)
_BATTERY_CRITICAL_RGB = (220, 0, 0)
_BATTERY_UNKNOWN_RGB = (120, 0, 120)
_OUTER_RING_COUNT = 6

# Solo mode: lets the ears cycle through a curated showpiece reel without
# a CLUE remote nearby. Designed for solo demos and pickup video shots.
# Triple-press the BOOT button to toggle, double-press to skip the current
# showpiece, single-press still cycles brightness, long-press still shows
# battery. Real BLE packets interrupt solo cleanly so park interaction
# still works while solo is enabled - wearer doesn't manage state.
_SOLO_BREATH_S = 0.5         # idle gap between showpieces
_SOLO_DEFAULT_DURATION_S = 9.5  # fallback when a showpiece has no timing

# Solo enter/exit indicator pulses. Sized to read clearly on camera so
# the moment of toggling is obvious in B-roll.
_SOLO_INDICATOR_ENTER_S = 0.6   # white burst: 200ms hold + 400ms fade
_SOLO_INDICATOR_EXIT_S = 0.7    # cool blue triangle pulse
_SOLO_EXIT_RGB = (40, 100, 220)

# Debouncer multi-press timing windows.
# short_duration_ms is how long after a release the debouncer waits before
# committing a multi-press count. 350ms is a common sweet spot - tight
# enough that single-press brightness cycling still feels responsive,
# wide enough that comfortable triple-presses register reliably.
BUTTON_SHORT_MS = 350
BUTTON_LONG_MS = int(LONG_PRESS_S * 1000)


def _build_showpieces():
    '''Construct the solo-mode showpiece reel as parsed command dicts.

    Each entry goes through magicband_protocol.parse() so the renderer
    treats it identically to a live BLE packet. Park captures from
    Epcot/MK can be added by appending raw payloads here.
    '''
    mp = magicband_protocol
    # 9.5s timing byte: scaler off, no fade, time_val=2 -> 1.5*2 + 6.5
    timing_short = 0x02
    showpieces = (
        # Headliners: firmware-baked rainbow rotation
        ("Taste the Rainbow", mp.parse(
            bytes.fromhex("e100e90c000f0f5d465bf00532374830b0"))),
        # 5-palette cycle, cruise-line warm rainbow
        ("DCL Rainbow", mp.parse(bytes((
            0xE1, 0x00, 0xE9, 0x0C, 0x00, 0x05, 0x0F,
            0x15,  # Red
            0x13,  # Orange
            0x10,  # Off Yellow
            0x19,  # Green
            0x07,  # Deep Purple
            0xB0)))),
        # Dual-color combos
        ("Red+Cyan", mp.parse(
            mp.build_dual_color(0x15, 0x00, timing=timing_short))),
        ("Purple+Yellow", mp.parse(
            mp.build_dual_color(0x07, 0x10, timing=timing_short))),
        # Five-color combos
        ("5C Rainbow", mp.parse(
            mp.build_five_color(
                center=0x10, top_left=0x15, bottom_left=0x13,
                bottom_right=0x19, top_right=0x07,
                timing=timing_short))),
        ("5C Sunset", mp.parse(
            mp.build_five_color(
                center=0x13, top_left=0x08, bottom_left=0x14,
                bottom_right=0x0F, top_right=0x10,
                timing=timing_short))),
        # 6-bit RGB demo - deep "Disney blue" the palette can't hit
        ("RGB6 Disney Blue", mp.parse(
            mp.build_six_bit_color(8, 24, 60, timing=timing_short))),
        # --- Disney park show captures (Epcot, April 2026) ---
        # Color labels match what was visually observed during capture.
        # Payloads come straight from BLE listen logs. Long-format
        # variants (E9 10/13, EA 14) aren't fully decoded yet so the
        # renderer falls back to a generic park-show pulse with a
        # payload-derived primary hue. Capture 6 (purple orange) had
        # no obvious show packet in its log so it's omitted here.
        ("Show: blue", mp.parse(bytes.fromhex(
            "e91300b60f404458f44882d06519d146060a307bff"))),
        ("Show: white light blue", mp.parse(bytes.fromhex(
            "e90800b50fa8a3b3b3a3"))),
        ("Show: rainbow", mp.parse(bytes.fromhex(
            "e90400010efd"))),
        ("Show: blue green", mp.parse(bytes.fromhex(
            "e90800f40fa0a4b9b9a4"))),
        ("Show: white sparkling", mp.parse(bytes.fromhex(
            "ea140100410f434858f44882d06520d1460208307b40"))),
        ("Show: orange red sparkle", mp.parse(bytes.fromhex(
            "e910000f0f545d58f44882d146090ad06528"))),
    )
    return showpieces


_SHOWPIECES = _build_showpieces()


def _pick_showpiece_idx(last_idx):
    '''Pick a random showpiece index that isn't the same as last_idx.'''
    if len(_SHOWPIECES) <= 1:
        return 0
    candidates = [i for i in range(len(_SHOWPIECES)) if i != last_idx]
    return random.choice(candidates)


def _render_solo_enter(zones, t):
    '''White burst indicator: full hold for 200ms, fade over 400ms.'''
    if t < 0.2:
        envelope = 1.0
    else:
        envelope = max(0.0, 1.0 - (t - 0.2) / 0.4)
    color = (int(255 * envelope),) * 3
    for zone in zones:
        zone.fill(color)


def _render_solo_exit(zones, t):
    '''Cool blue pulse indicator: triangle envelope over 700ms.'''
    frac = t / _SOLO_INDICATOR_EXIT_S
    if frac < 0.4:
        envelope = frac / 0.4
    else:
        envelope = max(0.0, (1.0 - frac) / 0.6)
    color = (int(_SOLO_EXIT_RGB[0] * envelope),
             int(_SOLO_EXIT_RGB[1] * envelope),
             int(_SOLO_EXIT_RGB[2] * envelope))
    for zone in zones:
        zone.fill(color)


def _battery_level_match(voltage):
    '''Return (count, rgb) for the given voltage, or None for critical.'''
    if voltage is None:
        return None
    for threshold, count, rgb in _BATTERY_LEVELS:
        if voltage >= threshold:
            return (count, rgb)
    return None  # below lowest threshold = critical


def _render_battery_critical(zones, voltage, t):
    '''Single-pixel critical/unknown battery animation.

    Used when voltage is too low to map to a level, or when no reading
    is available. A pixel swirls around the outer ring for 1s, then
    settles on a fixed location.
    '''
    if voltage is None:
        color = _BATTERY_UNKNOWN_RGB
    else:
        # Critical - pulsing red with a faster animation
        pulse = 0.4 + 0.6 * math.sin(2 * math.pi * t * 2.5)
        color = (int(_BATTERY_CRITICAL_RGB[0] * pulse),
                 int(_BATTERY_CRITICAL_RGB[1] * pulse),
                 int(_BATTERY_CRITICAL_RGB[2] * pulse))
    for zone in zones:
        zone.set_led(0, (0, 0, 0))
        if t < 1.0:
            head = int(t / 0.17) % _OUTER_RING_COUNT
            for i in range(1, zone.count):
                zone.set_led(i, color if (i - 1) == head else (0, 0, 0))
        else:
            for i in range(1, zone.count):
                zone.set_led(i, color if i == 1 else (0, 0, 0))


def _battery_phase1_swirl(zones, t, fill_end, target_count, rgb):
    '''Phase 1: swirling fill - leading-edge sweeps the ring.'''
    sweep_pos = (t / fill_end) * _OUTER_RING_COUNT
    for zone in zones:
        zone.set_led(0, (0, 0, 0))
        for i in range(1, zone.count):
            ring_idx = i - 1
            distance_since_passed = sweep_pos - (ring_idx + 1)
            if distance_since_passed < 0:
                zone.set_led(i, (0, 0, 0))
            elif distance_since_passed < 0.5:
                if ring_idx + 1 <= target_count:
                    zone.set_led(i, rgb)
                else:
                    fade = max(0.0, 1.0 - distance_since_passed * 2)
                    zone.set_led(i, (int(60 * fade),) * 3)
            else:
                zone.set_led(i, rgb if ring_idx + 1 <= target_count else (0, 0, 0))


def _battery_phase2_hold(zones, hold_t, target_count, rgb):
    '''Phase 2: gentle pulse on filled-in pixels.'''
    pulse = 0.9 + 0.1 * math.sin(2 * math.pi * hold_t / 1.2)
    pulsed = (int(rgb[0] * pulse), int(rgb[1] * pulse), int(rgb[2] * pulse))
    for zone in zones:
        zone.set_led(0, (0, 0, 0))
        for i in range(1, zone.count):
            zone.set_led(i, pulsed if (i - 1) + 1 <= target_count else (0, 0, 0))


def _battery_phase3_fade(zones, fade_t, target_count, rgb):
    '''Phase 3: smoothly fade filled pixels to black.'''
    fade_fraction = max(0.0, 1.0 - fade_t / _BATTERY_DISPLAY_FADE_S)
    if fade_fraction < 0.1:
        faded = (0, 0, 0)
    else:
        faded = (int(rgb[0] * fade_fraction),
                 int(rgb[1] * fade_fraction),
                 int(rgb[2] * fade_fraction))
    for zone in zones:
        zone.set_led(0, (0, 0, 0))
        for i in range(1, zone.count):
            zone.set_led(i, faded if (i - 1) + 1 <= target_count else (0, 0, 0))


def _render_battery_display(zones, voltage, t):
    '''Paint both jewels with an animated battery level indicator.

    - Phase 1 (fill): a single leading-edge pixel sweeps around the outer
      ring, leaving lit pixels behind it up to the target count.
    - Phase 2 (hold): all active pixels glow with a gentle pulse.
    - Phase 3 (fade): all pixels smoothly dim to black.
    '''
    matched = _battery_level_match(voltage)

    # Diagnostic: log path on first frame
    if t < 0.05:
        v_str = f"{voltage:.3f}V" if voltage is not None else "None"
        if matched is None:
            print(f"[battery render] {v_str} -> CRITICAL/unknown path")
        else:
            print(f"[battery render] {v_str} -> {matched[0]} pixels")

    if matched is None:
        _render_battery_critical(zones, voltage, t)
        return

    target_count, rgb = matched
    fill_end = _BATTERY_DISPLAY_FILL_S
    hold_end = fill_end + _BATTERY_DISPLAY_HOLD_S
    if t < fill_end:
        _battery_phase1_swirl(zones, t, fill_end, target_count, rgb)
    elif t < hold_end:
        _battery_phase2_hold(zones, t - fill_end, target_count, rgb)
    else:
        _battery_phase3_fade(zones, t - hold_end, target_count, rgb)


# Custom sub-protocol for remote-triggered actions.
# Uses the 0x0183 Disney CID but with a first byte (0xAA) that is
# neither MagicBand+ (E1/E2/CC) nor Starlight Wand (CF/C0). Real bands
# and wands ignore packets they don't recognize, so this is safe.
# Command byte:
#   0x01 = show battery level
#   0x03 = cycle brightness preset
#   0x04 = find me
#   0x05 = statue animation preview
# Remote-trigger packet table. Sub-protocol: AA42xx is sent only by the
# CLUE remote. Real bands and wands ignore packets they don't recognize,
# so this is safe alongside MagicBand+ (E1/E2/CC), wand (CF), and
# Fab 50 statue (C4) traffic.
REMOTE_COMMANDS = {
    bytes.fromhex("aa4201"): "battery",
    bytes.fromhex("aa4203"): "brightness",
    bytes.fromhex("aa4204"): "find",
    bytes.fromhex("aa4205"): "statue",
}


def remote_command(payload):
    '''Return the remote-trigger command name, or None if not a trigger.'''
    return REMOTE_COMMANDS.get(bytes(payload[:3]))


def _extract_disney_payload(ad_bytes):
    '''Walk a BLE advert and extract the 0x0183 manufacturer payload.'''
    i = 0
    while i < len(ad_bytes):
        length = ad_bytes[i]
        if length == 0 or i + 1 + length > len(ad_bytes):
            break
        ad_type = ad_bytes[i + 1]
        if ad_type == 0xFF and length >= 3:
            cid = ad_bytes[i + 2] | (ad_bytes[i + 3] << 8)
            if cid == magicband_protocol.DISNEY_CID:
                return bytes(ad_bytes[i + 4:i + 1 + length])
        i += 1 + length
    return None


def _log_command(label, rssi, raw):
    now = time.monotonic()
    print(f"[{now:8.2f}] rssi={rssi:>4}  {label}")
    print(f"           raw={raw.hex()}")


print("MagicBand+ BLE Beacon Ears")
print(f"BLE scan: window={_SCAN_WINDOW_S * 1000:.0f}ms"
      f"  interval={_SCAN_INTERVAL_S * 1000:.0f}ms")
print("-" * 60)

pixels = pixel_zones.StereoJewels(
    left_pin=board.A1, right_pin=board.A3,
    brightness=_BRIGHTNESS_PRESETS[0])
zones = pixels.make_zones()
brightness_idx = [0]

adapter = _bleio.adapter
if not adapter.enabled:
    adapter.enabled = True

batt = battery_mod.BatteryMonitor()

button_pin = digitalio.DigitalInOut(board.BUTTON)
button_pin.switch_to_input(pull=digitalio.Pull.UP)
button = Button(button_pin, value_when_pressed=False,
                short_duration_ms=BUTTON_SHORT_MS,
                long_duration_ms=BUTTON_LONG_MS)

active_state = None
active_started_at = 0.0
last_payload = None
last_payload_at = 0.0
brightness_flash_until = 0.0
brightness_flash_level = 0
last_trigger_time = 0.0
battery_display_until = 0.0
battery_display_started_at = 0.0
battery_display_voltage = None  # voltage snapshot at trigger time
unavailable_flash_until = 0.0   # yellow flash for "plug in to check"
unavailable_flash_started_at = 0.0
last_statue_trigger = 0.0       # last Fab 50 statue swirl fired
find_mode_until = 0.0           # find-me beacon animation end time
find_mode_started_at = 0.0
last_battery_log = 0.0
_BATTERY_LOG_INTERVAL_S = 60.0  # log raw voltage once per minute

# Solo mode state. solo_state is a renderer animation dict (same shape
# as active_state); solo_label / solo_idx / solo_started_at track the
# current showpiece. solo_indicator_* drives the enter/exit pulse.
solo_mode = False
solo_state = None
solo_label = ""
solo_idx = -1
solo_started_at = 0.0
solo_indicator_until = 0.0
solo_indicator_started_at = 0.0
solo_indicator_kind = None      # 'enter' or 'exit'

while True:
    frame_start = time.monotonic()

    new_command = None
    try:
        for entry in adapter.start_scan(
                interval=_SCAN_INTERVAL_S, window=_SCAN_WINDOW_S,
                minimum_rssi=_MIN_RSSI,
                timeout=_SCAN_WINDOW_S,
                extended=False, active=False):
            payload = _extract_disney_payload(entry.advertisement_bytes)
            if payload is None:
                continue
            if not payload:
                continue
            # Remote-trigger commands from the CLUE share a 4s cooldown.
            command = remote_command(payload)
            if command is not None:
                now = time.monotonic()
                if now - last_trigger_time < _TRIGGER_COOLDOWN_S:
                    continue
                last_trigger_time = now
                if command == "brightness":
                    brightness_idx[0] = (
                        (brightness_idx[0] + 1) % len(_BRIGHTNESS_PRESETS))
                    pixels.set_brightness(_BRIGHTNESS_PRESETS[brightness_idx[0]])
                    brightness_flash_until = now + _BRIGHTNESS_FLASH_DURATION_S
                    brightness_flash_level = brightness_idx[0]
                elif command == "battery":
                    # On battery power, WS2812 timing corruption makes
                    # the full animation unreliable (green renders as
                    # red). Show a brief yellow "plug in" flash on
                    # battery; full animation only on USB.
                    batt.update(force=True)
                    battery_display_voltage = batt.voltage
                    v_str = (f"{battery_display_voltage:.3f}V"
                             if battery_display_voltage is not None else "None")
                    if (battery_display_voltage is not None
                            and battery_display_voltage > _USB_PRESENT_V_RAW):
                        print(f"[battery trigger remote] {v_str} (USB)")
                        battery_display_until = now + _BATTERY_DISPLAY_DURATION_S
                        battery_display_started_at = now
                    else:
                        print(f"[battery trigger remote] {v_str} (yellow flash)")
                        unavailable_flash_until = now + _UNAVAILABLE_FLASH_DURATION_S
                        unavailable_flash_started_at = now
                elif command == "find":
                    # Forces max brightness for the 30s high-visibility
                    # animation, then restores the user's preset.
                    print("[find me] starting high-visibility animation")
                    pixels.set_brightness(1.0)
                    find_mode_until = now + renderer.FIND_MODE_DURATION_S
                    find_mode_started_at = now
                elif command == "statue":
                    # Fires the same golden swirl that real Fab 50
                    # statue beacons trigger - useful for demos.
                    print("[statue preview] firing golden swirl")
                    candidate = renderer.for_command({
                        "kind": "statue_beacon",
                        "statue_id": "PV",
                        "raw": bytes(payload),
                    })
                    if candidate is not None:
                        new_command = (candidate, entry.rssi, bytes(payload))
                continue
            # Accept MagicBand+ commands (E1/E2/CC), wand casts (CF),
            # and Fab 50 statue beacons (C4). Statue beacons trigger
            # a special golden-swirl animation rather than rendering
            # any of their content.
            is_mb = payload[0] in (0xE1, 0xE2, 0xCC)
            is_wand = magicband_protocol.is_wand_packet(payload)
            is_statue = (payload[0] == 0xC4 and len(payload) in (18, 23))
            if not (is_mb or is_wand or is_statue):
                continue
            now = time.monotonic()
            # Statues broadcast many packets per second per statue.
            # Use a longer cooldown specifically for statue triggers
            # to avoid restarting the swirl animation constantly.
            if is_statue:
                if now - last_statue_trigger < _STATUE_COOLDOWN_S:
                    continue
                last_statue_trigger = now
            else:
                if (payload == last_payload
                        and now - last_payload_at < _DEDUP_WINDOW_S):
                    continue
                last_payload = payload
                last_payload_at = now
            parsed = magicband_protocol.parse(payload)
            candidate = renderer.for_command(parsed)
            if candidate is not None:
                new_command = (candidate, entry.rssi, payload)
    finally:
        adapter.stop_scan()

    # --- Button check (BOOT button via adafruit_debouncer.Button) ---
    # short_count=1 -> cycle brightness
    # short_count=2 -> skip showpiece (solo mode only)
    # short_count>=3 -> toggle solo mode
    # long_press   -> show battery (USB) or yellow "plug in" flash
    button.update()
    if button.long_press:
        batt.update(force=True)
        battery_display_voltage = batt.voltage
        v_str = (f"{battery_display_voltage:.3f}V"
                 if battery_display_voltage is not None else "None")
        now = time.monotonic()
        if (battery_display_voltage is not None
                and battery_display_voltage > _USB_PRESENT_V_RAW):
            print(f"[battery trigger BOOT] {v_str} (USB - showing display)")
            battery_display_until = now + _BATTERY_DISPLAY_DURATION_S
            battery_display_started_at = now
        else:
            print(f"[battery trigger BOOT] {v_str} (battery - yellow flash)")
            unavailable_flash_until = now + _UNAVAILABLE_FLASH_DURATION_S
            unavailable_flash_started_at = now
    elif button.short_count >= 3:
        # Triple-press toggles solo mode.
        now = time.monotonic()
        solo_indicator_started_at = now
        if solo_mode:
            solo_mode = False
            solo_state = None
            solo_indicator_kind = "exit"
            solo_indicator_until = now + _SOLO_INDICATOR_EXIT_S
            print("[solo] exiting")
        else:
            solo_mode = True
            solo_idx = -1  # forces a fresh pick on next render
            solo_state = None
            solo_indicator_kind = "enter"
            solo_indicator_until = now + _SOLO_INDICATOR_ENTER_S
            print("[solo] entering")
    elif button.short_count == 2 and solo_mode:
        # Double-press in solo: skip to a new random showpiece.
        solo_state = None  # next render block picks a new one
        print("[solo] skipping to next showpiece")
    elif button.short_count == 1:
        # Single press: cycle brightness preset.
        brightness_idx[0] = (brightness_idx[0] + 1) % len(_BRIGHTNESS_PRESETS)
        new_b = _BRIGHTNESS_PRESETS[brightness_idx[0]]
        pixels.set_brightness(new_b)
        brightness_flash_until = time.monotonic() + _BRIGHTNESS_FLASH_DURATION_S
        brightness_flash_level = brightness_idx[0]

    # --- State update ---
    if new_command is not None:
        active_state, rssi, raw = new_command
        active_started_at = time.monotonic()
        _log_command(active_state["label"], rssi, raw)

    # --- Expiration check ---
    if active_state is not None:
        duration = active_state["duration_s"]
        if duration is not None:
            t = time.monotonic() - active_started_at
            if t >= duration:
                active_state = None

    # --- Battery monitor ---
    # update() internally throttles to every 5 seconds, so calling
    # every frame is cheap. No state machine - we just keep a fresh
    # voltage available for the on-demand display.
    batt.update()
    # Log raw voltage occasionally to help tune thresholds
    now = time.monotonic()
    if (batt.voltage is not None
            and now - last_battery_log >= _BATTERY_LOG_INTERVAL_S):
        last_battery_log = now
        level = _battery_level_match(batt.voltage)
        level_str = f"{level[0]} pixels" if level else "CRITICAL"
        print(f"[battery] raw={batt.voltage:.3f}V -> {level_str}")

    # --- Render frame ---
    frame_t = time.monotonic()
    # Find Me beacon takes priority over EVERYTHING - including
    # brightness flashes, animations, idle. Forces visibility for
    # the full 30 seconds. When it ends, restore the user's
    # brightness preset.
    if 0.0 < find_mode_until <= frame_t:
        # Animation just finished - restore user's brightness preset
        pixels.set_brightness(_BRIGHTNESS_PRESETS[brightness_idx[0]])
        find_mode_until = 0.0
        print("[find me] animation complete, brightness restored")

    if frame_t < find_mode_until:
        t = frame_t - find_mode_started_at
        # Build a synthetic command dict to invoke the renderer
        find_state = renderer.for_command({"kind": "find_me"})
        if find_state is not None:
            find_state["render"](zones, t)
    elif frame_t < solo_indicator_until:
        # Solo enter (white burst) or exit (cool blue pulse). Sized
        # to read clearly on camera for B-roll of the toggle moment.
        t = frame_t - solo_indicator_started_at
        if solo_indicator_kind == "enter":
            _render_solo_enter(zones, t)
        else:
            _render_solo_exit(zones, t)
    elif frame_t < brightness_flash_until:
        flash_t = _BRIGHTNESS_FLASH_DURATION_S - (brightness_flash_until - frame_t)
        frac = flash_t / _BRIGHTNESS_FLASH_DURATION_S
        if frac < 0.15:
            envelope = frac / 0.15
        elif frac < 0.65:
            envelope = 1.0
        else:
            envelope = max(0.0, (1.0 - frac) / 0.35)
        count = brightness_flash_level + 1
        lit = (int(255 * envelope),) * 3
        for zone in zones:
            zone.set_led(0, (0, 0, 0))
            for i in range(1, zone.count):
                ring_idx = i - 1
                if ring_idx < count:
                    zone.set_led(i, lit)
                else:
                    zone.set_led(i, (0, 0, 0))
    elif frame_t < unavailable_flash_until:
        # Brief yellow center pulse - "plug in to check battery"
        # Yellow uses both R and G channels heavily, which keeps it
        # readable even if WS2812 timing corrupts on battery.
        flash_t = frame_t - unavailable_flash_started_at
        frac = flash_t / _UNAVAILABLE_FLASH_DURATION_S
        # Triangle envelope: ramp up first half, ramp down second
        envelope = (frac * 2) if frac < 0.5 else max(0.0, 2 * (1 - frac))
        c = _UNAVAILABLE_FLASH_COLOR
        color = (int(c[0] * envelope),
                 int(c[1] * envelope),
                 int(c[2] * envelope))
        for zone in zones:
            zone.set_led(0, color)
            for i in range(1, zone.count):
                zone.set_led(i, (0, 0, 0))
    elif frame_t < battery_display_until:
        t = frame_t - battery_display_started_at
        _render_battery_display(zones, battery_display_voltage, t)
    elif active_state is not None:
        t = frame_t - active_started_at
        try:
            active_state["render"](zones, t)
        except Exception as err:  # pylint: disable=broad-except
            print(f"RENDER ERROR at t={t:.2f}s: "
                  f"{type(err).__name__}: {err}")
            active_state = None
            renderer.render_idle(zones)
    elif solo_mode:
        # Cycle through curated showpieces. A real BLE packet sets
        # active_state above this branch and preempts solo cleanly;
        # solo resumes (with a fresh pick) once the BLE animation
        # ends, so park interaction works without manual toggling.
        if solo_state is None:
            solo_idx = _pick_showpiece_idx(solo_idx)
            solo_label, parsed = _SHOWPIECES[solo_idx]
            solo_state = renderer.for_command(parsed)
            solo_started_at = frame_t
            print(f"[solo] now playing: {solo_label}")
        duration = solo_state["duration_s"] or _SOLO_DEFAULT_DURATION_S
        t = frame_t - solo_started_at
        if t >= duration + _SOLO_BREATH_S:
            # Showpiece + breath gap done; clear so next frame picks.
            solo_state = None
            renderer.render_idle(zones)
        elif t >= duration:
            # In the breath gap between showpieces.
            renderer.render_idle(zones)
        else:
            try:
                solo_state["render"](zones, t)
            except Exception as err:  # pylint: disable=broad-except
                print(f"SOLO RENDER ERROR ({solo_label}) at "
                      f"t={t:.2f}s: {type(err).__name__}: {err}")
                solo_state = None
                renderer.render_idle(zones)
    else:
        renderer.render_idle(zones)
    pixels.show()

    elapsed = time.monotonic() - frame_start
    remaining = _FRAME_BUDGET_S - elapsed
    if remaining > 0:
        time.sleep(remaining)
