# SPDX-FileCopyrightText: 2026 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Motion-Reactive Devil Horns
# Quiet ember pulse at rest
# Fast traveling flare on sharp movement
# Progressive demon charge on head tilt
#
# Adafruit RP2040 Prop-Maker Feather
#
# Pixel 0 = horn base
# Last pixel = horn tip

import math
import random
import time

import adafruit_lis3dh
import board
import digitalio
import neopixel


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

PIXEL_COUNT = 21
BRIGHTNESS = 0.9
FRAME_DELAY = 0.02

# Ember pulse timing.
EMBER_PULSE_SPEED = 1.4

# Small random flickers near the base.
EMBER_FLICKER_CHANCE = 8
EMBER_FLICKER_DECAY = 0.88

# Motion sensitivity.
MOTION_START = 1.5
MOTION_FULL = 7.0

# Sharp movement required to trigger the traveling flare.
FLARE_TRIGGER = 6.0
FLARE_COOLDOWN = 0.9

# Traveling flare behavior.
FLARE_STEP_TIME = 0.005
FLARE_WIDTH = 5

# Head tilt behavior.
#
# X axis is near 0 when your head is level.
# Tilt begins affecting the horns around this value.
TILT_TRIGGER = 3.0

# Around this X reading, the horn is fully charged.
TILT_FULL = 5.0

# Lower = slower/smoother response.
# Higher = faster response.
TILT_SMOOTHING = 0.10


# ---------------------------------------------------------------------------
# POWER AND NEOPIXEL SETUP
# ---------------------------------------------------------------------------

external_power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = digitalio.Direction.OUTPUT
external_power.value = True

pixels = neopixel.NeoPixel(
    board.EXTERNAL_NEOPIXELS,
    PIXEL_COUNT,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.GRB,
)


# ---------------------------------------------------------------------------
# ACCELEROMETER SETUP
# ---------------------------------------------------------------------------

i2c = board.I2C()
accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c)
accelerometer.range = adafruit_lis3dh.RANGE_4_G

previous_x, previous_y, previous_z = accelerometer.acceleration

motion_level = 0.0
tilt_level = 0.0
last_flare_time = -FLARE_COOLDOWN


# ---------------------------------------------------------------------------
# EMBER STATE
# ---------------------------------------------------------------------------

ember_flicker = [0.0] * PIXEL_COUNT


# ---------------------------------------------------------------------------
# FLARE STATE
# ---------------------------------------------------------------------------

flare_active = False
flare_position = 0.0
last_flare_step = time.monotonic()


# ---------------------------------------------------------------------------
# COLOR HELPERS
# ---------------------------------------------------------------------------

def scale_color(color, amount):
    """Scale an RGB color by a brightness amount."""

    amount = max(0.0, min(1.0, amount))

    return tuple(
        min(255, int(channel * amount))
        for channel in color
    )


def blend_colors(base_color, overlay_color, amount):
    """Blend two RGB colors."""

    amount = max(0.0, min(1.0, amount))

    return tuple(
        int(base + (overlay - base) * amount)
        for base, overlay in zip(base_color, overlay_color)
    )


def ember_color(position, pulse_amount):
    """Return the resting ember color for one pixel."""

    # Fade strongly from the horn base toward the tip.
    position_fade = max(
        0.0,
        1.0 - position / (PIXEL_COUNT - 1)
    )

    # Concentrate most of the glow in the lower half.
    position_fade = position_fade ** 1.8

    # Gentle breathing glow.
    brightness = (
        0.10
        + pulse_amount * 0.18
    ) * position_fade

    # Dark red with a trace of orange.
    color = (255, 24, 3)

    return scale_color(color, brightness)


def flare_color(strength):
    """Create the bright yellow-orange motion flare."""

    strength = max(0.0, min(1.0, strength))

    red = 255
    green = int(100 + 155 * strength)
    blue = int(8 + 120 * strength)

    return (
        red,
        min(255, green),
        min(135, blue),
    )


def charge_color(strength):
    """Red-orange glow for the sustained head-tilt charge."""

    strength = max(0.0, min(1.0, strength))

    red = 255
    green = int(30 + 90 * strength)
    blue = int(2 + 12 * strength)

    return (
        red,
        green,
        blue,
    )


# ---------------------------------------------------------------------------
# MOTION + TILT DETECTION
# ---------------------------------------------------------------------------

def read_motion_and_tilt():
    """Measure sharp motion and update the head-tilt level."""
    # pylint: disable=global-statement

    global previous_x, previous_y, previous_z
    global motion_level
    global tilt_level

    x, y, z = accelerometer.acceleration

    delta_x = x - previous_x
    delta_y = y - previous_y
    delta_z = z - previous_z

    previous_x = x
    previous_y = y
    previous_z = z

    acceleration_change = math.sqrt(
        delta_x * delta_x
        + delta_y * delta_y
        + delta_z * delta_z
    )

    # Preserve the existing general motion calculation.
    new_motion = (
        acceleration_change - MOTION_START
    ) / (MOTION_FULL - MOTION_START)

    new_motion = max(0.0, min(1.0, new_motion))

    if new_motion > motion_level:
        motion_level = new_motion
    else:
        motion_level *= 0.88

    # Head tilt uses the X axis.
    # abs() means left and right tilts behave identically.
    tilt_amount = abs(x)

    raw_tilt = (
        tilt_amount - TILT_TRIGGER
    ) / (TILT_FULL - TILT_TRIGGER)

    raw_tilt = max(0.0, min(1.0, raw_tilt))

    # Smooth the charge so it grows and recedes rather than jittering.
    tilt_level += (
        raw_tilt - tilt_level
    ) * TILT_SMOOTHING

    return acceleration_change


# ---------------------------------------------------------------------------
# EMBER ANIMATION
# ---------------------------------------------------------------------------

def update_embers():
    """Update small, irregular ember flickers."""

    for index in range(PIXEL_COUNT):
        ember_flicker[index] *= EMBER_FLICKER_DECAY

    # Occasional subtle flare-ups near the horn base.
    if random.randint(0, 100) < EMBER_FLICKER_CHANCE:
        flicker_pixel = random.randint(0, 4)
        ember_flicker[flicker_pixel] = random.uniform(0.15, 0.45)

        # Let some flicker spill into the next pixel.
        if flicker_pixel + 1 < PIXEL_COUNT:
            ember_flicker[flicker_pixel + 1] = max(
                ember_flicker[flicker_pixel + 1],
                ember_flicker[flicker_pixel] * 0.45,
            )


# ---------------------------------------------------------------------------
# TRAVELING FLARE
# ---------------------------------------------------------------------------

def start_traveling_flare():
    """Start a bright flare at the horn base."""
    # pylint: disable=global-statement

    global flare_active
    global flare_position
    global last_flare_step

    flare_active = True
    flare_position = -2.0
    last_flare_step = time.monotonic()


def update_traveling_flare():
    """Move the flare toward the horn tip."""
    # pylint: disable=global-statement

    global flare_active
    global flare_position
    global last_flare_step

    if not flare_active:
        return

    current_time = time.monotonic()

    if current_time - last_flare_step >= FLARE_STEP_TIME:
        flare_position += 1.0
        last_flare_step = current_time

    # End after the flare tail has fully moved past the tip.
    if flare_position - FLARE_WIDTH > PIXEL_COUNT - 1:
        flare_active = False


def flare_amount_for_pixel(index):
    """Return flare brightness for a particular pixel."""

    if not flare_active:
        return 0.0

    distance = flare_position - index

    if distance < 0 or distance > FLARE_WIDTH:
        return 0.0

    normalized = 1.0 - distance / FLARE_WIDTH

    # Keeps the flare front broad and bright.
    return normalized ** 0.45


# ---------------------------------------------------------------------------
# HEAD-TILT CHARGE
# ---------------------------------------------------------------------------

def charge_amount_for_pixel(index):
    """Return how strongly the tilt effect affects this pixel."""

    if tilt_level <= 0.0:
        return 0.0

    # As tilt increases, the glow climbs farther toward the horn tip.
    fill_position = tilt_level * (PIXEL_COUNT + 1)

    distance = fill_position - index

    if distance <= 0:
        return 0.0

    # Pixels comfortably below the fill line get the full tilt strength.
    if distance >= 2.0:
        return tilt_level

    # Soft leading edge.
    return tilt_level * (distance / 2.0)


# ---------------------------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------------------------

def draw_pixels():
    """Draw ember pulse, tilt charge, and motion flare."""

    current_time = time.monotonic()

    # Slow breathing pulse.
    pulse_wave = (
        math.sin(current_time * EMBER_PULSE_SPEED) + 1.0
    ) / 2.0

    # Keep the pulse gentle rather than fading completely out.
    pulse_amount = 0.25 + pulse_wave * 0.75

    for index in range(PIXEL_COUNT):
        base_color = ember_color(
            index,
            pulse_amount,
        )

        # Add small independent flickers.
        if ember_flicker[index] > 0:
            flicker_color = scale_color(
                (255, 48, 4),
                ember_flicker[index],
            )

            base_color = tuple(
                min(
                    255,
                    base_color[channel] + flicker_color[channel],
                )
                for channel in range(3)
            )

        # ---------------------------------------------------------------
        # HEAD-TILT CHARGE
        # ---------------------------------------------------------------

        charge_amount = charge_amount_for_pixel(index)

        if charge_amount > 0:
            charge_overlay = charge_color(charge_amount)

            base_color = blend_colors(
                base_color,
                charge_overlay,
                0.20 + charge_amount * 0.70,
            )

        # ---------------------------------------------------------------
        # TRAVELING FLARE
        # ---------------------------------------------------------------

        flare_amount = flare_amount_for_pixel(index)

        if flare_amount > 0:
            overlay = flare_color(flare_amount)

            overlay_amount = (
                0.72 + flare_amount * 0.28
            )

            final_color = blend_colors(
                base_color,
                overlay,
                overlay_amount,
            )
        else:
            final_color = base_color

        pixels[index] = final_color

    pixels.show()


# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

try:
    while True:
        motion_change = read_motion_and_tilt()
        now = time.monotonic()

        if (
            motion_change >= FLARE_TRIGGER
            and now - last_flare_time >= FLARE_COOLDOWN
        ):
            start_traveling_flare()
            last_flare_time = now

        update_embers()
        update_traveling_flare()
        draw_pixels()

        time.sleep(FRAME_DELAY)

except KeyboardInterrupt:
    pixels.fill((0, 0, 0))
    pixels.show()
    external_power.value = False
