# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Minecraft Compass — LIS3MDL magnetometer calibration utility.

User-paced calibration with schematic motion guides and auto-save via the
boot.py NVM-remount pattern. Requires boot.py from this project, and a
tactile button wired to D5 (one leg) and GND (other leg). Internal pull-up
is enabled; button is active low.

Button controls:
  - Short press (release < 1.5 s): Advance to next step.
  - Long press (hold >= 1.5 s): Retry current step (discards its samples).

Phase 1 — calibration walkthrough (no MAG_* keys in settings.toml yet):
  1. Welcome screen, press to begin.
  2. Four motion steps, each with a schematic showing the device, its
     rotation axis, and motion arrows:
       - Spin (yaw), Tilt up/down (pitch), Tilt left/right (roll), Figure-8.
     Each is user-paced and requires a minimum sample count before advance.
  3. Find True North: lay case flat, align with a watch compass, press.
     Two seconds of readings are averaged into a heading offset so the
     case-forward direction reads 0 degrees regardless of IMU mounting.
  4. Achievement screen, then microcontroller.reset() to commit the write.

Phase 2 — live verification (settings.toml has MAG_* and MAG_HEADING_OFFSET):
  Shows live heading + cardinal + jitter. Hold the button to recalibrate
  (clears settings.toml via boot.py and reboots into the walkthrough).

Note: heading is uncompensated (assumes the case is held flat). Tilt
compensation using the LSM6DSOX accelerometer is handled in the main code.

Hardware:
- Adafruit Feather RP2350 with 8MB PSRAM (PID 6130, A4 silicon)
- Adafruit 3.5" TFT FeatherWing V2 (PID 3651) — HX8357D
- Adafruit LSM6DSOX + LIS3MDL 9-DoF IMU (PID 4517) via STEMMA QT
- Side button on D5 (active low, internal pull-up)
"""
import math
import os
import struct
import time
import board
import digitalio
import displayio
import fourwire
import microcontroller
import supervisor
import terminalio
from adafruit_debouncer import Debouncer
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.triangle import Triangle
from adafruit_display_text import label
from adafruit_hx8357 import HX8357
import adafruit_lis3mdl
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX

# --- Tunable constants ---
SAMPLE_INTERVAL_S = 0.02       # 50 Hz sampling
ACCEL_SMOOTHING = 0.2          # EMA factor for accel (lower = smoother)
MIN_SAMPLES_PER_STEP = 250     # ~5 seconds minimum per step before advance
LONG_PRESS_DURATION_S = 1.5
ACHIEVEMENT_DISPLAY_S = 3.0
NORTH_AVERAGE_S = 2.0
BUTTON_PIN = board.D5

# NVM byte indices and action codes — must match boot.py
NVM_REMOUNT_FLAG = 0
NVM_ACTION_FLAG = 1
NVM_CAL_DATA_START = 2
NVM_CAL_DATA_LEN = 28          # seven 32-bit floats
ACTION_WRITE_CALIBRATION = 1
ACTION_CLEAR_CALIBRATION = 2

# Minecraft chat color palette
GOLD = 0xFFAA00
WHITE = 0xFFFFFF
GRAY = 0xAAAAAA
XP_GREEN = 0x80FF20
DARK_BG = 0x222222
RED = 0xFF5555
YELLOW = 0xFFD700
AMBER_DIM = 0x5A3D08           # dim amber fill for the device glyph
AXIS_GRAY = 0x777777

CARDINALS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")

# Phase definitions: (step_title, one-line description, indicator_kind)
MOTION_PHASES = (
    ("Spin It Around", "Turn it flat in a full circle", "yaw"),
    ("Tip Forward & Back", "Tip it like a phone, then back", "pitch"),
    ("Tip Side to Side", "Lean it left, then lean it right", "roll"),
    ("Draw a Figure-8", "Wave a big 8 and wiggle your wrist", "fig8"),
)

# Layout coordinates (480x320). All text is center-anchored, so X is always
# the screen center (240) and Y is the vertical center of each line.
# Bands: header (y 22-86), indicator (~120-205), footer text (244-272),
# progress bar (298).
CENTER_X = 240
TITLE_Y = 24
STEP_Y = 50
INSTRUCTION_Y = 78
INDICATOR_CX, INDICATOR_CY = 240, 162
DESC_Y = 248
FOOTER_Y = 274
PROGRESS_X, PROGRESS_Y = 10, 298
PROGRESS_W, PROGRESS_H = 460, 12


def cardinal_from_heading(deg):
    sector = int((deg + 22.5) // 45) % 8
    return CARDINALS[sector]


def _planar_mag(mag_vec, roll, pitch):
    """De-rotate the magnetometer vector into the horizontal plane.

    Returns (xh, yh) horizontal-plane components for heading via atan2.
    """
    m_x, m_y, m_z = mag_vec
    sin_r = math.sin(roll)
    cos_r = math.cos(roll)
    xh = m_x * math.cos(pitch) + (m_y * sin_r + m_z * cos_r) * math.sin(pitch)
    yh = m_y * cos_r - m_z * sin_r
    return xh, yh


def tilt_compensated_heading(mag_vec, accel_vec):
    """Tilt-compensated heading in degrees from calibrated mag + accel.

    mag_vec is (mx, my, mz) calibrated magnetometer; accel_vec is
    (ax, ay, az) gravity. Pitch and roll come from gravity, then the
    magnetometer vector is de-rotated into the horizontal plane (STMicro
    AN3192). When held flat this reduces to atan2(-my, mx), matching the
    original flat-only formula, so a saved heading offset stays valid.

    If tilting makes the heading swing instead of holding steady, an
    accel axis sign is flipped on this board: negate accel_vec[0] (or
    swap the sign in _planar_mag) and recalibrate.
    """
    a_x, a_y, a_z = accel_vec
    roll = math.atan2(a_y, a_z)
    pitch = math.atan2(-a_x, math.sqrt(a_y * a_y + a_z * a_z))
    xh, yh = _planar_mag(mag_vec, roll, pitch)
    return math.degrees(math.atan2(-yh, xh)) % 360


def pitch_roll_degrees(accel_vec):
    """Return (pitch_deg, roll_deg) from a gravity vector, for diagnostics."""
    a_x, a_y, a_z = accel_vec
    roll = math.degrees(math.atan2(a_y, a_z))
    pitch = math.degrees(math.atan2(-a_x, math.sqrt(a_y * a_y + a_z * a_z)))
    return pitch, roll


def corrected_heading(mag_vec, accel_vec, offset_deg):
    """Tilt-compensated heading with mounting offset applied."""
    return (tilt_compensated_heading(mag_vec, accel_vec) - offset_deg) % 360


def load_saved_calibration():
    """Return (ox, oy, oz, sx, sy, sz, heading_offset) or None if absent."""
    if os.getenv("MAG_OFFSET_X") is None:
        return None
    return (
        float(os.getenv("MAG_OFFSET_X")),
        float(os.getenv("MAG_OFFSET_Y")),
        float(os.getenv("MAG_OFFSET_Z")),
        float(os.getenv("MAG_SCALE_X")),
        float(os.getenv("MAG_SCALE_Y")),
        float(os.getenv("MAG_SCALE_Z")),
        float(os.getenv("MAG_HEADING_OFFSET", "0")),
    )


def pack_calibration_to_nvm(cal_data):
    """Pack seven calibration floats as big-endian into NVM from byte 2.

    cal_data is (offset_x, offset_y, offset_z, scale_x, scale_y, scale_z,
    heading_offset).
    """
    packed = struct.pack(">fffffff", *cal_data)
    for i, byte_val in enumerate(packed):
        microcontroller.nvm[NVM_CAL_DATA_START + i] = byte_val


def fill_progress(bitmap, fraction):
    """Fill the progress bitmap left-to-right to the given fraction (0..1)."""
    fill_width = int(PROGRESS_W * fraction)
    for fill_x in range(fill_width):
        for fill_y in range(PROGRESS_H):
            bitmap[fill_x, fill_y] = 1


def clear_progress(bitmap):
    """Clear the entire progress bitmap."""
    for fill_x in range(PROGRESS_W):
        for fill_y in range(PROGRESS_H):
            bitmap[fill_x, fill_y] = 0


def make_shadow_label(text, center_x, center_y, scale, color):
    """Minecraft console-style centered text: 1px black shadow + foreground.

    center_x, center_y is the desired center point. The label auto-centers
    via anchor_point so strings of any length stay centered.
    """
    shadow = label.Label(
        terminalio.FONT, text=text, color=0x000000, scale=scale,
    )
    shadow.anchor_point = (0.5, 0.5)
    shadow.anchored_position = (center_x + scale, center_y + scale)
    fg = label.Label(
        terminalio.FONT, text=text, color=color, scale=scale,
    )
    fg.anchor_point = (0.5, 0.5)
    fg.anchored_position = (center_x, center_y)
    return shadow, fg


def set_shadow_text(shadow, fg, text):
    shadow.text = text
    fg.text = text


def move_shadow_label(shadow, fg, center_x, center_y):
    shadow.anchored_position = (center_x + shadow.scale, center_y + shadow.scale)
    fg.anchored_position = (center_x, center_y)


def _add_arrowhead(group, end_pt, prev_pt, color):
    """Draw a triangular arrowhead at end_pt, oriented along prev->end."""
    dx = end_pt[0] - prev_pt[0]
    dy = end_pt[1] - prev_pt[1]
    length = math.sqrt(dx * dx + dy * dy) or 1.0
    ux = dx / length
    uy = dy / length
    head = 8
    base = (end_pt[0] - ux * head, end_pt[1] - uy * head)
    group.append(
        Triangle(
            int(end_pt[0] + ux * 2), int(end_pt[1] + uy * 2),
            int(base[0] - uy * head * 0.6), int(base[1] + ux * head * 0.6),
            int(base[0] + uy * head * 0.6), int(base[1] - ux * head * 0.6),
            fill=color, outline=color,
        )
    )


def add_arc(group, center, radii, span, color):
    """Draw an elliptical arc as line segments with an arrowhead at the end.

    center is (cx, cy), radii is (rx, ry), span is (start_deg, end_deg).
    """
    segments = 16
    points = []
    for i in range(segments + 1):
        angle = math.radians(span[0] + (span[1] - span[0]) * i / segments)
        points.append(
            (int(center[0] + radii[0] * math.cos(angle)),
             int(center[1] + radii[1] * math.sin(angle)))
        )
    for start, end in zip(points, points[1:]):
        group.append(Line(start[0], start[1], end[0], end[1], color))
    _add_arrowhead(group, points[-1], points[-2], color)


def add_device_glyph(group, cx, cy):
    """Draw the device as a rounded rect with a forward-pointing arrow.

    The arrow sits above the top edge and indicates the direction the
    compass points (the "forward" heading edge), not a pivot point.
    """
    width = 64
    height = 40
    x = cx - width // 2
    y = cy - height // 2
    group.append(
        RoundRect(x, y, width, height, 6, fill=AMBER_DIM, outline=GOLD, stroke=2)
    )
    # Upward forward-arrow: tip above the top edge, base just over the edge
    tip_y = y - 14
    base_y = y - 4
    group.append(
        Triangle(cx, tip_y, cx - 8, base_y, cx + 8, base_y,
                 fill=GOLD, outline=GOLD)
    )


def add_axis_line(group, x0, y0, x1, y1):
    """Draw a rotation-axis reference line."""
    group.append(Line(x0, y0, x1, y1, AXIS_GRAY))


def _add_figure_eight(group, cx, cy):
    """Draw a lemniscate (figure-8) path centered at (cx, cy)."""
    points = []
    for i in range(33):
        angle = math.radians(i / 32 * 360)
        denom = 1 + math.sin(angle) ** 2
        fx = int(cx + 70 * math.cos(angle) / denom)
        fy = int(cy + 70 * math.sin(angle) * math.cos(angle) / denom)
        points.append((fx, fy))
    for start, end in zip(points, points[1:]):
        group.append(Line(start[0], start[1], end[0], end[1], GOLD))


def build_indicator(motion_kind):
    """Build a displayio.Group schematic for the given motion kind."""
    group = displayio.Group()
    cx = INDICATOR_CX
    cy = INDICATOR_CY

    if motion_kind == "yaw":
        add_device_glyph(group, cx, cy)
        add_arc(group, (cx, cy), (78, 30), (160, 410), GOLD)

    elif motion_kind == "pitch":
        add_axis_line(group, cx - 95, cy, cx + 95, cy)
        add_device_glyph(group, cx, cy)
        add_arc(group, (cx + 70, cy), (22, 34), (250, 470), GOLD)

    elif motion_kind == "roll":
        add_axis_line(group, cx, cy - 55, cx, cy + 55)
        add_device_glyph(group, cx, cy)
        add_arc(group, (cx, cy + 48), (40, 20), (160, 380), GOLD)

    elif motion_kind == "fig8":
        _add_figure_eight(group, cx, cy)
        add_device_glyph(group, cx, cy)

    return group


# --- Hardware setup ---
displayio.release_displays()
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = HX8357(display_bus, width=480, height=320)
root = displayio.Group()
display.root_group = root

i2c = board.STEMMA_I2C()
mag = adafruit_lis3mdl.LIS3MDL(i2c)
imu = LSM6DSOX(i2c)

# Smoothed accelerometer state. A list holder lets read_accel mutate it
# without a module-level global statement. _accel_ready guards first read.
_accel_smooth = [0.0, 0.0, 0.0]
_accel_ready = [False]


def read_accel():
    """Return an exponentially smoothed (ax, ay, az) gravity vector.

    The IMU is mounted rotated 180 degrees about its X axis in this case,
    so held flat it reports gravity on -Z (roll near 180). Negating Y and
    Z brings gravity into a Z-up frame (roll near 0 when flat), which the
    tilt-compensation math expects. Without this, roll sticks near 180 and
    the heading comes out mirrored.
    """
    a_x, a_y, a_z = imu.acceleration
    a_y = -a_y
    a_z = -a_z
    if not _accel_ready[0]:
        _accel_smooth[0] = a_x
        _accel_smooth[1] = a_y
        _accel_smooth[2] = a_z
        _accel_ready[0] = True
    else:
        _accel_smooth[0] += ACCEL_SMOOTHING * (a_x - _accel_smooth[0])
        _accel_smooth[1] += ACCEL_SMOOTHING * (a_y - _accel_smooth[1])
        _accel_smooth[2] += ACCEL_SMOOTHING * (a_z - _accel_smooth[2])
    return _accel_smooth[0], _accel_smooth[1], _accel_smooth[2]


def read_mag_calibrated(cal_data):
    """Return calibrated (mx, my, mz) using the seven-value cal tuple.

    The LIS3MDL and LSM6DSOX axes are aligned on the 4517 board, so no
    sign changes are applied. (Earlier experiments negating Y or Z were
    found to mirror the heading - raw axes are correct.)
    """
    m_x, m_y, m_z = mag.magnetic
    return (
        (m_x - cal_data[0]) * cal_data[3],
        (m_y - cal_data[1]) * cal_data[4],
        (m_z - cal_data[2]) * cal_data[5],
    )

button_io = digitalio.DigitalInOut(BUTTON_PIN)
button_io.direction = digitalio.Direction.INPUT
button_io.pull = digitalio.Pull.UP
button = Debouncer(button_io)

# Press classification state (active-low: pressed == not value). A single
# element list holds the press-start timestamp so poll_button can mutate it
# without a module-level global statement. None means no press in progress.
_press_state = [None]


def poll_button():
    """Update the debouncer and classify completed presses.

    Returns one of: "none", "short" (tap), or "long" (hold past threshold).
    A long press is reported the instant the threshold is crossed, so the
    user gets immediate feedback and can release. A short press is reported
    on release if the hold was under the threshold.
    """
    button.update()

    if button.fell:  # button just pressed (active low)
        _press_state[0] = time.monotonic()
        return "none"

    if _press_state[0] is not None:
        held = time.monotonic() - _press_state[0]
        if held >= LONG_PRESS_DURATION_S:
            _press_state[0] = None
            return "long"

    if button.rose:  # button just released
        if _press_state[0] is not None:
            _press_state[0] = None
            return "short"

    return "none"


def trigger_recalibration():
    """Clear settings.toml via boot.py and reboot into the walkthrough."""
    microcontroller.nvm[NVM_ACTION_FLAG] = ACTION_CLEAR_CALIBRATION
    microcontroller.nvm[NVM_REMOUNT_FLAG] = 1
    microcontroller.reset()


# --- Phase routing ---
saved = load_saved_calibration()

if saved is None:
    # === Phase 1: User-paced calibration walkthrough ===

    title_shadow, title_fg = make_shadow_label(
        "Crafting Compass", CENTER_X, TITLE_Y, 2, GOLD,
    )
    step_shadow, step_fg = make_shadow_label(
        "Let's Begin", CENTER_X, STEP_Y, 2, GOLD,
    )
    instruction_shadow, instruction_fg = make_shadow_label(
        "Wave to Calibrate", CENTER_X, INSTRUCTION_Y, 2, WHITE,
    )
    desc_shadow, desc_fg = make_shadow_label(
        "4 quick moves to wake up the compass", CENTER_X, DESC_Y, 1, GRAY,
    )
    footer_shadow, footer_fg = make_shadow_label(
        "Press the button to start", CENTER_X, FOOTER_Y, 2, GOLD,
    )

    # XP-bar style progress
    progress_bg_bmp = displayio.Bitmap(PROGRESS_W, PROGRESS_H, 1)
    progress_bg_palette = displayio.Palette(1)
    progress_bg_palette[0] = DARK_BG
    progress_bg_tile = displayio.TileGrid(
        progress_bg_bmp, pixel_shader=progress_bg_palette,
        x=PROGRESS_X, y=PROGRESS_Y,
    )
    progress_fill_bmp = displayio.Bitmap(PROGRESS_W, PROGRESS_H, 2)
    progress_fill_palette = displayio.Palette(2)
    progress_fill_palette[0] = 0x000000
    progress_fill_palette.make_transparent(0)
    progress_fill_palette[1] = XP_GREEN
    progress_fill_tile = displayio.TileGrid(
        progress_fill_bmp, pixel_shader=progress_fill_palette,
        x=PROGRESS_X, y=PROGRESS_Y,
    )

    # Pre-build all four indicator groups; toggle visibility per step
    indicators = {}
    for _title, _desc, kind in MOTION_PHASES:
        ind = build_indicator(kind)
        ind.hidden = True
        indicators[kind] = ind

    # Z-order: progress, indicators, then text shadows + foregrounds
    root.append(progress_bg_tile)
    root.append(progress_fill_tile)
    for ind in indicators.values():
        root.append(ind)
    for lbl in (
        title_shadow, title_fg,
        step_shadow, step_fg,
        instruction_shadow, instruction_fg,
        desc_shadow, desc_fg,
        footer_shadow, footer_fg,
    ):
        root.append(lbl)

    print("Minecraft Compass — calibration starting.")
    print("Press the side button to begin.")
    print()

    # --- Welcome screen: wait for first press ---
    while True:
        if poll_button() != "none":
            break
        time.sleep(0.005)

    # --- Per-step user-paced loop ---
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]

    phase_idx = 0
    while phase_idx < len(MOTION_PHASES):
        step_title, description, kind = MOTION_PHASES[phase_idx]

        # Show this step's text and indicator, hide the others
        set_shadow_text(
            step_shadow, step_fg,
            f"Step {phase_idx + 1} of {len(MOTION_PHASES)}",
        )
        move_shadow_label(step_shadow, step_fg, CENTER_X, STEP_Y)
        set_shadow_text(instruction_shadow, instruction_fg, step_title)
        move_shadow_label(
            instruction_shadow, instruction_fg, CENTER_X, INSTRUCTION_Y
        )
        instruction_fg.color = WHITE
        set_shadow_text(desc_shadow, desc_fg, description)
        move_shadow_label(desc_shadow, desc_fg, CENTER_X, DESC_Y)
        desc_fg.color = GRAY
        for key, ind in indicators.items():
            ind.hidden = key != kind

        # Snapshot for retry rollback
        snapshot_mins = list(mins)
        snapshot_maxs = list(maxs)
        step_samples = 0
        last_footer = 0.0
        press_latched = False

        retry_requested = False
        while True:
            event = poll_button()

            reading = mag.magnetic
            for axis in range(3):
                if reading[axis] < mins[axis]:
                    mins[axis] = reading[axis]
                if reading[axis] > maxs[axis]:
                    maxs[axis] = reading[axis]
            step_samples += 1

            # A hold triggers redo immediately. A tap latches so an early
            # tap still advances once the minimum sample count is reached.
            if event == "long":
                mins = snapshot_mins
                maxs = snapshot_maxs
                retry_requested = True
                break
            if event == "short":
                press_latched = True

            now = time.monotonic()
            if now - last_footer >= 0.2:
                ready = step_samples >= MIN_SAMPLES_PER_STEP
                if not ready:
                    set_shadow_text(
                        footer_shadow, footer_fg, "Keep moving...",
                    )
                    footer_fg.color = GRAY
                    fill_progress(
                        progress_fill_bmp, step_samples / MIN_SAMPLES_PER_STEP
                    )
                elif press_latched:
                    set_shadow_text(footer_shadow, footer_fg, "Nice! Next...")
                    footer_fg.color = XP_GREEN
                    fill_progress(progress_fill_bmp, 1.0)
                else:
                    set_shadow_text(
                        footer_shadow, footer_fg, "Tap: next   Hold: redo",
                    )
                    footer_fg.color = GOLD
                    fill_progress(progress_fill_bmp, 1.0)
                last_footer = now

            if press_latched and step_samples >= MIN_SAMPLES_PER_STEP:
                phase_idx += 1
                break

            time.sleep(SAMPLE_INTERVAL_S)

        # Clear the progress bar before the next step or retry
        clear_progress(progress_fill_bmp)

        if retry_requested:
            continue

    # Hide all indicators going into the orientation step
    for ind in indicators.values():
        ind.hidden = True

    # --- Compute calibration constants ---
    offset_x = (maxs[0] + mins[0]) / 2
    offset_y = (maxs[1] + mins[1]) / 2
    offset_z = (maxs[2] + mins[2]) / 2

    range_x = (maxs[0] - mins[0]) / 2
    range_y = (maxs[1] - mins[1]) / 2
    range_z = (maxs[2] - mins[2]) / 2
    avg_range = (range_x + range_y + range_z) / 3

    scale_x = avg_range / range_x if range_x > 0 else 1.0
    scale_y = avg_range / range_y if range_y > 0 else 1.0
    scale_z = avg_range / range_z if range_z > 0 else 1.0

    # Cal tuple (heading offset filled in after the Point to North step)
    cal = (offset_x, offset_y, offset_z, scale_x, scale_y, scale_z, 0.0)

    print("=== Motion calibration complete ===")
    print(f"X range: {mins[0]:+8.2f} to {maxs[0]:+8.2f} uT")
    print(f"Y range: {mins[1]:+8.2f} to {maxs[1]:+8.2f} uT")
    print(f"Z range: {mins[2]:+8.2f} to {maxs[2]:+8.2f} uT")
    print(f"Average range: {avg_range:0.2f} uT (Earth = 25-65 uT)")
    print()

    # --- Phase 1C: Find True North (continuous heading offset) ---
    set_shadow_text(step_shadow, step_fg, "Point to North")
    move_shadow_label(step_shadow, step_fg, CENTER_X, STEP_Y)
    set_shadow_text(
        desc_shadow, desc_fg, "Lay it flat and aim the arrow north",
    )
    move_shadow_label(desc_shadow, desc_fg, CENTER_X, DESC_Y)
    desc_fg.color = GRAY
    set_shadow_text(footer_shadow, footer_fg, "Press when it points NORTH")
    move_shadow_label(footer_shadow, footer_fg, CENTER_X, FOOTER_Y)
    footer_fg.color = GOLD

    north_latched = False
    last_preview = 0.0
    while True:
        if poll_button() != "none":
            north_latched = True
        if north_latched:
            break
        now = time.monotonic()
        if now - last_preview >= 0.1:
            preview = tilt_compensated_heading(
                read_mag_calibrated(cal), read_accel()
            )
            set_shadow_text(
                instruction_shadow, instruction_fg, f"Now: {preview:3.0f} deg",
            )
            move_shadow_label(
                instruction_shadow, instruction_fg, CENTER_X, INSTRUCTION_Y
            )
            instruction_fg.color = WHITE
            last_preview = now
        else:
            read_accel()  # keep the smoothing filter current
        time.sleep(0.02)

    # Average a couple seconds to reject momentary tilt/noise
    set_shadow_text(footer_shadow, footer_fg, "Hold still...")
    move_shadow_label(footer_shadow, footer_fg, CENTER_X, FOOTER_Y)
    footer_fg.color = YELLOW

    sin_sum = 0.0
    cos_sum = 0.0
    avg_start = time.monotonic()
    while time.monotonic() - avg_start < NORTH_AVERAGE_S:
        raw = tilt_compensated_heading(read_mag_calibrated(cal), read_accel())
        sin_sum += math.sin(math.radians(raw))
        cos_sum += math.cos(math.radians(raw))
        time.sleep(SAMPLE_INTERVAL_S)

    heading_offset = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
    print(f"Heading offset captured: {heading_offset:0.2f} deg")
    print()

    # --- Achievement Unlocked ---
    move_shadow_label(title_shadow, title_fg, CENTER_X, 40)
    set_shadow_text(title_shadow, title_fg, "Achievement Unlocked")
    set_shadow_text(step_shadow, step_fg, " ")
    move_shadow_label(instruction_shadow, instruction_fg, CENTER_X, 140)
    set_shadow_text(instruction_shadow, instruction_fg, "Compass Calibrated")
    move_shadow_label(desc_shadow, desc_fg, CENTER_X, 200)
    set_shadow_text(
        desc_shadow, desc_fg,
        f"X{offset_x:+0.1f} Y{offset_y:+0.1f} Off {heading_offset:0.0f}",
    )
    desc_fg.color = GRAY
    set_shadow_text(footer_shadow, footer_fg, "Saving and rebooting...")
    move_shadow_label(footer_shadow, footer_fg, CENTER_X, FOOTER_Y)
    footer_fg.color = GOLD

    print("Saving to settings.toml on CIRCUITPY...")
    print(f'  MAG_OFFSET_X = "{offset_x:+0.4f}"')
    print(f'  MAG_OFFSET_Y = "{offset_y:+0.4f}"')
    print(f'  MAG_OFFSET_Z = "{offset_z:+0.4f}"')
    print(f'  MAG_SCALE_X = "{scale_x:0.4f}"')
    print(f'  MAG_SCALE_Y = "{scale_y:0.4f}"')
    print(f'  MAG_SCALE_Z = "{scale_z:0.4f}"')
    print(f'  MAG_HEADING_OFFSET = "{heading_offset:0.4f}"')
    print()

    pack_calibration_to_nvm(
        (offset_x, offset_y, offset_z, scale_x, scale_y, scale_z, heading_offset)
    )
    microcontroller.nvm[NVM_ACTION_FLAG] = ACTION_WRITE_CALIBRATION
    microcontroller.nvm[NVM_REMOUNT_FLAG] = 1

    time.sleep(ACHIEVEMENT_DISPLAY_S)
    microcontroller.reset()

else:
    # === Phase 2: Calibration loaded, run live verification ===
    cal = saved
    heading_offset = cal[6]

    print("Calibration loaded from settings.toml.")
    print(f"  Offsets: X={cal[0]:+0.4f} Y={cal[1]:+0.4f} Z={cal[2]:+0.4f}")
    print(f"  Scales:  X={cal[3]:0.4f} Y={cal[4]:0.4f} Z={cal[5]:0.4f}")
    print(f"  Heading offset: {heading_offset:0.4f} deg")
    print()
    print("Live verification. Hold button to recalibrate.")

    title_shadow, title_fg = make_shadow_label(
        "Live Heading Check", CENTER_X, 30, 2, GOLD,
    )
    heading_shadow, heading_fg = make_shadow_label(
        "---", 190, 155, 7, YELLOW,
    )
    cardinal_shadow, cardinal_fg = make_shadow_label(
        "--", 320, 155, 5, WHITE,
    )
    jitter_shadow, jitter_fg = make_shadow_label(
        "Jitter: ---", CENTER_X, 250, 3, XP_GREEN,
    )
    hint_shadow, hint_fg = make_shadow_label(
        "Tap to use compass - hold to recalibrate", CENTER_X, 298, 2, GRAY,
    )
    for lbl in (
        title_shadow, title_fg,
        heading_shadow, heading_fg,
        cardinal_shadow, cardinal_fg,
        jitter_shadow, jitter_fg,
        hint_shadow, hint_fg,
    ):
        root.append(lbl)

    BUFFER_SIZE = 50
    heading_buffer = []
    last_update = 0.0

    while True:
        press = poll_button()
        if press == "long":
            set_shadow_text(hint_shadow, hint_fg, "Recalibrating...")
            hint_fg.color = YELLOW
            time.sleep(0.5)
            trigger_recalibration()
        elif press == "short":
            # Calibration is already good: hand back to the compass.
            set_shadow_text(hint_shadow, hint_fg, "Starting compass...")
            time.sleep(0.4)
            supervisor.set_next_code_file("code.py")
            supervisor.reload()

        heading_deg = corrected_heading(
            read_mag_calibrated(cal), read_accel(), heading_offset
        )

        heading_buffer.append(heading_deg)
        if len(heading_buffer) > BUFFER_SIZE:
            heading_buffer.pop(0)

        now = time.monotonic()
        if now - last_update >= 0.1 and len(heading_buffer) >= 10:
            sin_sum = sum(math.sin(math.radians(h)) for h in heading_buffer)
            cos_sum = sum(math.cos(math.radians(h)) for h in heading_buffer)
            mean_rad = math.atan2(sin_sum, cos_sum)

            max_dev = 0.0
            for h in heading_buffer:
                diff = math.radians(h) - mean_rad
                while diff > math.pi:
                    diff -= 2 * math.pi
                while diff < -math.pi:
                    diff += 2 * math.pi
                abs_dev = abs(math.degrees(diff))
                max_dev = max(max_dev, abs_dev)

            set_shadow_text(heading_shadow, heading_fg, f"{heading_deg:3.0f}")
            set_shadow_text(
                cardinal_shadow, cardinal_fg, cardinal_from_heading(heading_deg),
            )
            set_shadow_text(jitter_shadow, jitter_fg, f"Jitter: +/-{max_dev:0.1f}")

            if max_dev < 2.0:
                jitter_fg.color = XP_GREEN
            elif max_dev < 5.0:
                jitter_fg.color = YELLOW
            else:
                jitter_fg.color = RED

            last_update = now

        time.sleep(0.02)
