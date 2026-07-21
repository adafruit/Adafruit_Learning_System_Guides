# SPDX-FileCopyrightText: 2026 Erin St Blaine and ChatGPT for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Motion-reactive ember and flare animations for an LED polka-dot dress."""

# CircuitPython hardware modules are provided on-device, not by desktop Python.
# pylint: disable=import-error

import time
import math
import random
import board
import digitalio
import neopixel
import adafruit_lis3dh


# --------------------------------------------------
# PIXEL SETUP
# --------------------------------------------------

NUM_PIXELS = 216
BRIGHTNESS = 0.8

external_power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = digitalio.Direction.OUTPUT
external_power.value = True

pixels = neopixel.NeoPixel(
    board.EXTERNAL_NEOPIXELS,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.BGR,
)


# --------------------------------------------------
# ACCELEROMETER SETUP
# --------------------------------------------------

i2c = board.I2C()

accelerometer_interrupt = digitalio.DigitalInOut(
    board.ACCELEROMETER_INTERRUPT
)

lis3dh = adafruit_lis3dh.LIS3DH_I2C(
    i2c,
    int1=accelerometer_interrupt,
)

lis3dh.range = adafruit_lis3dh.RANGE_2_G


# --------------------------------------------------
# DRESS ZONES
# --------------------------------------------------

# Left skirt:  0-80
# Right skirt: 81-165
# Right top:   166-192
# Left top:    193-215

LEFT_SKIRT = tuple(range(0, 81))
RIGHT_SKIRT = tuple(range(81, 166))
RIGHT_TOP = tuple(range(166, 193))
LEFT_TOP = tuple(range(193, 216))

SKIRT_PIXELS = LEFT_SKIRT + RIGHT_SKIRT
TOP_PIXELS = RIGHT_TOP + LEFT_TOP

# Reverse one skirt range if its flare travels
# in the wrong physical direction.
#
# RIGHT_SKIRT = tuple(range(165, 80, -1))


# --------------------------------------------------
# SKIRT HEIGHT GROUPS
# --------------------------------------------------

# Pixel 0 was added to upper.
# Pixel 139 was added to middle.
# Pixel 165 was added to upper.

UPPER_SKIRT_PIXELS = (
    0, 1, 2, 3, 4,
    14, 15, 16, 17, 18, 19, 20, 21,
    39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
    74, 75, 76, 77, 78, 79, 80,
    81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
    113, 114, 115, 116, 117, 118, 119, 120,
    121, 122, 123, 124, 125,
    141, 142, 143, 144, 145, 146, 147, 148,
    149, 150, 151,
    161, 162, 163, 164, 165
)

MIDDLE_SKIRT_PIXELS = (
    5, 6, 7, 8, 9, 10, 11, 12, 13,
    22, 23, 24, 25, 26,
    35, 36, 37, 38,
    50, 51, 52, 53, 54,
    69, 70, 71, 72, 73,
    91, 92, 93, 94,
    108, 109, 110, 111, 112,
    126, 127, 128,
    136, 137, 138, 139, 140,
    152, 153, 154, 155, 156, 157, 158, 159, 160
)

LOWER_SKIRT_PIXELS = (
    27, 28, 29, 30, 31, 32, 33, 34,
    55, 56, 57, 58, 59, 60, 61, 62,
    63, 64, 65, 66, 67, 68,
    95, 96, 97, 98, 99, 100, 101, 102,
    103, 104, 105, 106, 107,
    129, 130, 131, 132, 133, 134, 135
)


# --------------------------------------------------
# EMBER SETTINGS
# --------------------------------------------------

FRAME_DELAY = 0.02

# Lower values make existing embers linger longer.
EMBER_FADE_AMOUNT = 4

# Number of new embers created each frame.
MIN_EMBERS_PER_FRAME = 4
MAX_EMBERS_PER_FRAME = 8

HOT_SPARK_CHANCE = 0.14

# Where embers appear.
LOWER_EMBER_WEIGHT = 0.55
MIDDLE_EMBER_WEIGHT = 0.30
UPPER_EMBER_WEIGHT = 0.15


# --------------------------------------------------
# CUP AFTERGLOW SETTINGS
# --------------------------------------------------

# Higher values make the animated cup fade last longer.
TOP_AFTERGLOW_FADE = 0.7

# How quickly existing cup sparkles fade between frames.
TOP_PIXEL_FADE = 0.82

# Number of new cup sparkles attempted each frame.
TOP_SPARKLE_COUNT = 4


# --------------------------------------------------
# MOTION SETTINGS
# --------------------------------------------------

MOTION_THRESHOLD = 5.0
MOTION_SMOOTHING = 0.25
TRIGGER_COUNT_REQUIRED = 1
FLARE_COOLDOWN = 0.4

DEBUG_MOTION = False

# Mutable animation and sensor state. Keeping runtime values together avoids
# module-level variables being mistaken for constants by desktop Pylint.
STATE = {
    "top_afterglow": 0.0,
    "motion_level": 0.0,
    "trigger_count": 0,
    "last_flare_time": time.monotonic(),
    "last_debug_time": time.monotonic(),
}


# --------------------------------------------------
# GENERAL HELPERS
# --------------------------------------------------

def fade_color(color, amount):
    """Subtract a fixed amount from an RGB color."""
    red, green, blue = color

    return (
        max(0, red - amount),
        max(0, green - amount),
        max(0, blue - amount),
    )


def scale_color(color, scale):
    """Scale an RGB color proportionally."""
    red = int(color[0] * scale)
    green = int(color[1] * scale)
    blue = int(color[2] * scale)

    if red < 2:
        red = 0

    if green < 2:
        green = 0

    if blue < 2:
        blue = 0

    return red, green, blue


def fade_all(amount):
    """Fade every pixel on the dress."""
    for index in range(NUM_PIXELS):
        pixels[index] = fade_color(
            pixels[index],
            amount,
        )


def clear_zone(zone):
    """Turn off every pixel in a zone."""
    for index in zone:
        pixels[index] = (0, 0, 0)


def shuffle_list(items):
    """Shuffle a list in place in CircuitPython."""
    for index in range(len(items) - 1, 0, -1):
        swap_index = random.randrange(index + 1)

        items[index], items[swap_index] = (
            items[swap_index],
            items[index],
        )


def pick_from(group):
    """Pick one item from a tuple or list."""
    return group[random.randrange(len(group))]


def pick_weighted_skirt_pixel():
    """Choose a skirt pixel, favoring the lower skirt."""
    roll = random.random()

    if roll < LOWER_EMBER_WEIGHT:
        return pick_from(LOWER_SKIRT_PIXELS)

    if roll < LOWER_EMBER_WEIGHT + MIDDLE_EMBER_WEIGHT:
        return pick_from(MIDDLE_SKIRT_PIXELS)

    return pick_from(UPPER_SKIRT_PIXELS)


# --------------------------------------------------
# EMBER EFFECT
# --------------------------------------------------

def add_weighted_ember():
    """Add one dark ember, favoring the lower skirt."""
    roll = random.random()

    if roll < LOWER_EMBER_WEIGHT:
        index = pick_from(LOWER_SKIRT_PIXELS)

        color = (
            random.randrange(55, 115),
            random.randrange(0, 16),
            0,
        )

    elif roll < LOWER_EMBER_WEIGHT + MIDDLE_EMBER_WEIGHT:
        index = pick_from(MIDDLE_SKIRT_PIXELS)

        color = (
            random.randrange(35, 85),
            random.randrange(0, 10),
            0,
        )

    else:
        index = pick_from(UPPER_SKIRT_PIXELS)

        color = (
            random.randrange(18, 50),
            random.randrange(0, 6),
            0,
        )

    pixels[index] = color


def add_hot_spark():
    """Add a brighter spark, still favoring the lower skirt."""
    roll = random.random()

    if roll < 0.60:
        index = pick_from(LOWER_SKIRT_PIXELS)

        color = (
            random.randrange(110, 180),
            random.randrange(10, 45),
            0,
        )

    elif roll < 0.90:
        index = pick_from(MIDDLE_SKIRT_PIXELS)

        color = (
            random.randrange(85, 145),
            random.randrange(6, 28),
            0,
        )

    else:
        index = pick_from(UPPER_SKIRT_PIXELS)

        color = (
            random.randrange(65, 110),
            random.randrange(2, 16),
            0,
        )

    pixels[index] = color


# --------------------------------------------------
# ANIMATED CUP AFTERGLOW
# --------------------------------------------------

def animate_top_afterglow():
    """
    Keep the cups flickering while their overall
    brightness gradually fades to black.
    """
    if STATE["top_afterglow"] <= 0.01:
        STATE["top_afterglow"] = 0.0
        clear_zone(TOP_PIXELS)
        return

    # Fade all existing cup pixels quickly enough that
    # they continue blinking instead of appearing frozen.
    for index in TOP_PIXELS:
        pixels[index] = scale_color(
            pixels[index],
            TOP_PIXEL_FADE,
        )

    # Add fresh flickering points at the current
    # afterglow brightness level.
    for _ in range(TOP_SPARKLE_COUNT):
        index = pick_from(TOP_PIXELS)
        sparkle_roll = random.random()

        if sparkle_roll < 0.12:
            base_color = (255, 180, 60)

        elif sparkle_roll < 0.45:
            base_color = (255, 70, 5)

        else:
            base_color = (170, 8, 0)

        pixels[index] = (
            int(base_color[0] * STATE["top_afterglow"]),
            int(base_color[1] * STATE["top_afterglow"]),
            int(base_color[2] * STATE["top_afterglow"]),
        )

    STATE["top_afterglow"] *= TOP_AFTERGLOW_FADE


def ember_frame():
    """Draw weighted skirt embers and animated cup afterglow."""

    # Fade skirt pixels.
    for index in SKIRT_PIXELS:
        pixels[index] = fade_color(
            pixels[index],
            EMBER_FADE_AMOUNT,
        )

    # Keep the cups flickering after a flare while
    # their maximum brightness gradually decreases.
    animate_top_afterglow()

    ember_count = random.randrange(
        MIN_EMBERS_PER_FRAME,
        MAX_EMBERS_PER_FRAME + 1,
    )

    for _ in range(ember_count):
        add_weighted_ember()

    if random.random() < HOT_SPARK_CHANCE:
        add_hot_spark()

    pixels.show()


# --------------------------------------------------
# SKIRT FLARE
# --------------------------------------------------

def draw_flare_front(zone, progress):
    """Draw a bright flare traveling through one skirt zone."""
    progress = max(0.0, min(1.0, progress))

    zone_length = len(zone)
    front = int(progress * (zone_length - 1))

    for local_index in range(front + 1):
        pixel_index = zone[local_index]
        distance = front - local_index

        if distance == 0:
            pixels[pixel_index] = (255, 180, 60)

        elif distance < 3:
            pixels[pixel_index] = (255, 70, 5)

        elif distance < 8:
            pixels[pixel_index] = (180, 10, 0)

        else:
            pixels[pixel_index] = (55, 0, 0)


# --------------------------------------------------
# CUP DISSOLVE
# --------------------------------------------------

LEFT_TOP_DISSOLVE = list(LEFT_TOP)
RIGHT_TOP_DISSOLVE = list(RIGHT_TOP)

shuffle_list(LEFT_TOP_DISSOLVE)
shuffle_list(RIGHT_TOP_DISSOLVE)


def dissolve_zone(zone_order, progress):
    """Dissolve a zone into view in randomized pixel order."""
    progress = max(0.0, min(1.0, progress))

    pixels_to_light = int(len(zone_order) * progress)

    for position in range(pixels_to_light):
        pixel_index = zone_order[position]
        age = pixels_to_light - position

        if age < 3:
            color = (255, 150, 35)

        elif age < 8:
            color = (255, 55, 5)

        else:
            color = (170, 8, 0)

        pixels[pixel_index] = color


# --------------------------------------------------
# FULL FLARE SEQUENCE
# --------------------------------------------------

def flare_up():
    """Run the skirt flare, cup dissolve, and spark burst."""
    shuffle_list(LEFT_TOP_DISSOLVE)
    shuffle_list(RIGHT_TOP_DISSOLVE)

    # Stop any previous afterglow while the new flare runs.
    STATE["top_afterglow"] = 0.0

    # Phase 1: fast skirt flare and cup dissolve.
    flare_frames = 20

    for frame in range(flare_frames):
        fade_all(30)

        progress = frame / (flare_frames - 1)

        draw_flare_front(
            LEFT_SKIRT,
            progress,
        )

        draw_flare_front(
            RIGHT_SKIRT,
            progress,
        )

        if progress > 0.35:
            top_progress = (
                progress - 0.35
            ) / 0.65

            dissolve_zone(
                LEFT_TOP_DISSOLVE,
                top_progress,
            )

            dissolve_zone(
                RIGHT_TOP_DISSOLVE,
                top_progress,
            )

        pixels.show()
        time.sleep(0.01)

    # Phase 2: short energetic spark burst.
    for _ in range(12):
        fade_all(22)

        for _ in range(10):
            index = pick_weighted_skirt_pixel()
            burst_roll = random.random()

            if burst_roll < 0.25:
                color = (255, 20, 0)

            elif burst_roll < 0.50:
                color = (255, 70, 0)

            elif burst_roll < 0.80:
                color = (255, 140, 20)

            else:
                color = (255, 220, 100)

            pixels[index] = color

        # Keep the cups actively flickering during the burst.
        for _ in range(4):
            index = pick_from(LEFT_TOP)
            pixels[index] = random.choice(
                (
                    (255, 50, 5),
                    (255, 120, 30),
                    (255, 200, 90),
                )
            )

        for _ in range(4):
            index = pick_from(RIGHT_TOP)
            pixels[index] = random.choice(
                (
                    (255, 50, 5),
                    (255, 120, 30),
                    (255, 200, 90),
                )
            )

        pixels.show()
        time.sleep(0.018)

    # Begin the animated fading cup afterglow.
    STATE["top_afterglow"] = 1.0


# --------------------------------------------------
# MOTION DETECTION
# --------------------------------------------------

def read_motion():
    """
    Measure movement based on how far total acceleration
    differs from normal gravity.
    """
    x, y, z = lis3dh.acceleration

    acceleration_magnitude = math.sqrt(
        x * x + y * y + z * z
    )

    raw_motion = abs(
        acceleration_magnitude
        - adafruit_lis3dh.STANDARD_GRAVITY
    )

    STATE["motion_level"] = (
        STATE["motion_level"] * (1.0 - MOTION_SMOOTHING)
        + raw_motion * MOTION_SMOOTHING
    )

    return STATE["motion_level"]


def motion_should_trigger():
    """Return True when motion is strong enough to trigger."""
    current_motion = read_motion()
    now = time.monotonic()

    if (
        DEBUG_MOTION
        and now - STATE["last_debug_time"] > 0.25
    ):
        print(
            "Motion:",
            round(current_motion, 2),
            "Threshold:",
            MOTION_THRESHOLD,
        )

        STATE["last_debug_time"] = now

    if current_motion > MOTION_THRESHOLD:
        STATE["trigger_count"] += 1
    else:
        STATE["trigger_count"] = 0

    if STATE["trigger_count"] >= TRIGGER_COUNT_REQUIRED:
        STATE["trigger_count"] = 0
        return True

    return False


# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

pixels.fill((0, 0, 0))
pixels.show()

while True:
    ember_frame()

    current_time = time.monotonic()

    cooldown_finished = (
        current_time - STATE["last_flare_time"]
        >= FLARE_COOLDOWN
    )

    if cooldown_finished and motion_should_trigger():
        print("FLARE!")

        STATE["last_flare_time"] = time.monotonic()

        flare_up()

        STATE["motion_level"] = 0.0
        STATE["trigger_count"] = 0

    time.sleep(FRAME_DELAY)
