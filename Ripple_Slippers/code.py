# SPDX-FileCopyrightText: 2026 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import neopixel

# =========================================================
# Ripple Footstep Lights with Color Cycling
# Pylint-friendly version
#
# What this project does:
# - Reads an FSR on pin A0
# - Triggers a ripple of light from the center of the strip
# - Changes color on each new press
# - If pressed again while running:
#     - the timer extends
#     - the color changes immediately
#     - the ripple restarts from the center
# =========================================================


# -----------------------------
# USER SETTINGS
# -----------------------------
NUM_PIXELS = 20
ACTIVE_SECONDS = 3.0
PIXEL_BRIGHTNESS = 0.3

# Lower = faster ripple, higher = slower ripple
RIPPLE_DELAY = 0.05

# Lower = shorter trail, higher = longer trail
TRAIL_FADE = 0.6

# End fade settings
FADE_DELAY = 0.03
FADE_STEPS = 20

# Color cycle: white -> pink -> purple -> blue
COLOR_SEQUENCE = [
    (255, 255, 255),  # white
    (255, 100, 180),  # pink
    (180, 0, 255),    # purple
    (0, 120, 255),    # blue
]

print("boot")


# -----------------------------
# SENSOR SETUP
# -----------------------------
# FSR wired between A0 and GND.
# With internal pull-up enabled:
# - unpressed = True
# - pressed = False
motion = digitalio.DigitalInOut(board.A0)
motion.direction = digitalio.Direction.INPUT
motion.pull = digitalio.Pull.UP
print("motion ready")


# -----------------------------
# EXTERNAL POWER SETUP
# -----------------------------
# The Prop-Maker Feather needs EXTERNAL_POWER enabled
# to power the external NeoPixel terminal.
external_power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = digitalio.Direction.OUTPUT
external_power.value = True
print("external power enabled")


# -----------------------------
# NEOPIXEL SETUP
# -----------------------------
pixels = neopixel.NeoPixel(
    board.EXTERNAL_NEOPIXELS,
    NUM_PIXELS,
    brightness=PIXEL_BRIGHTNESS,
    auto_write=False
)
print("pixels ready")


# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def clear():
    """Turn all pixels off."""
    pixels.fill((0, 0, 0))
    pixels.show()


def dim_rgb(rgb_value, factor):
    """Return a dimmed version of an RGB color tuple."""
    return (
        int(rgb_value[0] * factor),
        int(rgb_value[1] * factor),
        int(rgb_value[2] * factor),
    )


def get_next_color(sequence_index):
    """
    Advance to the next color in the sequence.

    Returns:
        tuple: (new_index, new_rgb)
    """
    new_index = (sequence_index + 1) % len(COLOR_SEQUENCE)
    return new_index, COLOR_SEQUENCE[new_index]


def ripple_frame(center_pixel, radius, ripple_rgb):
    """
    Draw one frame of the ripple animation.

    center_pixel: where the ripple starts
    radius: how far the wave has expanded
    ripple_rgb: current ripple color
    """
    for pixel_index in range(NUM_PIXELS):
        distance = abs(pixel_index - center_pixel)

        # Bright wave front
        if distance == radius:
            pixels[pixel_index] = ripple_rgb

        # Optional thicker wave front:
        # Uncomment these two lines and comment out the line above
        # if abs(distance - radius) <= 1:
        #     pixels[pixel_index] = ripple_rgb

        # Fade the trail behind the wave
        elif distance < radius:
            red, green, blue = pixels[pixel_index]
            pixels[pixel_index] = (
                int(red * TRAIL_FADE),
                int(green * TRAIL_FADE),
                int(blue * TRAIL_FADE),
            )

        # Pixels ahead of the wave stay off
        else:
            pixels[pixel_index] = (0, 0, 0)

    pixels.show()


def ripple_for(seconds, start_rgb, starting_index):
    """
    Run the ripple animation for a set amount of time.

    If the sensor is pressed again while the animation is running:
    - extend the timer
    - change to the next color
    - restart the ripple from the center

    Returns:
        int: updated color sequence index
    """
    center_pixel = NUM_PIXELS // 2
    active_rgb = start_rgb
    sequence_index = starting_index
    end_time = time.monotonic() + seconds
    was_pressed = False
    radius = 0

    while time.monotonic() < end_time:
        is_pressed = not motion.value

        # Detect a new press during the active animation
        if is_pressed and not was_pressed:
            sequence_index, active_rgb = get_next_color(sequence_index)
            print("extended, new color:", active_rgb)

            end_time = time.monotonic() + seconds
            radius = 0

        ripple_frame(center_pixel, radius, active_rgb)

        radius += 1
        if radius > NUM_PIXELS:
            radius = 0

        time.sleep(RIPPLE_DELAY)
        was_pressed = is_pressed

    return sequence_index


def fade_out():
    """Fade the current pixels smoothly to black."""
    current_pixels = [pixels[pixel_index] for pixel_index in range(NUM_PIXELS)]

    for step in range(FADE_STEPS, -1, -1):
        factor = step / FADE_STEPS

        for pixel_index in range(NUM_PIXELS):
            pixels[pixel_index] = dim_rgb(current_pixels[pixel_index], factor)

        pixels.show()
        time.sleep(FADE_DELAY)

    clear()


# -----------------------------
# STARTUP FLASH
# -----------------------------
startup_colors = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
]

for startup_rgb in startup_colors:
    pixels.fill(startup_rgb)
    pixels.show()
    time.sleep(0.2)

clear()
print("starting loop")


# -----------------------------
# MAIN LOOP
# -----------------------------
last_state = motion.value
current_sequence_index = -1

while True:
    current_state = motion.value

    if current_state != last_state:
        print("changed:", current_state)

        # Trigger on press: True -> False
        if not current_state:
            print("TRIGGERED")

            current_sequence_index, trigger_rgb = get_next_color(
                current_sequence_index
            )
            print("color:", trigger_rgb)

            current_sequence_index = ripple_for(
                ACTIVE_SECONDS,
                trigger_rgb,
                current_sequence_index
            )

            fade_out()

        last_state = current_state

    time.sleep(0.01)
