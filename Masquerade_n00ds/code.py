# SPDX-FileCopyrightText: Erin St. Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Tilt-Triggered Antler Sweep with Idle Breathing Glow
====================================================

What this does
--------------
This project uses an AW9523 constant-current LED driver to animate 3V LED n00ds
arranged as "antlers", plus a center "rose" symbol. A Prop-Maker FeatherWing's
LIS3DH accelerometer detects head tilts:

- While you're not tilting: the antlers "breathe" (pulse) between two brightness levels.
- Tilt your head LEFT  -> antlers sweep LEFT-to-RIGHT, then back (a "down and back" sweep).
- Tilt your head RIGHT -> antlers sweep RIGHT-to-LEFT, then back.
- A cooldown prevents re-triggering too quickly.

Hardware
--------
- RP2040 Prop-Maker Feather (LIS3DH accelerometer)
- AW9523 GPIO expander + constant-current LED driver (I2C)
- 7x 3V LED n00ds (wired to AW9523 LED outputs)

Wiring notes
------------
- AW9523 connects via I2C (STEMMA QT / Qwiic works great).
- Each n00d's + goes to your power rail (3V), and - goes to an AW9523 LED pin.
- The center rose symbol is on AW9523 pin 9 in this example.

How to tune
-----------
All the numbers you’ll likely tweak live in the USER SETTINGS section:
- TILT_AXIS and thresholds: for your board orientation on the headpiece
- BLINK_OFF_TIME / BLINK_GAP_TIME: sweep feel
- IDLE_LOW / IDLE_HIGH / IDLE_STEP / IDLE_DELAY: breathing glow speed + depth
- MIN_SECONDS_BETWEEN_TRIGGERS: cooldown

Tip: Start with DEBUG_PRINT = True, open the Serial Monitor, tilt your head, and
watch the axis values. Then adjust thresholds until it feels reliable.
"""

import time

import adafruit_aw9523
import adafruit_lis3dh
import board
import busio

# ============================================================
# USER SETTINGS (edit these first)
# ============================================================

# --- Brightness (0-255) ---
OFF = 0
DIM = int(255 * 0.60)   # Base level used during the sweep (returns to after each blink)
ROSE = 255              # Rose stays on continuously once it fades in

# --- Rose fade-in ---
ROSE_FADE_S = 0.90
FADE_STEPS = 80         # Higher = smoother fade (slightly more CPU time)

# --- Sweep timing ---
BLINK_OFF_TIME = 0.18   # How long each n00d goes dark (OFF) during the sweep
BLINK_GAP_TIME = 0.04   # How long to wait after returning to DIM before moving to the next n00d

# --- Idle "breathing" pulse ---
IDLE_LOW = int(255 * 0.40)
IDLE_HIGH = 255
IDLE_STEP = 3           # Smaller = smoother/slower pulse; larger = faster pulse
IDLE_DELAY = 0.015      # Larger = slower pulse; smaller = faster pulse

# --- Cooldown between triggers ---
MIN_SECONDS_BETWEEN_TRIGGERS = 3.0

# --- Tilt detection ---
TILT_AXIS = "x"              # Change to "y" or "z" depending on how the board is mounted
TILT_RIGHT_THRESHOLD = +6.0  # Tilt direction "right" if axis value >= this threshold
TILT_LEFT_THRESHOLD = -6.0   # Tilt direction "left"  if axis value <= this threshold
CONFIRM_SAMPLES = 4          # Require sustained tilt for this many samples

# --- Debug printing (Serial Monitor) ---
DEBUG_PRINT = True
PRINT_EVERY_N_SAMPLES = 2

# ============================================================
# PIN MAPPING (AW9523 pins your n00ds are connected to)
# ============================================================

# Antler groups (by your physical layout)
OUTER = [0, 1]
MIDDLE = [2, 11]
INNER = [3, 10]
ANTLERS = INNER + MIDDLE + OUTER

# Center symbol (rose)
SYMBOL_PIN = 9
SYMBOL = [SYMBOL_PIN]

# List of every AW9523 channel we touch
USED = ANTLERS + SYMBOL

# Sweep order across the antlers (left -> right).
SWEEP_L2R = [1, 2, 3, 10, 11, 0]
SWEEP_R2L = list(reversed(SWEEP_L2R))


def down_and_back(order):
    """
    Convert a one-way sweep list into a "down and back" path without repeating the end pin.

    Example:
        [A, B, C, D] -> [A, B, C, D, C, B]
    """
    if len(order) < 2:
        return order
    return order + order[-2:0:-1]


# ============================================================
# HARDWARE SETUP (I2C + devices)
# ============================================================

# Shared I2C bus (STEMMA QT port uses board.SCL/board.SDA)
i2c = busio.I2C(board.SCL, board.SDA)

# AW9523 constant-current LED driver
aw = adafruit_aw9523.AW9523(i2c)
print("Found AW9523")

# Put all pins into LED (constant-current) mode and configure as outputs
aw.LED_modes = 0xFFFF
aw.directions = 0xFFFF

# LIS3DH accelerometer (Prop-Maker FeatherWing)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)
lis3dh.range = adafruit_lis3dh.RANGE_4_G
print("Found LIS3DH")

# ============================================================
# AW9523 HELPERS (set brightness, fades, and applying updates)
# ============================================================

# Keep track of each channel's current brightness so we can fade smoothly
levels = {p: 0 for p in USED}


def apply_levels():
    """Push our current 'levels' dict out to the AW9523."""
    for pin, value in levels.items():
        aw.set_constant_current(pin, value)


def set_all(value=0):
    """Set all used channels to one brightness value (0-255)."""
    value = max(0, min(255, int(value)))
    for pin in USED:
        levels[pin] = value
    apply_levels()


def set_group(group, value):
    """Set a group of channels (list of pins) to one brightness value (0-255)."""
    value = max(0, min(255, int(value)))
    for pin in group:
        levels[pin] = value
    apply_levels()


def fade_group_to(group, target, seconds):
    """
    Fade a group of channels from their current brightness to 'target' over 'seconds'.
    """
    target = max(0, min(255, int(target)))
    start = levels[group[0]]  # groups stay aligned in this project

    if start == target or seconds <= 0:
        for pin in group:
            levels[pin] = target
        apply_levels()
        return

    dt = seconds / FADE_STEPS
    for step_i in range(FADE_STEPS + 1):
        t = step_i / FADE_STEPS
        v = int(start + (target - start) * t)
        for pin in group:
            levels[pin] = v
        apply_levels()
        time.sleep(dt)


# ============================================================
# IDLE ANIMATION (breathing/pulsing antlers)
# ============================================================

def idle_pulse_step(pulse_dir, value):
    """
    Advance the idle pulse by one small step.

    pulse_dir: +1 or -1
    value: current brightness value

    Returns updated (pulse_dir, value).
    """
    value += pulse_dir * IDLE_STEP

    if value >= IDLE_HIGH:
        value = IDLE_HIGH
        pulse_dir = -1
    elif value <= IDLE_LOW:
        value = IDLE_LOW
        pulse_dir = 1

    # Apply pulse to antlers only (rose stays on)
    for pin in ANTLERS:
        levels[pin] = value
    apply_levels()

    return pulse_dir, value


# ============================================================
# SWEEP ANIMATION (blink OFF in a path)
# ============================================================

def blink_off(pin):
    """
    Blink a single antler channel OFF briefly, then return it to DIM.
    """
    levels[pin] = OFF
    apply_levels()
    time.sleep(BLINK_OFF_TIME)

    levels[pin] = DIM
    apply_levels()
    time.sleep(BLINK_GAP_TIME)


def run_sweep_once(order):
    """
    Run exactly one down-and-back sweep (no repeated end pin).

    order: a list of pins that defines the sweep direction (e.g. SWEEP_L2R).
    """
    # Bring all antlers to a consistent base brightness for a clean sweep
    set_group(ANTLERS, DIM)

    path = down_and_back(order)
    if DEBUG_PRINT:
        print("Sweep path:", path)

    for pin in path:
        blink_off(pin)


# ============================================================
# TILT DETECTION (with idle pulsing while waiting)
# ============================================================

def pick_axis(ax, ay, az, which):
    """Return the chosen axis value from the LIS3DH reading."""
    if which == "x":
        return ax
    if which == "y":
        return ay
    return az  # "z"


def wait_for_tilt_with_idle_pulse():
    """
    Idle animation + tilt detection in one loop.

    While waiting:
      - antlers pulse between IDLE_LOW and IDLE_HIGH

    Returns:
      "left"  if tilted left
      "right" if tilted right
    """
    right_hot = 0
    left_hot = 0
    sample_count = 0

    # Start the idle pulse at the low end
    pulse_dir = 1
    pulse_val = IDLE_LOW

    if DEBUG_PRINT:
        print("\n--- Idling (pulsing) + waiting for tilt ---")

    while True:
        # 1) Do one small idle pulse step
        pulse_dir, pulse_val = idle_pulse_step(pulse_dir, pulse_val)

        # 2) Read accel + evaluate tilt
        ax, ay, az = lis3dh.acceleration
        axis_val = pick_axis(ax, ay, az, TILT_AXIS)

        # Right tilt
        if axis_val >= TILT_RIGHT_THRESHOLD:
            right_hot += 1
        else:
            right_hot = max(0, right_hot - 1)

        # Left tilt
        if axis_val <= TILT_LEFT_THRESHOLD:
            left_hot += 1
        else:
            left_hot = max(0, left_hot - 1)

        # Optional debug printing (Serial Monitor) - f-string to satisfy pylint
        if DEBUG_PRINT and (sample_count % PRINT_EVERY_N_SAMPLES == 0):
            print(
                f"{TILT_AXIS}={axis_val:6.2f} | "
                f"right_hot={right_hot} left_hot={left_hot} | "
                f"idle={pulse_val}"
            )

        # Trigger if the tilt is sustained long enough
        if right_hot >= CONFIRM_SAMPLES:
            if DEBUG_PRINT:
                print(">>> TILT RIGHT DETECTED <<<")
            return "right"

        if left_hot >= CONFIRM_SAMPLES:
            if DEBUG_PRINT:
                print(">>> TILT LEFT DETECTED <<<")
            return "left"

        sample_count += 1
        time.sleep(IDLE_DELAY)


# ============================================================
# BOOT SEQUENCE
# ============================================================

# Start everything off
set_all(OFF)

# Fade the rose up once, then leave it on
print("Boot: fading rose up...")
fade_group_to(SYMBOL, ROSE, ROSE_FADE_S)
print("Rose is ON.")

# Start antlers at a consistent level before we begin idling
set_group(ANTLERS, DIM)

# Allow an immediate trigger on startup
last_trigger_time = time.monotonic() - MIN_SECONDS_BETWEEN_TRIGGERS

# ============================================================
# MAIN LOOP
# ============================================================

while True:
    # Wait for a tilt while idling (pulsing) in the background
    tilt_direction = wait_for_tilt_with_idle_pulse()

    # Cooldown gate (prevents rapid retriggering)
    now = time.monotonic()
    if (now - last_trigger_time) < MIN_SECONDS_BETWEEN_TRIGGERS:
        if DEBUG_PRINT:
            print("(cooldown) ignoring trigger")
        continue
    last_trigger_time = now

    # NOTE: Your current mapping is intentionally swapped:
    # - tilt_direction == "left"  runs the L->R sweep
    # - tilt_direction == "right" runs the R->L sweep
    # This is handy when the board is mounted "flipped" on the headpiece.
    if tilt_direction == "left":
        if DEBUG_PRINT:
            print("\n>>> SWEEP: LEFT -> RIGHT -> BACK <<<")
        run_sweep_once(SWEEP_L2R)

    elif tilt_direction == "right":
        if DEBUG_PRINT:
            print("\n>>> SWEEP: RIGHT -> LEFT -> BACK <<<")
        run_sweep_once(SWEEP_R2L)

    # Return to a known base brightness; the idle pulse will take over immediately.
    set_group(ANTLERS, DIM)
