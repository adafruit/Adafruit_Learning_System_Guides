# SPDX-FileCopyrightText: Copyright (c) 2023 john park for Adafruit Industries
# SPDX-FileCopyrightText: 2026 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Camera preview with an accelerometer-driven bubble level for Adafruit MEMENTO."""

import math
import time

import adafruit_pycamera
import displayio
import vectorio

pycam = adafruit_pycamera.PyCamera()

# Settings
PHOTO_RESOLUTION = 8  # 0-12 preset resolutions:
#                      0: 240x240, 1: 320x240, 2: 640x480, 3: 800x600, 4: 1024x768,
#                      5: 1280x720, 6: 1280x1024, 7: 1600x1200, 8: 1920x1080, 9: 2048x1536,
#                      10: 2560x1440, 11: 2560x1600, 12: 2560x1920

LED_LEVEL = 0 # 0-4 preset brightness levels

FULL_SCALE_DEGREES = 8.0  # Bubble reaches the end at this much error
GREEN_DEGREES = 1.5
AMBER_DEGREES = 4.0
SMOOTHING = 0.18  # 0.0 = frozen, 1.0 = no filtering

# The gap between these angles prevents AUTO mode from flickering.
DOWN_ENTER_DEGREES = 35
DOWN_EXIT_DEGREES = 45

# Level geometry within the 240 x 32 band below the live preview.
BAR_WIDTH = 64
BAR_HEIGHT = 25
BAR_BOTTOM_MARGIN = 2
BUBBLE_RADIUS = 6

# Constants and Calculated Values
AUTO = 0
DOWN = 1
HORIZON = 2

GREEN = 0x00FF88
AMBER = 0xFFC43D
RED = 0xFF4D5A

BAR_LEFT = pycam.display.width // 2 - BAR_WIDTH // 2
BAR_TOP = pycam.display.height - BAR_HEIGHT - BAR_BOTTOM_MARGIN
BAR_CENTER_X = BAR_LEFT + BAR_WIDTH // 2
BAR_CENTER_Y = BAR_TOP + BAR_HEIGHT // 2
HORIZONTAL_TRAVEL = BAR_WIDTH // 2 - BUBBLE_RADIUS - 2
VERTICAL_TRAVEL = BAR_HEIGHT // 2 - BUBBLE_RADIUS - 2

def clamp(value, low, high):
    return max(low, min(high, value))

def level_color(error_degrees):
    if error_degrees <= GREEN_DEGREES:
        return GREEN
    if error_degrees <= AMBER_DEGREES:
        return AMBER
    return RED

def update_level(active_mode, x_angle, y_angle, roll_angle):
    """Move and recolor the retained vector bubble."""
    down_references.hidden = active_mode != DOWN
    horizon_references.hidden = active_mode == DOWN

    if active_mode == DOWN:
        bubble_x = BAR_CENTER_X + int(
            clamp(x_angle / FULL_SCALE_DEGREES, -1.0, 1.0) * HORIZONTAL_TRAVEL
        )
        bubble_y = BAR_CENTER_Y + int(
            clamp(y_angle / FULL_SCALE_DEGREES, -1.0, 1.0) * VERTICAL_TRAVEL
        )
        error = max(abs(x_angle), abs(y_angle))
    else:
        bubble_x = BAR_CENTER_X + int(
            clamp(roll_angle / FULL_SCALE_DEGREES, -1.0, 1.0)
            * HORIZONTAL_TRAVEL
        )
        bubble_y = BAR_CENTER_Y
        error = abs(roll_angle)

    bubble_outline.x = bubble_x
    bubble_outline.y = bubble_y
    bubble_fill.x = bubble_x
    bubble_fill.y = bubble_y
    bubble_palette[0] = level_color(error)

def take_photo(camera):
    camera.tone(1200, 0.04)
    camera.tone(1600, 0.04)
    try:
        camera.display_message("snap", color=0x00DD00)
        camera.capture_jpeg()
    except TypeError:
        camera.display_message("Capture failed", color=0xFF0000, scale=2)
        time.sleep(0.5)
    except RuntimeError:
        camera.display_message("No SD card", color=0xFF0000, scale=2)
        time.sleep(0.5)
    finally:
        camera.live_preview_mode()

pycam.mode = 0  # JPEG
pycam.resolution = PHOTO_RESOLUTION
pycam.led_level = LED_LEVEL
pycam.effect = 0

# Replace PyCamera's resolution/SD top bar with retained vector shapes. The
# camera preview begins at y=32, so this group never covers it.
black_palette = displayio.Palette(1)
black_palette[0] = 0x000000
white_palette = displayio.Palette(1)
white_palette[0] = 0xFFFFFF
bubble_palette = displayio.Palette(1)
bubble_palette[0] = RED

def white_rect(width, height, x, y):
    return vectorio.Rectangle(
        pixel_shader=white_palette, width=width, height=height, x=x, y=y
    )

level_group = displayio.Group()

# Four filled rectangles make an outlined vial.
level_group.append(white_rect(BAR_WIDTH, 1, BAR_LEFT, BAR_TOP))
level_group.append(
    white_rect(BAR_WIDTH, 1, BAR_LEFT, BAR_TOP + BAR_HEIGHT - 1)
)
level_group.append(white_rect(1, BAR_HEIGHT, BAR_LEFT, BAR_TOP))
level_group.append(
    white_rect(1, BAR_HEIGHT, BAR_LEFT + BAR_WIDTH - 1, BAR_TOP)
)

# DOWN gets a small two-axis target.
down_references = displayio.Group()
down_references.append(white_rect(9, 1, BAR_CENTER_X - 4, BAR_CENTER_Y))
down_references.append(white_rect(1, 9, BAR_CENTER_X, BAR_CENTER_Y - 4))
level_group.append(down_references)

# HORIZON gets three vertical vial marks.
horizon_references = displayio.Group()
for offset in (-HORIZONTAL_TRAVEL // 2, 0, HORIZONTAL_TRAVEL // 2):
    tick_height = 15 if offset == 0 else 9
    horizon_references.append(
        white_rect(
            1, tick_height, BAR_CENTER_X + offset, BAR_CENTER_Y - tick_height // 2
        )
    )
level_group.append(horizon_references)

bubble_outline = vectorio.Circle(
    pixel_shader=white_palette,
    radius=BUBBLE_RADIUS + 1,
    x=BAR_CENTER_X,
    y=BAR_CENTER_Y,
)
bubble_fill = vectorio.Circle(
    pixel_shader=bubble_palette,
    radius=BUBBLE_RADIUS - 1,
    x=BAR_CENTER_X,
    y=BAR_CENTER_Y,
)
level_group.append(bubble_outline)
level_group.append(bubble_fill)

# Add it on top of the toolbar
pycam.splash.append(level_group)
pycam.display.refresh()

mode_setting = AUTO
active_mode = HORIZON
screen_x, screen_y, forward = pycam.accel.acceleration
zero_down_x = 0.0
zero_down_y = 0.0
zero_horizon = 0.0
last_print = time.monotonic()

while True:
    frame = pycam.continuous_capture()
    pycam.keys_debounce()

    raw = pycam.accel.acceleration
    screen_x += (raw[0] - screen_x) * SMOOTHING
    screen_y += (raw[1] - screen_y) * SMOOTHING
    forward += (raw[2] - forward) * SMOOTHING

    angle_from_vertical = math.degrees(
        math.atan2(
            math.sqrt(screen_x * screen_x + screen_y * screen_y),
            abs(forward),
        )
    )

    if mode_setting == AUTO:
        if active_mode == HORIZON and angle_from_vertical <= DOWN_ENTER_DEGREES:
            active_mode = DOWN
        elif active_mode == DOWN and angle_from_vertical >= DOWN_EXIT_DEGREES:
            active_mode = HORIZON
    else:
        active_mode = mode_setting

    # atan2 keeps the reading stable even if total measured gravity varies.
    x_angle = math.degrees(math.atan2(screen_x, abs(forward))) - zero_down_x
    y_angle = math.degrees(math.atan2(screen_y, abs(forward))) - zero_down_y
    roll_angle = math.degrees(math.atan2(screen_x, abs(screen_y))) - zero_horizon

    if frame is not None and hasattr(frame, "width"):
        pycam.blit(frame)

    update_level(active_mode, x_angle, y_angle, roll_angle)
    pycam.display.refresh()

    if pycam.select.fell:
        mode_setting = (mode_setting + 1) % 3
        names = ("AUTO", "DOWN", "HORIZON")
        pycam.display_message(names[mode_setting], color=0xFFFFFF, scale=2)
        time.sleep(0.2)

    if pycam.ok.fell:
        if active_mode == DOWN:
            zero_down_x += x_angle
            zero_down_y += y_angle
            message = "DOWN zeroed"
        else:
            zero_horizon += roll_angle
            message = "HORIZON zeroed"
        pycam.display_message(message, color=0x00DD00, scale=2)
        time.sleep(0.2)

    if pycam.shutter.short_count:
        take_photo(pycam)

    if pycam.card_detect.fell:
        print("SD card removed")
        pycam.unmount_sd_card()
        pycam.display.refresh()

    if pycam.card_detect.rose:
        print("SD card inserted")
        pycam.display_message("Mounting SD", color=0xFFFFFF, scale=2)
        try:
            pycam.mount_sd_card()
        except OSError as error:
            print("SD mount failed:", error)
            pycam.display_message("SD failed", color=0xFF0000, scale=2)
            time.sleep(0.5)
        pycam.display.refresh()
