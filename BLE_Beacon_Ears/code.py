# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''MagicBand+ Beacon Ears main loop.

Scans for Disney BLE adverts and renders matching commands on stereo
NeoPixel Jewels. Two logical zones (left ear, right ear) are rendered
with stereo phase offsets to give static colors a gentle out-of-phase
breathing animation and rotations a left-leads-right sweep.

To switch from real Jewels to onboard NeoPixel for testing without the
ear hardware, flip _USE_ONBOARD to True below.
'''
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

# Flip this to True to test on the QT Py's onboard pixel without jewels.
_USE_ONBOARD = False

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
_LONG_PRESS_S = 0.5
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
_BUTTON_SHORT_MS = 350
_BUTTON_LONG_MS = int(_LONG_PRESS_S * 1000)


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
_REMOTE_BATTERY_PACKET = bytes.fromhex("aa4201")
_REMOTE_BRIGHTNESS_PACKET = bytes.fromhex("aa4203")
_REMOTE_FIND_PACKET = bytes.fromhex("aa4204")
_REMOTE_STATUE_PACKET = bytes.fromhex("aa4205")


def _is_remote_battery_trigger(payload):
    return bytes(payload[:3]) == _REMOTE_BATTERY_PACKET


def _is_remote_brightness_trigger(payload):
    return bytes(payload[:3]) == _REMOTE_BRIGHTNESS_PACKET


def _is_remote_find_trigger(payload):
    return bytes(payload[:3]) == _REMOTE_FIND_PACKET


def _is_remote_statue_trigger(payload):
    return bytes(payload[:3]) == _REMOTE_STATUE_PACKET


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



class _RuntimeState:
    '''All mutable state for the receiver main loop in one object.

    Bundling state into a single object keeps main() under the lint limit
    for local variables and makes the per-frame helpers cleanly testable.
    Plain data holder, no methods, like a struct.
    '''
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        # Active rendered animation
        self.active_state = None
        self.active_started_at = 0.0
        # Dedup tracking for incoming BLE packets
        self.last_payload = None
        self.last_payload_at = 0.0
        # Brightness flash UI feedback
        self.brightness_flash_until = 0.0
        self.brightness_flash_level = 0
        self.brightness_idx = [0]  # list-wrapped for mutation reasons
        # Trigger cooldowns to suppress repeated remote commands
        self.last_trigger_time = 0.0
        self.last_statue_trigger = 0.0
        # On-demand battery display state
        self.battery_display_until = 0.0
        self.battery_display_started_at = 0.0
        self.battery_display_voltage = None
        # Yellow "plug in" flash (battery display unavailable)
        self.unavailable_flash_until = 0.0
        self.unavailable_flash_started_at = 0.0
        # Find Me beacon mode
        self.find_mode_until = 0.0
        self.find_mode_started_at = 0.0
        # Periodic battery voltage logging
        self.last_battery_log = 0.0
        # Solo mode (curated showpiece reel)
        self.solo_mode = False
        self.solo_state = None
        self.solo_label = ""
        self.solo_idx = -1
        self.solo_started_at = 0.0
        self.solo_indicator_until = 0.0
        self.solo_indicator_started_at = 0.0
        self.solo_indicator_kind = None  # 'enter' or 'exit'


_BATTERY_LOG_INTERVAL_S = 60.0  # log raw voltage once per minute


def _handle_button(state, button, batt, pixels):
    '''Process one tick of BOOT-button input.

    Single-press: brightness cycle. Double-press (in solo): skip
    showpiece. Triple-press: toggle solo mode. Long-press: battery.
    '''
    button.update()
    if button.long_press:
        batt.update(force=True)
        state.battery_display_voltage = batt.voltage
        v_str = (f"{state.battery_display_voltage:.3f}V"
                 if state.battery_display_voltage is not None else "None")
        now = time.monotonic()
        if (state.battery_display_voltage is not None
                and state.battery_display_voltage > _USB_PRESENT_V_RAW):
            print(f"[battery trigger BOOT] {v_str} (USB - showing display)")
            state.battery_display_until = now + _BATTERY_DISPLAY_DURATION_S
            state.battery_display_started_at = now
        else:
            print(f"[battery trigger BOOT] {v_str} (battery - yellow flash)")
            state.unavailable_flash_until = now + _UNAVAILABLE_FLASH_DURATION_S
            state.unavailable_flash_started_at = now
    elif button.short_count >= 3:
        # Triple-press toggles solo mode.
        now = time.monotonic()
        state.solo_indicator_started_at = now
        if state.solo_mode:
            state.solo_mode = False
            state.solo_state = None
            state.solo_indicator_kind = "exit"
            state.solo_indicator_until = now + _SOLO_INDICATOR_EXIT_S
            print("[solo] exiting")
        else:
            state.solo_mode = True
            state.solo_idx = -1
            state.solo_state = None
            state.solo_indicator_kind = "enter"
            state.solo_indicator_until = now + _SOLO_INDICATOR_ENTER_S
            print("[solo] entering")
    elif button.short_count == 2 and state.solo_mode:
        state.solo_state = None
        print("[solo] skipping to next showpiece")
    elif button.short_count == 1:
        state.brightness_idx[0] = (
            (state.brightness_idx[0] + 1) % len(_BRIGHTNESS_PRESETS))
        new_b = _BRIGHTNESS_PRESETS[state.brightness_idx[0]]
        pixels.set_brightness(new_b)
        state.brightness_flash_until = (
            time.monotonic() + _BRIGHTNESS_FLASH_DURATION_S)
        state.brightness_flash_level = state.brightness_idx[0]


def _check_battery_log(state, batt):
    '''Throttled battery voltage logger - one line per minute.'''
    batt.update()
    now = time.monotonic()
    if (batt.voltage is not None
            and now - state.last_battery_log >= _BATTERY_LOG_INTERVAL_S):
        state.last_battery_log = now
        level = _battery_level_match(batt.voltage)
        level_str = f"{level[0]} pixels" if level else "CRITICAL"
        print(f"[battery] raw={batt.voltage:.3f}V -> {level_str}")


def _render_brightness_flash(zones, state, frame_t):
    '''Brightness-cycle confirmation flash on the outer ring.'''
    flash_t = (_BRIGHTNESS_FLASH_DURATION_S
               - (state.brightness_flash_until - frame_t))
    frac = flash_t / _BRIGHTNESS_FLASH_DURATION_S
    if frac < 0.15:
        envelope = frac / 0.15
    elif frac < 0.65:
        envelope = 1.0
    else:
        envelope = max(0.0, (1.0 - frac) / 0.35)
    count = state.brightness_flash_level + 1
    lit = (int(255 * envelope),) * 3
    for zone in zones:
        zone.set_led(0, (0, 0, 0))
        for i in range(1, zone.count):
            zone.set_led(i, lit if (i - 1) < count else (0, 0, 0))


def _render_unavailable_flash(zones, state, frame_t):
    '''Yellow center pulse - "plug in to check battery".'''
    flash_t = frame_t - state.unavailable_flash_started_at
    frac = flash_t / _UNAVAILABLE_FLASH_DURATION_S
    envelope = (frac * 2) if frac < 0.5 else max(0.0, 2 * (1 - frac))
    color = (int(_UNAVAILABLE_FLASH_COLOR[0] * envelope),
             int(_UNAVAILABLE_FLASH_COLOR[1] * envelope),
             int(_UNAVAILABLE_FLASH_COLOR[2] * envelope))
    for zone in zones:
        zone.set_led(0, color)
        for i in range(1, zone.count):
            zone.set_led(i, (0, 0, 0))


def _render_active_state(zones, state, frame_t):
    '''Render the currently active animation, with crash safety.'''
    t = frame_t - state.active_started_at
    try:
        state.active_state["render"](zones, t)
    except Exception as err:  # pylint: disable=broad-except
        print(f"RENDER ERROR at t={t:.2f}s: "
              f"{type(err).__name__}: {err}")
        state.active_state = None
        renderer.render_idle(zones)


def _render_solo_cycle(zones, state, frame_t):
    '''Render one frame of solo mode\'s curated showpiece reel.'''
    if state.solo_state is None:
        state.solo_idx = _pick_showpiece_idx(state.solo_idx)
        state.solo_label, parsed = _SHOWPIECES[state.solo_idx]
        state.solo_state = renderer.for_command(parsed)
        state.solo_started_at = frame_t
        print(f"[solo] now playing: {state.solo_label}")
    duration = state.solo_state["duration_s"] or _SOLO_DEFAULT_DURATION_S
    t = frame_t - state.solo_started_at
    if t >= duration + _SOLO_BREATH_S:
        state.solo_state = None
        renderer.render_idle(zones)
    elif t >= duration:
        renderer.render_idle(zones)
    else:
        try:
            state.solo_state["render"](zones, t)
        except Exception as err:  # pylint: disable=broad-except
            print(f"SOLO RENDER ERROR ({state.solo_label}) at "
                  f"t={t:.2f}s: {type(err).__name__}: {err}")
            state.solo_state = None
            renderer.render_idle(zones)


def _render_frame(zones, state, pixels):
    '''Render one frame, picking the highest-priority active source.'''
    frame_t = time.monotonic()
    if 0.0 < state.find_mode_until <= frame_t:
        pixels.set_brightness(_BRIGHTNESS_PRESETS[state.brightness_idx[0]])
        state.find_mode_until = 0.0
        print("[find me] animation complete, brightness restored")

    if frame_t < state.find_mode_until:
        t = frame_t - state.find_mode_started_at
        find_state = renderer.for_command({"kind": "find_me"})
        if find_state is not None:
            find_state["render"](zones, t)
    elif frame_t < state.solo_indicator_until:
        t = frame_t - state.solo_indicator_started_at
        if state.solo_indicator_kind == "enter":
            _render_solo_enter(zones, t)
        else:
            _render_solo_exit(zones, t)
    elif frame_t < state.brightness_flash_until:
        _render_brightness_flash(zones, state, frame_t)
    elif frame_t < state.unavailable_flash_until:
        _render_unavailable_flash(zones, state, frame_t)
    elif frame_t < state.battery_display_until:
        t = frame_t - state.battery_display_started_at
        _render_battery_display(zones, state.battery_display_voltage, t)
    elif state.active_state is not None:
        _render_active_state(zones, state, frame_t)
    elif state.solo_mode:
        _render_solo_cycle(zones, state, frame_t)
    else:
        renderer.render_idle(zones)


def main():
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    '''Receiver main loop. See README "code.py size constraint" for
    why the lint disables above are required - exceeding ~32.5KB
    breaks _bleio init on QT Py S3 with CP 10.1.4 (bisected).
    '''
    print("MagicBand+ BLE Beacon Ears")
    print(f"Rendering on {'onboard NeoPixel' if _USE_ONBOARD else 'stereo Jewels'}")
    print(f"BLE scan: window={_SCAN_WINDOW_S * 1000:.0f}ms"
          f"  interval={_SCAN_INTERVAL_S * 1000:.0f}ms")
    print("-" * 60)

    if _USE_ONBOARD:
        pixels = pixel_zones.OnboardSingle(brightness=0.2)
    else:
        pixels = pixel_zones.StereoJewels(
            left_pin=board.A1, right_pin=board.A3,
            brightness=_BRIGHTNESS_PRESETS[0])
    zones = pixels.make_zones()

    adapter = _bleio.adapter
    if not adapter.enabled:
        adapter.enabled = True

    batt = battery_mod.BatteryMonitor()

    button_pin = digitalio.DigitalInOut(board.BUTTON)
    button_pin.switch_to_input(pull=digitalio.Pull.UP)
    button = Button(button_pin, value_when_pressed=False,
                    short_duration_ms=_BUTTON_SHORT_MS,
                    long_duration_ms=_BUTTON_LONG_MS)

    state = _RuntimeState()

    while True:
        frame_start = time.monotonic()

        # --- BLE scan (still inline; Stages E and F will refactor) ---
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
                if _is_remote_brightness_trigger(payload):
                    now = time.monotonic()
                    if now - state.last_trigger_time < _TRIGGER_COOLDOWN_S:
                        continue
                    state.last_trigger_time = now
                    state.brightness_idx[0] = (
                        (state.brightness_idx[0] + 1) % len(_BRIGHTNESS_PRESETS))
                    new_b = _BRIGHTNESS_PRESETS[state.brightness_idx[0]]
                    pixels.set_brightness(new_b)
                    state.brightness_flash_until = now + _BRIGHTNESS_FLASH_DURATION_S
                    state.brightness_flash_level = state.brightness_idx[0]
                    continue
                if _is_remote_battery_trigger(payload):
                    now = time.monotonic()
                    if now - state.last_trigger_time < _TRIGGER_COOLDOWN_S:
                        continue
                    state.last_trigger_time = now
                    batt.update(force=True)
                    state.battery_display_voltage = batt.voltage
                    v_str = (f"{state.battery_display_voltage:.3f}V"
                             if state.battery_display_voltage is not None else "None")
                    if (state.battery_display_voltage is not None
                            and state.battery_display_voltage > _USB_PRESENT_V_RAW):
                        print(f"[battery trigger remote] {v_str} (USB - showing display)")
                        state.battery_display_until = now + _BATTERY_DISPLAY_DURATION_S
                        state.battery_display_started_at = now
                    else:
                        print(f"[battery trigger remote] {v_str} (battery - yellow flash)")
                        state.unavailable_flash_until = now + _UNAVAILABLE_FLASH_DURATION_S
                        state.unavailable_flash_started_at = now
                    continue
                if _is_remote_find_trigger(payload):
                    now = time.monotonic()
                    if now - state.last_trigger_time < _TRIGGER_COOLDOWN_S:
                        continue
                    state.last_trigger_time = now
                    print("[find me] starting high-visibility animation")
                    pixels.set_brightness(1.0)
                    state.find_mode_until = now + renderer.FIND_MODE_DURATION_S
                    state.find_mode_started_at = now
                    continue
                if _is_remote_statue_trigger(payload):
                    now = time.monotonic()
                    if now - state.last_trigger_time < _TRIGGER_COOLDOWN_S:
                        continue
                    state.last_trigger_time = now
                    print("[statue preview] firing golden swirl")
                    fake_statue_cmd = {
                        "kind": "statue_beacon",
                        "statue_id": "PV",
                        "raw": bytes(payload),
                    }
                    candidate = renderer.for_command(fake_statue_cmd)
                    if candidate is not None:
                        new_command = (candidate, entry.rssi, bytes(payload))
                    continue
                is_mb = payload[0] in (0xE1, 0xE2, 0xCC)
                is_wand = magicband_protocol.is_wand_packet(payload)
                is_statue = (payload[0] == 0xC4 and len(payload) in (18, 23))
                if not (is_mb or is_wand or is_statue):
                    continue
                now = time.monotonic()
                if is_statue:
                    if now - state.last_statue_trigger < _STATUE_COOLDOWN_S:
                        continue
                    state.last_statue_trigger = now
                else:
                    if (payload == state.last_payload
                            and now - state.last_payload_at < _DEDUP_WINDOW_S):
                        continue
                    state.last_payload = payload
                    state.last_payload_at = now
                parsed = magicband_protocol.parse(payload)
                candidate = renderer.for_command(parsed)
                if candidate is not None:
                    new_command = (candidate, entry.rssi, payload)
        finally:
            adapter.stop_scan()

        # --- Helpers extracted in Stage D ---
        _handle_button(state, button, batt, pixels)

        if new_command is not None:
            state.active_state, rssi, raw = new_command
            state.active_started_at = time.monotonic()
            _log_command(state.active_state["label"], rssi, raw)

        if state.active_state is not None:
            duration = state.active_state["duration_s"]
            if duration is not None:
                if time.monotonic() - state.active_started_at >= duration:
                    state.active_state = None

        _check_battery_log(state, batt)
        _render_frame(zones, state, pixels)
        pixels.show()

        elapsed = time.monotonic() - frame_start
        remaining = _FRAME_BUDGET_S - elapsed
        if remaining > 0:
            time.sleep(remaining)


main()
