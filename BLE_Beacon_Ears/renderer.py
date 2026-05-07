# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''Animation renderer for MagicBand+ commands.

Given a parsed command dict from magicband_protocol, produces an
AnimationState that the game loop can render over time. The state is a
small dict holding:
    started_at (seconds)         - time.monotonic() when command received
    duration_s (float or None)   - how long until animation stops; None = forever
    render(zones, t)             - callback that paints a frame at time t

Design rules:
  - Renderer NEVER blocks. All timing is derived from t (time since start).
  - All palette colors are looked up via magicband_protocol.PALETTE_RGB.
  - Stereo effects are applied at render time via per-zone phase offset.
  - When no active animation exists, zones are filled black.
'''
# Target: Adafruit QT Py ESP32-S3 - the BLE Beacon Ears
import math

import magicband_protocol

# Breathing envelope - applied to static colors to add life.
# Amplitude 0.45 means brightness oscillates between 55% and 100% of target.
# This is more pronounced than a subtle 25% amplitude would be - on 7-pixel
# jewels with full color, you need more contrast to read as "breathing."
_BREATH_PERIOD_S = 2.5
_BREATH_AMPLITUDE = 0.45

# Rotation period for animations without explicit timing cues.
_ROTATE_PERIOD_S = 2.0

# Default duration when a command has no parseable timing byte.
_DEFAULT_DURATION_S = 10.0

# Cross-fade period for dual-color alternation on pixel prototype.
_DUAL_ALTERNATE_PERIOD_S = 1.2


def _scale_rgb(rgb, factor):
    '''Multiply each channel by factor (0.0-1.0) and clamp.'''
    return (
        min(255, max(0, int(rgb[0] * factor))),
        min(255, max(0, int(rgb[1] * factor))),
        min(255, max(0, int(rgb[2] * factor))),
    )


def _breath_factor(t, phase=0.0):
    '''Return 0..1 brightness multiplier that breathes gently over time.'''
    # Sinusoid, output range (1 - amp) to 1.0.
    wave = 0.5 + 0.5 * math.sin(
        2 * math.pi * (t / _BREATH_PERIOD_S + phase))
    return (1.0 - _BREATH_AMPLITUDE) + _BREATH_AMPLITUDE * wave


def for_command(command):
    '''Build an AnimationState from a parsed command dict.'''
    kind = command.get("kind", "unknown")
    handler = _COMMAND_HANDLERS.get(kind)
    if handler is None:
        return None
    if kind == "ping":
        return handler()
    return handler(command)


def _state_parade_command(_command):
    '''CD 07 / parade beacon - colors not decoded.

    Newer Disney park show commands (Starlight Parade etc.) use formats
    we haven't reverse-engineered. Rather than ignoring them and being
    silent during the show, render a generic rainbow rotation so the
    ears at least respond visibly. The wearer sees that the show IS
    triggering them, just not in the exact same way as a real band.
    '''
    rainbow_colors = (
        (255, 0, 0),       # red
        (255, 100, 0),     # orange
        (255, 220, 0),     # yellow
        (0, 255, 0),       # green
        (0, 120, 255),     # blue
        (180, 0, 255),     # purple
    )

    def render(zones, t):
        # Smooth rotation over 2 seconds per cycle
        phase = t / 2.0
        n_colors = len(rainbow_colors)
        for zone_idx, zone in enumerate(zones):
            zone_offset = 0.5 if zone_idx == 1 else 0.0
            outer_count = max(1, zone.count - 1)
            # Center pixel cycles slowly
            center_slot = int(phase) % n_colors
            zone.set_led(0, _scale_rgb(rainbow_colors[center_slot], 0.4))
            for led_idx in range(1, zone.count):
                angle_frac = (led_idx - 1) / outer_count
                color_phase = phase + zone_offset + angle_frac
                slot = int(color_phase * n_colors) % n_colors
                zone.set_led(led_idx, rainbow_colors[slot])

    return {"duration_s": 5.0, "render": render, "label": "PARADE"}


def _state_statue_beacon(command):
    '''Fab 50 statue detected - golden swirl with sparkles and pulse.

    Disney's Fab 50 golden statues at Magic Kingdom broadcast continuous
    location beacons. We trigger this animation to acknowledge "the
    statue sees you" when one is detected nearby. The original 2-second
    version felt too brief - now 4.0s with two pulse "beats" so the
    surprise lasts long enough to register.

    Visual: warm gold pixels swirl around the outer ring, with random
    bright white sparkles popping in. Sparkles get easier to trigger
    on pulse peaks. A breathing brightness envelope creates two beats
    over the 4-second span; each beat peaks mid-rotation, so the swirl
    waxes bright at ~1s and ~3s with a softer dip between them.
    '''
    statue_id = command.get("statue_id", "?")
    gold_bright = (255, 180, 30)
    gold_dim = (120, 80, 10)
    sparkle_white = (255, 255, 200)

    def _statue_pixel_for(led_idx, ring_idx, zone_idx, t, phase, envelope, pulse):
        '''Compute the RGB for one outer-ring LED in the statue swirl.'''
        # Sparkle: pseudo-random per LED + time. Threshold gets
        # slightly easier on pulse peaks so sparkles cluster
        # rhythmically with the beat instead of feeling random.
        sparkle_phase = t * 12.0 + led_idx * 1.7 + zone_idx * 0.5
        if math.sin(sparkle_phase) > 0.88 - 0.06 * pulse:
            return _scale_rgb(sparkle_white, envelope)
        zone_offset = phase + (0.3 if zone_idx == 1 else 0.0)
        outer_count = 6
        head_pos = (zone_offset * outer_count) % outer_count
        distance = (head_pos - ring_idx) % outer_count
        if distance < 1.0:
            return _scale_rgb(gold_bright, envelope)
        if distance < 3.0:
            fade = 1.0 - (distance / 3.0)
            return _scale_rgb(gold_dim, envelope * fade)
        return (0, 0, 0)

    def render(zones, t):
        # Outer envelope: 0-0.3s fade in, 3.7-4.0s fade out, flat between.
        if t < 0.3:
            fade_envelope = t / 0.3
        elif t > 3.7:
            fade_envelope = max(0.0, (4.0 - t) / 0.3)
        else:
            fade_envelope = 1.0
        # Two-beat pulse: dim at t=0, peak at t=1, dim at t=2, peak at
        # t=3, dim at t=4. Cosine-shifted sine keeps range tight (0.5..1.0)
        # so the swirl never disappears entirely between peaks.
        pulse = 0.75 + 0.25 * math.sin(
            2 * math.pi * t / 2.0 - math.pi / 2)
        envelope = fade_envelope * pulse
        # Continuous rotation - no reset between beats. ~3 full
        # revolutions over the 4s span at 1.5 rev/s base rate.
        phase = t * 1.5
        for zone_idx, zone in enumerate(zones):
            # Center pixel: steady warm gold modulated by envelope
            zone.set_led(0, (int(gold_bright[0] * envelope * 0.6),
                             int(gold_bright[1] * envelope * 0.6),
                             int(gold_bright[2] * envelope * 0.6)))
            for led_idx in range(1, zone.count):
                zone.set_led(led_idx, _statue_pixel_for(
                    led_idx, led_idx - 1, zone_idx, t, phase,
                    envelope, pulse))

    return {
        "duration_s": 4.0,
        "render": render,
        "label": f"STATUE #{statue_id}",
    }


# Find Me beacon - 3-phase high-visibility animation for locating a
# stroller, wheelchair, or EV scooter in a busy parking lot. Triggered
# by the CLUE remote's "Find Me" command. The main loop also forces
# the pixel brightness to maximum during this animation regardless of
# the user's preset, then restores their preset after.
_FIND_STROBE_S = 3.0       # Phase 1: attention-grabbing strobe
_FIND_CHASE_S = 15.0       # Phase 2: rainbow chase (motion + color)
_FIND_BREATHE_S = 12.0     # Phase 3: rainbow breathing (steady glow)
FIND_MODE_DURATION_S = _FIND_STROBE_S + _FIND_CHASE_S + _FIND_BREATHE_S


def _state_find_me(_command):
    '''3-phase high-visibility "find me" animation.

    Phase 1: Strobe - rapid full-white + saturated color flashes to
        catch eyes from across a parking lot.
    Phase 2: Rainbow chase - bright pixels rotating around the ring with
        rainbow color trail. Easy to spot at distance, indicates motion
        / liveness.
    Phase 3: Rainbow breathing - steady saturated rainbow at slower
        breath rate. Less alarming once located, easy to home in on.
    '''
    # Vivid colors used throughout (full saturation for visibility)
    rainbow = (
        (255, 0, 0),      # red
        (255, 80, 0),     # orange
        (255, 200, 0),    # yellow
        (0, 255, 0),      # green
        (0, 80, 255),     # blue
        (180, 0, 255),    # purple
    )
    white = (255, 255, 255)

    def _phase_strobe(zones, t):
        '''Phase 1: strobe at 5 Hz alternating white and rainbow color.'''
        strobe_idx = int(t * 10)  # 10 strobes/sec
        if strobe_idx % 2 == 0:
            color = white
        else:
            color = rainbow[(strobe_idx // 2) % len(rainbow)]
        for zone in zones:
            zone.fill(color)

    def _phase_chase(zones, phase_t):
        '''Phase 2: rainbow chase rotating around the ring.'''
        rotation = phase_t * 1.5  # ~1.5 revolutions per second
        n = len(rainbow)
        for zone_idx, zone in enumerate(zones):
            zone_offset = rotation + (0.3 if zone_idx == 1 else 0.0)
            zone.set_led(0, rainbow[int(rotation * 0.5) % n])
            outer_count = max(1, zone.count - 1)
            for led_idx in range(1, zone.count):
                angle = (led_idx - 1) / outer_count
                zone.set_led(led_idx,
                             rainbow[int((zone_offset + angle) * n) % n])

    def _phase_breathe(zones, phase_t):
        '''Phase 3: rainbow breathing - all pixels rainbow with envelope.'''
        breath = 0.5 + 0.5 * math.sin(2 * math.pi * phase_t / 2.0)
        n = len(rainbow)
        for zone_idx, zone in enumerate(zones):
            zone_offset = 0.5 if zone_idx == 1 else 0.0
            zone.set_led(0, _scale_rgb(
                rainbow[int(phase_t / 2.0) % n], breath))
            outer_count = max(1, zone.count - 1)
            for led_idx in range(1, zone.count):
                angle = (led_idx - 1) / outer_count
                zone.set_led(led_idx, _scale_rgb(
                    rainbow[int((angle + zone_offset) * n) % n], breath))

    def render(zones, t):
        if t < _FIND_STROBE_S:
            _phase_strobe(zones, t)
        elif t < _FIND_STROBE_S + _FIND_CHASE_S:
            _phase_chase(zones, t - _FIND_STROBE_S)
        else:
            _phase_breathe(zones, t - _FIND_STROBE_S - _FIND_CHASE_S)

    return {
        "duration_s": FIND_MODE_DURATION_S,
        "render": render,
        "label": "FIND ME",
    }


def _lighten(rgb, amount=0.4):
    '''Return rgb shifted toward white by `amount` (0.0-1.0).'''
    return (
        min(255, int(rgb[0] + (255 - rgb[0]) * amount)),
        min(255, int(rgb[1] + (255 - rgb[1]) * amount)),
        min(255, int(rgb[2] + (255 - rgb[2]) * amount)),
    )


def _state_wand_cast(command):
    '''Starlight Wand cast - a multi-phase comet animation.

    Narrative:
      1. Comet swirls on the LEFT ear twice (outer ring), tail fading behind.
      2. Comet "crosses over" briefly (both ears show a quick trail).
      3. Comet swirls on the RIGHT ear twice.
      4. Both ears sparkle with a lighter shade of the cast color.
      5. Both ears settle into a slow breathing glow of the cast color,
         holding for 30 seconds or until the next command arrives.

    Each outer-ring pixel on a 7-pixel Jewel is indexed 1..6 with pixel 0
    being the center. The comet moves around the 6 outer pixels; the
    center pixel glows at a modest fraction to anchor the swirl.
    '''
    palette_idx = command["palette_idx"]
    rgb = magicband_protocol.PALETTE_RGB[palette_idx]
    sparkle_rgb = _lighten(rgb, 0.55)
    name = magicband_protocol.PALETTE_NAMES[palette_idx]

    # Phase timings (seconds from t=0): swirl_left_end, crossover_end,
    # swirl_right_end, sparkle_end, total_duration.
    timings = (0.9, 1.1, 2.0, 2.8, 30.0)
    # Comet shape: outer_count, tail_len, tail_falloff (per-step dimming).
    comet_shape = (6, 4, 0.55)

    def _comet_on_zone(zone, head_position, color_bright):
        '''Draw a comet with tail on the outer ring of one zone.

        head_position is a float 0..outer_count-1 indicating where the
        comet "head" sits on the ring. Tail trails behind it at decreasing
        brightness. Center pixel (idx 0) anchors at a modest glow.
        '''
        outer_count, tail_len, tail_falloff = comet_shape
        # Fade the center so it's subtle but present
        zone.set_led(0, _scale_rgb(color_bright, 0.3))
        # Tail effect - for each outer ring pixel, compute its distance
        # back from the head and set brightness accordingly.
        head_int = int(head_position) % outer_count
        for ring_idx in range(outer_count):
            led_idx = ring_idx + 1  # skip center
            # Distance back from head (always positive, wrapping around)
            distance = (head_int - ring_idx) % outer_count
            if distance > tail_len:
                zone.set_led(led_idx, (0, 0, 0))
            elif distance == 0:
                # Bright head
                zone.set_led(led_idx, color_bright)
            else:
                factor = tail_falloff ** distance
                zone.set_led(led_idx, _scale_rgb(color_bright, factor))

    def _dark_zone(zone):
        for i in range(zone.count):
            zone.set_led(i, (0, 0, 0))

    def render(zones, t):
        left, right = zones[0], zones[1]
        swirl_left_end, crossover_end, swirl_right_end, sparkle_end, _ = timings
        outer_count = comet_shape[0]

        if t < swirl_left_end:
            _wand_phase_left(left, right, t, swirl_left_end,
                             outer_count, rgb, _comet_on_zone, _dark_zone)
        elif t < crossover_end:
            _wand_phase_crossover(left, right, t, swirl_left_end,
                                  crossover_end, outer_count, rgb,
                                  _comet_on_zone)
        elif t < swirl_right_end:
            _wand_phase_right(left, right, t, crossover_end,
                              swirl_right_end, outer_count, rgb,
                              _comet_on_zone, _dark_zone)
        elif t < sparkle_end:
            _wand_phase_sparkle(zones, t, rgb, sparkle_rgb)
        else:
            _wand_phase_breathe(left, right, t - sparkle_end, rgb)

    return {
        "duration_s": timings[4],
        "render": render,
        "label": f"WAND {name}",
    }


def _wand_phase_left(left, right, t, swirl_left_end, outer_count,
                     rgb, comet_fn, dark_fn):
    '''Phase 1: left ear comet, 2 full swirls. Right ear dark.'''
    progress = t / swirl_left_end
    comet_fn(left, progress * outer_count * 2, rgb)
    dark_fn(right)


def _wand_phase_crossover(left, right, t, swirl_left_end, crossover_end,
                          outer_count, rgb, comet_fn):
    '''Phase 2: crossover - left fades, right starts.'''
    fade_progress = (t - swirl_left_end) / (crossover_end - swirl_left_end)
    comet_fn(left, outer_count * 2 - 1,
             _scale_rgb(rgb, 1.0 - fade_progress))
    comet_fn(right, 0, _scale_rgb(rgb, fade_progress))


def _wand_phase_right(left, right, t, crossover_end, swirl_right_end,
                      outer_count, rgb, comet_fn, dark_fn):
    '''Phase 3: right ear comet, 2 full swirls. Left ear dark.'''
    progress = (t - crossover_end) / (swirl_right_end - crossover_end)
    dark_fn(left)
    comet_fn(right, progress * outer_count * 2, rgb)


def _wand_phase_sparkle(zones, t, rgb, sparkle_rgb):
    '''Phase 4: sparkle burst - both ears scatter light shimmers.'''
    for zone_idx, zone in enumerate(zones):
        for led_idx in range(zone.count):
            phase = t * 22.0 + led_idx * 1.3 + zone_idx * 0.7
            twinkle = abs(math.sin(phase * 2 * math.pi))
            if twinkle > 0.75:
                zone.set_led(led_idx, sparkle_rgb)
            elif twinkle > 0.4:
                zone.set_led(led_idx, _scale_rgb(rgb, twinkle))
            else:
                zone.set_led(led_idx, _scale_rgb(rgb, 0.2))


def _wand_phase_breathe(left, right, t_breath, rgb):
    '''Phase 5: settled breathing - slow, gentle pulse on both ears.'''
    # 4-second period, 30% amplitude (between 70% and 100%). Right ear
    # is offset by half a cycle so the two ears breathe out of phase.
    left_f = 0.85 + 0.15 * math.sin(2 * math.pi * t_breath / 4.0)
    right_f = 0.85 + 0.15 * math.sin(
        2 * math.pi * (t_breath / 4.0 + 0.5))
    left.fill(_scale_rgb(rgb, left_f))
    right.fill(_scale_rgb(rgb, right_f))


def _state_ping():
    # Wake-ping packets (CC03) are fired by the CLUE remote right before
    # commands flagged needs_ping=True. They're a meta-signal meant for
    # the band receiver, not something the ears should visualize. Return
    # None so the game loop ignores it entirely.
    return None


def _state_single_color(command):
    palette = command["palette_idx"]
    rgb = magicband_protocol.PALETTE_RGB[palette]
    name = magicband_protocol.PALETTE_NAMES[palette]
    duration = None if command["timing"]["always_on"] else command["timing"]["seconds"]

    def render(zones, t):
        # Stereo breathing: left and right out of phase by half a cycle.
        left_rgb = _scale_rgb(rgb, _breath_factor(t, phase=0.0))
        right_rgb = _scale_rgb(rgb, _breath_factor(t, phase=0.5))
        zones[0].fill(left_rgb)
        zones[1].fill(right_rgb)

    return {
        "duration_s": duration,
        "render": render,
        "label": f"SINGLE {name}",
    }


def _state_dual_color(command):
    inner = magicband_protocol.PALETTE_RGB[command["inner_idx"]]
    outer = magicband_protocol.PALETTE_RGB[command["outer_idx"]]
    inner_name = magicband_protocol.PALETTE_NAMES[command["inner_idx"]]
    outer_name = magicband_protocol.PALETTE_NAMES[command["outer_idx"]]
    duration = None if command["timing"]["always_on"] else command["timing"]["seconds"]

    def render(zones, t):
        # Stereo assignment: left = inner, right = outer. Each still breathes
        # to stay lively. Out-of-phase breathing keeps the two ears feeling
        # alive rather than identical.
        zones[0].fill(_scale_rgb(inner, _breath_factor(t, phase=0.0)))
        zones[1].fill(_scale_rgb(outer, _breath_factor(t, phase=0.5)))

    return {
        "duration_s": duration,
        "render": render,
        "label": f"DUAL {inner_name}/{outer_name}",
    }


def _state_five_color(command):
    # Each of the 5 band LEDs has its own palette slot. We pick a
    # representative color per zone: left zone uses top-left + bottom-left,
    # right zone uses top-right + bottom-right, each zone's center lights up
    # the average. For single-pixel prototype we flatten further.
    tl = magicband_protocol.PALETTE_RGB[command["top_left"]]
    bl = magicband_protocol.PALETTE_RGB[command["bottom_left"]]
    tr = magicband_protocol.PALETTE_RGB[command["top_right"]]
    br = magicband_protocol.PALETTE_RGB[command["bottom_right"]]
    center = magicband_protocol.PALETTE_RGB[command["center"]]
    duration = (None if command["timing"]["always_on"]
                else command["timing"]["seconds"])

    def _avg(a, b, c):
        return ((a[0] + b[0] + c[0]) // 3,
                (a[1] + b[1] + c[1]) // 3,
                (a[2] + b[2] + c[2]) // 3)

    left_rgb = _avg(tl, bl, center)
    right_rgb = _avg(tr, br, center)

    def render(zones, t):
        zones[0].fill(_scale_rgb(left_rgb, _breath_factor(t, phase=0.0)))
        zones[1].fill(_scale_rgb(right_rgb, _breath_factor(t, phase=0.5)))

    return {"duration_s": duration, "render": render, "label": "FIVE"}


def _state_six_bit(command):
    # E9 08 gives raw 6-bit RGB. Expand to 8-bit and use it directly.
    rgb = (command["red"] << 2, command["green"] << 2, command["blue"] << 2)
    duration = (None if command["timing"]["always_on"]
                else command["timing"]["seconds"])

    def render(zones, t):
        zones[0].fill(_scale_rgb(rgb, _breath_factor(t, phase=0.0)))
        zones[1].fill(_scale_rgb(rgb, _breath_factor(t, phase=0.5)))

    return {"duration_s": duration, "render": render, "label": "RGB6"}


# Firmware-baked E9 0C animations. These have known payload signatures
# whose bytes are NOT raw 5-slot palette indices but rather animation
# program selectors. We map them to approximate visual color sequences
# matching how real MagicBand+ hardware actually plays them.
#
# Key: first 12 bytes of payload (signature prefix, excludes timing/vib/vib)
# Value: (label, ordered color RGB list)
_BAKED_ANIMATIONS = {
    # Taste the Rainbow - full rainbow rotation
    bytes.fromhex("e100e90c000f0f5d465bf005"): (
        "Rainbow",
        [
            (255, 0, 0),        # red
            (255, 90, 0),       # orange
            (255, 220, 0),      # yellow
            (0, 255, 0),        # green
            (0, 120, 255),      # blue
            (180, 0, 255),      # purple
        ],
    ),
    # Blink White - white strobe
    bytes.fromhex("e100e90c000f0f5d465bf005"): (
        "Blink White",
        [(255, 220, 200), (0, 0, 0)],
    ),
    # Orange Blink - orange pulse
    bytes.fromhex("e100e90c00ef0f4f4f5bf0fb"): (
        "Orange Blink",
        [(255, 90, 0), (50, 20, 0)],
    ),
}


def _lookup_baked_animation(raw):
    '''Return (label, slots) if raw matches a known firmware animation.'''
    # Taste the Rainbow and Blink White share the same 12-byte prefix but
    # differ in tail bytes. Disambiguate by comparing tail too.
    prefix = bytes(raw[:12])
    tail = bytes(raw[12:]) if len(raw) > 12 else b""

    # Taste the Rainbow full: e100e90c000f0f5d465bf005 32 37 48 b0
    # Blink White full:       e100e90c000f0f5d465bf005 32 37 48 95
    # Distinguished by last byte: b0=no vibration (TTR), 95=other (Blink White)
    if prefix == bytes.fromhex("e100e90c000f0f5d465bf005"):
        if len(tail) >= 4 and tail[-1] == 0x95:
            return ("Blink White",
                    [(255, 220, 200), (0, 0, 0)])
        # Default this prefix to Taste the Rainbow
        return ("Rainbow",
                [(255, 0, 0), (255, 90, 0), (255, 220, 0),
                 (0, 255, 0), (0, 120, 255), (180, 0, 255)])

    # Orange Blink
    if prefix == bytes.fromhex("e100e90c00ef0f4f4f5bf0fb"):
        return ("Orange Blink",
                [(255, 90, 0), (50, 20, 0)])

    return None


def _decode_5slot_palette(raw):
    '''Decode bytes 7..11 of a 5-slot E9 0C payload into colors and label.

    Returns (slots, label) where slots is a list of RGB tuples and label
    is a short summary of the distinct color names involved.
    '''
    slot_bytes = raw[7:12] if len(raw) >= 12 else raw[7:]
    slots = []
    slot_names = []
    for byte in slot_bytes:
        idx = byte & 0x1F
        slots.append(magicband_protocol.PALETTE_RGB[idx])
        slot_names.append(magicband_protocol.PALETTE_NAMES[idx])
    if not slots:
        slots = [(255, 255, 255)]
        slot_names = ["White"]
    distinct = []
    for name in slot_names:
        short = name.split()[0][:4]
        if not distinct or distinct[-1] != short:
            distinct.append(short)
    return slots, f"SHOW {'>'.join(distinct)}"


def _state_show_fx(command):
    '''E9 0C captured park animations.

    Some E9 0C payloads are firmware-baked animation programs (Taste the
    Rainbow, Blink White, Orange Blink) where the bytes are program IDs,
    not 5-slot palettes. We recognize those by signature and use hardcoded
    color sequences matching their real visual appearance.

    Other E9 0C payloads (5 Palette Cycle, DCL Rainbow, future clones) are
    true 5-slot palette cycles - for those we extract colors from bytes
    7-11 as palette indices.
    '''
    raw = command["raw"]
    baked = _lookup_baked_animation(raw)
    if baked is not None:
        label_suffix, slots = baked
        label = f"SHOW {label_suffix}"
    else:
        slots, label = _decode_5slot_palette(raw)

    duration = _DEFAULT_DURATION_S
    if len(raw) >= 6:
        timing = magicband_protocol.decode_timing(raw[5])
        duration = None if timing["always_on"] else timing["seconds"]

    def render(zones, t):
        n_slots = len(slots)
        phase = t / _ROTATE_PERIOD_S
        for zone_idx, zone in enumerate(zones):
            zone_offset = 0.5 if zone_idx == 1 else 0.0
            center_slot = int(phase) % n_slots
            zone.set_led(0, slots[center_slot])
            outer_count = max(1, zone.count - 1)
            for led_idx in range(1, zone.count):
                angle_frac = (led_idx - 1) / outer_count
                color_phase = phase + zone_offset + angle_frac
                slot = int(color_phase * n_slots) % n_slots
                zone.set_led(led_idx, slots[slot])

    return {"duration_s": duration, "render": render, "label": label}


def _state_cross_fade(command):
    # E9 11 cross fade between two palette colors. The two endpoint colors
    # are encoded in bytes 7 (from) and 8 (to) of the payload. Bytes 9+
    # appear to be fade timing and repeat parameters, not additional color
    # slots.
    raw = command["raw"]
    slot_a_idx = (raw[7] if len(raw) > 7 else 0) & 0x1F
    slot_b_idx = (raw[8] if len(raw) > 8 else 0) & 0x1F
    slot_a = magicband_protocol.PALETTE_RGB[slot_a_idx]
    slot_b = magicband_protocol.PALETTE_RGB[slot_b_idx]
    name_a = magicband_protocol.PALETTE_NAMES[slot_a_idx]
    name_b = magicband_protocol.PALETTE_NAMES[slot_b_idx]
    duration = _DEFAULT_DURATION_S * 2
    if len(raw) >= 6:
        timing = magicband_protocol.decode_timing(raw[5])
        duration = None if timing["always_on"] else timing["seconds"]

    def _mix(a, b, f):
        return (
            int(a[0] * (1 - f) + b[0] * f),
            int(a[1] * (1 - f) + b[1] * f),
            int(a[2] * (1 - f) + b[2] * f),
        )

    def render(zones, t):
        # Slow sinusoidal cross fade between a and b. Left leads right.
        f_left = 0.5 + 0.5 * math.sin(2 * math.pi * t / 4.0)
        f_right = 0.5 + 0.5 * math.sin(2 * math.pi * (t - 1.0) / 4.0)
        zones[0].fill(_mix(slot_a, slot_b, f_left))
        zones[1].fill(_mix(slot_a, slot_b, f_right))

    return {
        "duration_s": duration,
        "render": render,
        "label": f"FADE {name_a}<>{name_b}",
    }


def _show_command_slots_path(slots):
    '''5-slot palette path for show_command. Returns a state dict.'''
    slot_colors = [magicband_protocol.PALETTE_RGB[i] for i in slots]
    slot_names = [magicband_protocol.PALETTE_NAMES[i] for i in slots]
    distinct = []
    for name in slot_names:
        short = name.split()[0][:4]
        if not distinct or distinct[-1] != short:
            distinct.append(short)
    full_label = f"SHOW5 {'>'.join(distinct)}"

    def render_slots(zones, t):
        n_slots = len(slot_colors)
        phase = t / _ROTATE_PERIOD_S
        for zone_idx, zone in enumerate(zones):
            zone_offset = 0.5 if zone_idx == 1 else 0.0
            zone.set_led(0, slot_colors[int(phase) % n_slots])
            outer_count = max(1, zone.count - 1)
            for led_idx in range(1, zone.count):
                angle_frac = (led_idx - 1) / outer_count
                color_phase = phase + zone_offset + angle_frac
                zone.set_led(led_idx,
                             slot_colors[int(color_phase * n_slots) % n_slots])

    return {"duration_s": _DEFAULT_DURATION_S, "render": render_slots,
            "label": full_label}


def _show_command_generic_path(raw, label):
    '''Generic park-show pulse for un-decoded long-format packets.

    Uses a position-weighted polynomial hash to derive a deterministic
    primary palette index per capture - simple XOR collapsed multiple
    captures into the same bucket, which defeats the "tell captures
    apart on camera" goal.
    '''
    seed = 0
    for byte in raw:
        seed = (seed * 31 + byte) & 0xFFFF
    palette_size = len(magicband_protocol.PALETTE_RGB)
    primary_idx = seed % palette_size
    # Skip the "Off" palette entry so the primary is never black.
    if magicband_protocol.PALETTE_RGB[primary_idx] == (0, 0, 0):
        primary_idx = (primary_idx + 1) % palette_size
    primary_name = magicband_protocol.PALETTE_NAMES[primary_idx]
    # Anchor the primary plus three accents spaced around the palette.
    accents = (
        magicband_protocol.PALETTE_RGB[primary_idx],
        magicband_protocol.PALETTE_RGB[(primary_idx + 6) % palette_size],
        magicband_protocol.PALETTE_RGB[(primary_idx + 12) % palette_size],
        magicband_protocol.PALETTE_RGB[(primary_idx + 18) % palette_size],
    )

    def render_generic(zones, t):
        # 1.2s rotation - faster than the 2.0s used for guest commands,
        # gives the show pulse a more energetic feel.
        phase = t / 1.2
        n_slots = 4
        for zone_idx, zone in enumerate(zones):
            zone_offset = 0.5 if zone_idx == 1 else 0.0
            zone.set_led(0, accents[int(phase) % n_slots])
            outer_count = max(1, zone.count - 1)
            for led_idx in range(1, zone.count):
                angle_frac = (led_idx - 1) / outer_count
                color_phase = phase + zone_offset + angle_frac
                zone.set_led(led_idx,
                             accents[int(color_phase * n_slots) % n_slots])

    return {"duration_s": _DEFAULT_DURATION_S, "render": render_generic,
            "label": f"{label} hue={primary_name}"}


def _state_show_command(command):
    '''Park-show packet renderer (Epcot light show, etc.).

    Two paths depending on whether the payload decodes:
      - If `slots` is set (E9 08 short form), render as a 5-slot palette
        rotation matching firmware show_fx output.
      - Otherwise the long-format payloads (E9 10, E9 13, EA 14) aren't
        fully decoded yet, so render a generic park-show pulse with a
        primary hue derived from the payload bytes. Different captured
        payloads produce visibly different primary colors, so multiple
        captures can be told apart on camera even though we can't decode
        their internal structure.
    '''
    slots = command.get("slots")
    if slots is not None:
        return _show_command_slots_path(slots)
    return _show_command_generic_path(
        command["raw"], command.get("label", "SHOW"))


def _state_animation(command):
    # Generic animation (E9 0B, E9 0E, E9 0F, etc.). The jewels have 7
    # pixels each (1 center + 6 outer ring), so we can do real spatial
    # rotation: cycle the outer ring through the palette slots while
    # keeping the center a fixed color. Reads as a proper "color wheel"
    # effect like the real bands.
    raw = command["raw"]
    slots = []
    slot_names = []
    # Most animation payloads have color bytes after the 7-byte header.
    # Skip the last byte (vibration) when collecting colors.
    for byte in raw[7:-1]:
        idx = byte & 0x1F
        if idx < 0x1F:  # skip obvious non-color bytes like vibration codes
            slots.append(magicband_protocol.PALETTE_RGB[idx])
            slot_names.append(magicband_protocol.PALETTE_NAMES[idx])
    if not slots:
        slots = [(100, 100, 100)]
        slot_names = ["Gray"]
    func = command.get("func", 0)

    # Label lists distinct color short names for at-a-glance recognition.
    distinct = []
    for name in slot_names:
        short = name.split()[0][:4]
        if not distinct or distinct[-1] != short:
            distinct.append(short)
    # Cap label length so serial output stays readable
    label_colors = '>'.join(distinct[:4])
    if len(distinct) > 4:
        label_colors += '...'
    label = f"ANIM 0x{func:04X} {label_colors}"

    def render(zones, t):
        n_slots = len(slots)
        # How fast the color wheel rotates - one full revolution per period
        rotations_per_s = 1.0 / _ROTATE_PERIOD_S
        # Global phase advances linearly with time
        phase = t * rotations_per_s
        for zone_idx, zone in enumerate(zones):
            zone_offset = 0.5 if zone_idx == 1 else 0.0  # right trails left
            # Center LED gets the "middle" slot as an anchor color
            center_slot = int(phase) % n_slots
            zone.set_led(0, slots[center_slot])
            # Outer ring LEDs (1-6) each get a color at their angular
            # position, offset by the rotating phase.  count=7 means
            # indices 1..6 are outer pixels for the NeoPixel Jewel.
            outer_count = max(1, zone.count - 1)
            for led_idx in range(1, zone.count):
                # Each outer pixel's color index walks around the palette
                # based on its physical angular position + the rotation phase
                angle_frac = (led_idx - 1) / outer_count
                color_phase = phase + zone_offset + angle_frac
                slot = int(color_phase * n_slots) % n_slots
                zone.set_led(led_idx, slots[slot])

    return {
        "duration_s": _DEFAULT_DURATION_S,
        "render": render,
        "label": label,
    }


# Dispatch table for for_command(). Defined after the _state_* functions
# so all references resolve. Handlers all take a command dict, except
# _state_ping which takes no args.
_COMMAND_HANDLERS = {
    "ping": _state_ping,
    "wand_cast": _state_wand_cast,
    "single_color": _state_single_color,
    "dual_color": _state_dual_color,
    "five_color": _state_five_color,
    "six_bit_color": _state_six_bit,
    "show_fx": _state_show_fx,
    "cross_fade": _state_cross_fade,
    "animation": _state_animation,
    "parade_command": _state_parade_command,
    "show_command": _state_show_command,
    "statue_beacon": _state_statue_beacon,
    "find_me": _state_find_me,
}


def render_idle(zones):
    '''Default renderer when no animation is active. Blanks both zones.'''
    zones[0].fill((0, 0, 0))
    zones[1].fill((0, 0, 0))
