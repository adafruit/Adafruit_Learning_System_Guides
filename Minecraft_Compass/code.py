# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Minecraft Compass — Dial preview.

Stand-alone preview that draws the compass dial face with a rotating
needle driven by live tilt-compensated heading from settings.toml. Use to
iterate on the visual design before wiring it into the main code.py.

Layout (480x320):
  - Header row at top: mode label + heading number
  - Dial centered at (240, 160), outer radius 115
  - Footer row at bottom: hints and cardinal label
  - Cardinal letters N/E/S/W fixed at 12/3/6/9 o'clock
  - Small gold tick triangles point inward at each cardinal
  - Dim gold dots at NE/SE/SW/NW for finer angular reference
  - Rotating needle: red north tip (longer) + grey south tail (shorter)
  - Gold pivot dot covers the hinge

Requires:
  - boot.py and a completed calibration.py run (settings.toml present)
  - LSM6DSOX + LIS3MDL on STEMMA QT (PID 4517)
  - 3.5 inch TFT FeatherWing V2 (PID 3651)
  - Side button on D5 (used here only for recalibration)
"""
import gc
import json
import math
import os
import time
import board
import bitmaptools
import digitalio
import displayio
import fourwire
import microcontroller
import supervisor
import terminalio
import vectorio
from adafruit_debouncer import Debouncer
from adafruit_display_text import label
from adafruit_hx8357 import HX8357
import adafruit_gps
import adafruit_lis3mdl
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
from adafruit_max1704x import MAX17048
import adafruit_tsc2007

# --- Tunable constants ---
ACCEL_SMOOTHING = 0.2
HEADING_SMOOTHING = 0.25   # low-pass on the heading angle (0=frozen, 1=raw)
NEEDLE_DEADBAND_DEG = 1.5  # don't redraw the needle if it moved less than this
LONG_PRESS_S = 1.5        # hold this long = save waypoint
EXTRA_LONG_PRESS_S = 3.5  # keep holding this long = toggle theme
BUTTON_PIN = board.D5

# Modes
MODE_COMPASS = 0
MODE_WAYPOINT = 1
MODE_NAMES = ("Compass", "Waypoint")

# Magnetic declination correction in degrees (east positive). Central
# Florida is about -6. Left at 0 for now; will become a menu setting so
# the user never edits code. Applied to the true-north GPS bearing to
# convert it into the magnetic frame the compass heading uses.
MAGNETIC_DECLINATION = 0.0

# Earth radius for haversine distance (metres)
EARTH_RADIUS_M = 6371000.0

# Waypoint state. waypoints is a list of (lat, lon, name) tuples, up to
# MAX_WAYPOINTS. active_index[0] selects which one is the current nav
# target. Both persist to WAYPOINTS_FILE (a JSON object with the list and
# the active index) so the last selection survives a power cycle.
# Coordinates are true-north (e.g. pasted from Google Maps); magnetic
# declination is applied later at display time.
WAYPOINTS_FILE = "/waypoints.json"
MAX_WAYPOINTS = 8
waypoints = []        # list of (lat, lon, name)
active_index = [0]    # index into waypoints of the active nav target

# Layout
CENTER_X = 240
CENTER_Y = 160
CARDINAL_RADIUS = 92
DOT_RADIUS = 100
# The footer text is centered in the case opening (more room on the left).
# The header is RIGHT-anchored at a fixed gap before the charging bolt, so
# its spacing to the battery cluster stays constant for any name length and
# long names (e.g. "Stronghold") grow leftward into the free space instead
# of colliding with the bolt. Tuned to the enclosure with calipers.
HEADER_RIGHT_X = 254
FOOTER_CENTER_X = 208

# Battery indicator: a row of discrete vertical bars (Minecraft-style),
# filling left-to-right with green as charge rises; unfilled bars are dark
# red, with the percentage overlaid in white. Sits in the header just to
# the right of the centered title (which stays aligned over the dial),
# matching the layout in the reference photos. Verified to fit inside the
# case cutout's top band (see screen.svg).
BATT_BARS = 5
BATT_BAR_W = 7
BATT_BAR_GAP = 2
BATT_BAR_H = 22
BATT_X = 277            # left edge of first bar; cluster centered in opening
BATT_Y = 10             # top edge of the bars (title baseline is ~y=20)
BATT_NUB_W = 4
BATT_NUB_H = 10
BATT_BAR_GREEN = 0x35C035
BATT_BAR_EMPTY = 0x7A1010   # dark red for depleted bars
# Percentage label centered over the bar row.
BATT_PCT_X = BATT_X + (BATT_BARS * (BATT_BAR_W + BATT_BAR_GAP)) // 2
BATT_PCT_Y = BATT_Y + BATT_BAR_H // 2

# Charging bolt, shown just left of the battery when the gauge reports a
# positive charge rate (cable plugged in and charging). Gold lightning
# glyph so it reads against the dark background.
BOLT_X = 264
BOLT_Y = BATT_Y
BOLT_COLOR = 0xFFD000

# Touch calibration: TSC2007 raw ranges mapped to screen pixels. Values
# from Adafruit's reference for this FeatherWing; fine-tuned if needed.
TOUCH_MIN_X = 300
TOUCH_MAX_X = 3800
TOUCH_MIN_Y = 185
TOUCH_MAX_Y = 3700
TOUCH_PRESSURE_MIN = 100   # ignore feather-light/false touches below this
# When the display is rotated 180, the touch panel's slight Y calibration
# asymmetry shows up as a constant offset. Measured at ~22 px on hardware.
ROTATED_TOUCH_Y_FIX = 22
# Likewise, rotating the panel 180 shifts the whole image horizontally by a
# few px (panel addressing asymmetry). At 0 the UI is centered; at 180 it
# drifts right, so shift the root group left by this much when flipped.
# Positive value moves content left. Tuned on hardware via calipers so 180
# matches the 0 layout.
ROTATED_X_SHIFT = 21

# Inventory button: translucent white rounded square with three dots,
# Inventory button: small grey square with three dots, in the Waypoint
# Mode footer at the same size and position as the Compass Mode settings
# gear (bottom-right corner). The two never show at once (different
# modes), so they share the corner for a consistent look. Tapping it opens
# the waypoint list.
INV_BTN_SIZE = 30
INV_BTN_X = 316
INV_BTN_Y = 284
INV_DOT_R = 3

# Waypoint list panel (Minecraft settings style): dark-grey outline,
# light-grey row cells, dark text, green trash boxes. Sized to sit inside
# the cutout's full-width band (display y 63..248).
LIST_X = 70
LIST_Y = 66
LIST_W = 360
LIST_H = 180
LIST_PAD = 8
LIST_TITLE_H = 28
LIST_ROW_H = 32
LIST_ROW_GAP = 3
LIST_VISIBLE_ROWS = 4
LIST_ARROW_COL_W = 30
# Close button (X) in the title bar, top-right.
LIST_CLOSE_SIZE = 20
# Trash box at the right end of each row.
LIST_TRASH_SIZE = 24
# Minecraft settings palette
LIST_OUTLINE = 0x3A3A3A     # dark grey panel outline / title bar
LIST_PANEL_BG = 0x202022    # panel interior
LIST_ROW_BG = 0xC6C6C6      # light grey row cell
LIST_ROW_TEXT = 0x2A2A2A    # dark grey row text
LIST_TRASH_BG = 0x35C035    # green trash box
LIST_ARROW = 0x9A9A9A       # grey scroll triangles

# Name picker modal: a grid of preset names shown when saving a new
# waypoint, so it gets a real name instead of "WP N". Reuses the list
# panel footprint. 10 presets in a 2-column, 5-row grid.
PICK_NAMES = (
    "Home", "Spawn", "Portal", "Mine", "Castle",
    "Nether", "End", "Stronghold", "Outpost", "Camp",
)
PICK_COLS = 2
PICK_ROWS = 5
PICK_PAD = 10
PICK_TITLE_H = 26
PICK_CELL_GAP = 6
PICK_CELL_BG = 0xC6C6C6
PICK_CELL_TEXT = 0x2A2A2A

# Settings gear button: small box in the Compass Mode footer (bottom-right,
# mirroring the battery's top-right position). Opens the settings panel.
GEAR_SIZE = 30
GEAR_X = 316
GEAR_Y = 284

# Settings panel: reuses the list panel footprint and styling. Two rows:
# Recalibrate, and Marine Mode toggle.
SET_X = LIST_X
SET_Y = LIST_Y
SET_W = LIST_W
SET_H = LIST_H
SET_PAD = 10
SET_TITLE_H = 28
SET_ROW_H = 30
SET_ROW_GAP = 5

# Pixel-art needle, matching the reference exactly (pixel-sampled). The
# needle is a zigzag chain of touching cells, red tip to grey tail, with
# no gap at the pivot. Each art-pixel is drawn as a block with a dark
# outline for the "made of blocks" Minecraft look. Coordinates are in
# art-pixel units relative to the pivot; col 0 is the needle's center
# column, row increases downward. Red points UP (negative rows) at
# heading 0.
PIXEL = 16
STROKE = 3  # dark block outline thickness in screen pixels

# Reference layout (north-up), pivot between the lowest red and top grey.
# This layout is the source-of-truth for the pre-rendered needle.bmp (which
# the rotozoom needle rotates each frame); the constants are kept for
# documentation and so the bitmap can be regenerated if the art changes.
#   col -1  0  1
#   .       .  R   row -4  (tip)
#   .       .  R   row -3
#   .       R  R   row -2  (step left)
#   .       R  .   row -1
#   G       G  .   row  0  (grey begins, adjacent to red)
#   G       .  .   row  1
RED_PIXEL_CELLS = [
    (1, -4),
    (1, -3),
    (0, -2), (1, -2),
    (0, -1),
]
GREY_PIXEL_CELLS = [
    (-1, 0), (0, 0),
    (-1, 1),
]

# Fixed colors (same in both themes): the needle reads well on either
# background, so red/grey/outline never change.
RED = 0xD63A2E
GREY = 0x707070
BLOCK_OUTLINE = 0x101010  # dark edge around each needle block

# Themes. Each defines the colors that swap between dark (default, indoor /
# low light) and light (bright sunlight) modes. Triple-press toggles them.
#   bg:     screen background fill
#   accent: cardinal letters and ticks (gold on dark, dark amber on light)
#   dot:    intercardinal dots
#   text:   footer / header foreground
#   shadow: 1px drop shadow behind text (opposite of text for contrast)
THEME_DARK = {
    "bg": 0x000000,
    "accent": 0xFFAA00,    # bright gold
    "dot": 0x8A5A00,       # dim gold
    "text": 0xFFFFFF,      # white
    "shadow": 0x000000,    # black shadow
}
THEME_LIGHT = {
    "bg": 0xF2F2F2,        # near-white, easy to see in sun
    "accent": 0xB5660A,    # darker amber for contrast on light bg
    "dot": 0xC08A2A,       # mid amber
    "text": 0x101010,      # near-black text
    "shadow": 0xFFFFFF,    # white shadow for separation on light bg
}
THEMES = (THEME_DARK, THEME_LIGHT)

CARDINALS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def cardinal_from_heading(deg):
    """Return the 8-point compass label (N, NE, ...) for a heading in degrees."""
    return CARDINALS[int((deg + 22.5) // 45) % 8]


def format_distance(metres):
    """Human-friendly distance string in the selected units.

    Metric: metres under 1 km, else km. Imperial: feet under 0.1 mi, else
    miles. The units flag is read at call time from units_imperial.
    """
    if units_imperial[0]:
        miles = metres / 1609.344
        if miles < 0.1:
            return f"{metres * 3.28084:.0f} ft"
        return f"{miles:.1f} mi"
    if metres < 1000:
        return f"{metres:.0f} m"
    return f"{metres / 1000:.1f} km"


def haversine_distance(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres between two lat/lon points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    sin_dphi = math.sin(d_phi / 2)
    sin_dlam = math.sin(d_lambda / 2)
    a = sin_dphi * sin_dphi + math.cos(phi1) * math.cos(phi2) * sin_dlam * sin_dlam
    central_angle = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * central_angle


def initial_bearing(lat1, lon1, lat2, lon2):
    """Initial true-north compass bearing in degrees from point 1 to 2."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    y = math.sin(d_lambda) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2)
         - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda))
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def load_calibration():
    """Return cal tuple (ox, oy, oz, sx, sy, sz, heading_offset) or None."""
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


def load_waypoints():
    """Load waypoints and the active index from WAYPOINTS_FILE.

    The file is a JSON object {"active": int, "waypoints": [...]}. For
    backward compatibility a plain JSON list (the old format, or a
    hand-edited list pasted from Google Maps) is also accepted. A missing
    or malformed file leaves the list empty. Up to MAX_WAYPOINTS entries
    are kept. Failures print a reason to the serial console so a bad
    hand-edit is not a silent mystery.
    """
    try:
        with open(WAYPOINTS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError:
        print(f"waypoints: no {WAYPOINTS_FILE} found (starting empty)")
        return
    except ValueError as parse_error:
        print(f"waypoints: {WAYPOINTS_FILE} is not valid JSON: {parse_error}")
        print("  check for trailing commas or single quotes; use \" quotes")
        return
    if isinstance(data, dict):
        entries = data.get("waypoints", [])
        active = data.get("active", 0)
    else:
        entries = data          # old/hand-edited plain-list format
        active = 0
    waypoints.clear()
    try:
        for entry in entries[:MAX_WAYPOINTS]:
            waypoints.append(
                (float(entry["lat"]), float(entry["lon"]), entry["name"])
            )
    except (KeyError, TypeError, ValueError) as entry_error:
        print(f"waypoints: bad entry in {WAYPOINTS_FILE}: {entry_error}")
        print('  each entry needs "name", "lat", "lon"')
    if waypoints:
        active_index[0] = max(0, min(len(waypoints) - 1, active))
        print(f"waypoints: loaded {len(waypoints)} "
              f"({', '.join(w[2] for w in waypoints)})")
    else:
        active_index[0] = 0


def save_waypoints():
    """Write waypoints and active index to WAYPOINTS_FILE as JSON.

    Requires the filesystem to be writable by code.py, which boot.py
    arranges on a normal (device-mode) boot. If the filesystem is
    read-only (computer-edit mode), the write raises OSError, which the
    caller treats as a failed save.
    """
    data = {
        "active": active_index[0],
        "waypoints": [
            {"name": name, "lat": lat, "lon": lon}
            for (lat, lon, name) in waypoints
        ],
    }
    with open(WAYPOINTS_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle)


def active_waypoint():
    """Return the active (lat, lon, name) tuple, or None if list empty."""
    if not waypoints:
        return None
    return waypoints[active_index[0]]


def _planar_mag(mag_vec, roll, pitch):
    m_x, m_y, m_z = mag_vec
    sin_r = math.sin(roll)
    cos_r = math.cos(roll)
    xh = m_x * math.cos(pitch) + (m_y * sin_r + m_z * cos_r) * math.sin(pitch)
    yh = m_y * cos_r - m_z * sin_r
    return xh, yh


def tilt_compensated_heading(mag_vec, accel_vec):
    """Compute a tilt-compensated compass heading (deg) from mag + accel.

    Uses the accelerometer to find roll/pitch (AN3192 method) and de-rotates
    the magnetometer vector so the heading stays correct when the device is
    not held flat.
    """
    a_x, a_y, a_z = accel_vec
    roll = math.atan2(a_y, a_z)
    pitch = math.atan2(-a_x, math.sqrt(a_y * a_y + a_z * a_z))
    xh, yh = _planar_mag(mag_vec, roll, pitch)
    return math.degrees(math.atan2(-yh, xh)) % 360


def corrected_heading(mag_vec, accel_vec, offset_deg):
    """Tilt-compensated heading minus the calibration offset, wrapped 0-360."""
    return (tilt_compensated_heading(mag_vec, accel_vec) - offset_deg) % 360


def angle_diff(a, b):
    """Smallest signed difference a - b in degrees, in range (-180, 180]."""
    return (a - b + 180) % 360 - 180


def smooth_heading(raw, previous, factor):
    """Low-pass a heading toward raw along the shortest arc (wrap-aware).

    Headings are circular (359 and 1 are adjacent), so a plain average
    would swing the long way around 0/360. This nudges previous toward raw
    by factor of the shortest angular step and re-wraps into 0-360.
    """
    if previous is None:
        return raw
    return (previous + factor * angle_diff(raw, previous)) % 360


# --- Hardware setup ---
displayio.release_displays()
spi = board.SPI()
# board.SPI() defaults to a conservative baud rate, which made each
# display.refresh() take ~150 ms. Raising it to 24 MHz roughly halved that
# to ~76 ms. Note: the RP2350 SPI clock is an integer divisor of the system
# clock, so it rounds the request DOWN to the nearest achievable rate.
# 24 MHz lands on a good divisor; requesting 32 MHz actually rounds to a
# SLOWER real rate here, so 24 MHz is the sweet spot. (Measured.)
display_bus = fourwire.FourWire(
    spi, command=board.D10, chip_select=board.D9, baudrate=24_000_000
)
display = HX8357(display_bus, width=480, height=320)
# Manual refresh: the needle is redrawn by clearing its bitmap then drawing
# the rotated image. With auto-refresh on, the display could refresh in the
# gap between clear and draw, showing a blank "blink". Refreshing manually
# once per loop (after all drawing) makes each frame appear all at once.
display.auto_refresh = False
root = displayio.Group()
display.root_group = root

# --- Theme system ---
def solid_palette(color):
    """Return a 1-entry displayio.Palette filled with the given color."""
    pal = displayio.Palette(1)
    pal[0] = color
    return pal


# theme_index[0] selects THEMES[...]. Two-tier hold toggles dark/light.
# Persisted in one NVM byte (writable from code without a remount, unlike
# settings.toml). Default to light (index 1) for outdoor daylight use.
# NVM byte 30 is used here, clear of the calibration data in bytes 0-29.
NVM_THEME_BYTE = 30
# Marine mode: when on, the compass needle always points to true north
# (marine convention) instead of at the cardinal you face (intuitive,
# default). Persisted in NVM byte 31.
NVM_MARINE_BYTE = 31
# Units: 0 = metric (m/km), 1 = imperial (miles). Persisted in NVM byte 32.
NVM_UNITS_BYTE = 32
# Magnetic declination: stored as an index into DECLINATION_OPTIONS in NVM
# byte 33. Declination is the angle between true and magnetic north; East
# is positive, West negative. Central Florida is about 6 degrees West.
NVM_DECLINATION_BYTE = 33
DECLINATION_OPTIONS = (20, 15, 10, 5, 0, -5, -10, -15, -20)
DECLINATION_DEFAULT_INDEX = 4   # 0 degrees
# Display rotation: 0 = normal, 1 = flipped 180 degrees. Lets the case be
# built with the button at the bottom. Persisted in NVM byte 34.
NVM_ROTATION_BYTE = 34


def load_theme_index():
    """Read the saved theme index from NVM, defaulting to light (1)."""
    stored = microcontroller.nvm[NVM_THEME_BYTE]
    return stored if stored < len(THEMES) else 1


def load_marine_mode():
    """Read the saved marine-mode flag from NVM (default off)."""
    return microcontroller.nvm[NVM_MARINE_BYTE] == 1


def load_units_imperial():
    """Read the saved units flag from NVM (default metric)."""
    return microcontroller.nvm[NVM_UNITS_BYTE] == 1


def load_declination_index():
    """Read the saved declination option index from NVM (default 0 deg)."""
    stored = microcontroller.nvm[NVM_DECLINATION_BYTE]
    if stored < len(DECLINATION_OPTIONS):
        return stored
    return DECLINATION_DEFAULT_INDEX


def load_rotation_flipped():
    """Read the saved display-rotation flag from NVM (default not flipped)."""
    return microcontroller.nvm[NVM_ROTATION_BYTE] == 1


theme_index = [load_theme_index()]
marine_mode = [load_marine_mode()]
units_imperial = [load_units_imperial()]
declination_index = [load_declination_index()]
rotation_flipped = [load_rotation_flipped()]


def apply_rotation():
    """Set display rotation and the matching root X shift for the flip.

    At 180 the panel drifts the image right a few px, so nudge the whole
    root group left by ROTATED_X_SHIFT to recenter. The oversized
    background keeps the shifted edge filled.
    """
    if rotation_flipped[0]:
        display.rotation = 180
        root.x = -ROTATED_X_SHIFT
    else:
        display.rotation = 0
        root.x = 0


# Apply the saved display rotation (180 deg if the case has the button at
# the bottom). Touch coordinates are flipped to match in read_touch().
apply_rotation()

# Full-screen background rectangle, drawn first (behind everything). Its
# palette entry is mutated on theme change. Oversized and offset negative so
# that shifting the root group (rotation X correction) never exposes an
# unfilled edge.
bg_palette = displayio.Palette(1)
bg_palette[0] = THEMES[0]["bg"]
bg_rect = vectorio.Rectangle(
    pixel_shader=bg_palette, width=560, height=400, x=-40, y=-40,
)
root.append(bg_rect)

# Registries of themeable elements, populated as the UI is built. Each
# accent/dot palette is mutated in place; each label records which theme
# role drives its color so apply_theme can update them.
accent_palettes = []   # palettes that follow theme["accent"]
dot_palettes = []      # palettes that follow theme["dot"]
text_labels = []       # (fg, shadow) pairs following text/shadow
accent_text_labels = []  # (fg, shadow) pairs whose fg follows accent


def themed_accent_palette():
    """Accent-colored palette, registered so it re-themes on theme change."""
    pal = solid_palette(THEMES[theme_index[0]]["accent"])
    accent_palettes.append(pal)
    return pal


def themed_dot_palette():
    """Dot-colored palette, registered so it re-themes on theme change."""
    pal = solid_palette(THEMES[theme_index[0]]["dot"])
    dot_palettes.append(pal)
    return pal


def apply_theme():
    """Push the active theme's colors into all registered elements."""
    theme = THEMES[theme_index[0]]
    bg_palette[0] = theme["bg"]
    for pal in accent_palettes:
        pal[0] = theme["accent"]
    for pal in dot_palettes:
        pal[0] = theme["dot"]
    for fg_label, shadow_label in text_labels:
        fg_label.color = theme["text"]
        shadow_label.color = theme["shadow"]
    for fg_label, shadow_label in accent_text_labels:
        fg_label.color = theme["accent"]
        shadow_label.color = theme["shadow"]


def toggle_theme():
    """Advance to the next theme, persist it to NVM, and repaint."""
    theme_index[0] = (theme_index[0] + 1) % len(THEMES)
    microcontroller.nvm[NVM_THEME_BYTE] = theme_index[0]
    apply_theme()

i2c = board.STEMMA_I2C()
mag = adafruit_lis3mdl.LIS3MDL(i2c)
imu = LSM6DSOX(i2c)

# PA1010D GPS on the same STEMMA QT chain (I2C address 0x10).
gps = adafruit_gps.GPS_GtopI2C(i2c, debug=False)
# Stream just the sentences we need: GGA (fix + sats) and RMC (position).
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
# Update position once per second (plenty for walking navigation).
gps.send_command(b"PMTK220,1000")

# MAX17048 fuel gauge (I2C 0x36) is optional: the Feather RP2350 has no
# onboard gauge, so this is an external breakout that may not be mounted
# yet. Scan for it and only use it if present; otherwise the battery
# indicator is simply hidden and everything else runs normally.
def detect_battery_gauge():
    """Return a MAX17048 if one answers at 0x36, else None."""
    while not i2c.try_lock():
        pass
    try:
        present = 0x36 in i2c.scan()
    finally:
        i2c.unlock()
    return MAX17048(i2c) if present else None


battery = detect_battery_gauge()
battery_present = battery is not None

# TSC2007 resistive touch controller (I2C 0x48 on the same bus). The
# invert_x + swap_xy options map raw touch coordinates to the 480x320
# landscape display orientation (per Adafruit's reference for this wing).
touch = adafruit_tsc2007.TSC2007(i2c, invert_x=True, swap_xy=True)

button_io = digitalio.DigitalInOut(BUTTON_PIN)
button_io.direction = digitalio.Direction.INPUT
button_io.pull = digitalio.Pull.UP
button = Debouncer(button_io)

_accel_smooth = [0.0, 0.0, 0.0]
_accel_ready = [False]


def read_accel():
    """Read the accelerometer, correcting for the IMU's 180-deg X mounting.

    The board mounts the LSM6DSOX rotated 180 about X, so ay and az are
    negated; ax is unchanged.
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
    """Read the magnetometer and apply hard/soft-iron calibration.

    cal_data is (offset_x, offset_y, offset_z, scale_x, scale_y, scale_z)
    from the calibration walk-through; each axis is centered then scaled.
    """
    m_x, m_y, m_z = mag.magnetic
    return (
        (m_x - cal_data[0]) * cal_data[3],
        (m_y - cal_data[1]) * cal_data[4],
        (m_z - cal_data[2]) * cal_data[5],
    )


_press_state = [None]   # press-start time, or None when not pressed
_hold_tier = [0]        # 0 none, 1 past LONG, 2 past EXTRA_LONG


def poll_button():
    """Classify button activity with two hold tiers.

    Returns one of:
      "none"       - nothing this poll
      "short"      - quick tap (released before LONG_PRESS_S)
      "enter_save" - crossed into the save tier while holding (feedback)
      "enter_theme"- crossed into the theme tier while holding (feedback)
      "save"       - released within the save tier
      "theme"      - released within the theme tier
    The "enter_*" events let the caller flash on-screen feedback so the
    user knows which tier they are in before releasing.
    """
    button.update()

    if button.fell:
        _press_state[0] = time.monotonic()
        _hold_tier[0] = 0
        return "none"

    result = "none"

    if _press_state[0] is not None:
        held = time.monotonic() - _press_state[0]
        if held >= EXTRA_LONG_PRESS_S and _hold_tier[0] < 2:
            _hold_tier[0] = 2
            result = "enter_theme"
        elif held >= LONG_PRESS_S and _hold_tier[0] < 1:
            _hold_tier[0] = 1
            result = "enter_save"

    if button.rose and _press_state[0] is not None:
        tier = _hold_tier[0]
        _press_state[0] = None
        _hold_tier[0] = 0
        result = ("short", "save", "theme")[tier]

    return result


# --- Reusable palette + shape helpers ---
def make_shadow_label(text_str, center_x, center_y, scale, role="text"):
    """Center-anchored label with a 1px drop shadow, themed.

    role is "accent" (cardinal letters, header) or "text" (footer). The
    label's colors follow the active theme and update on theme change.
    """
    theme = THEMES[theme_index[0]]
    fg_color = theme["accent"] if role == "accent" else theme["text"]
    shadow = label.Label(
        terminalio.FONT, text=text_str, color=theme["shadow"], scale=scale,
    )
    shadow.anchor_point = (0.5, 0.5)
    shadow.anchored_position = (center_x + scale, center_y + scale)
    fg = label.Label(
        terminalio.FONT, text=text_str, color=fg_color, scale=scale,
    )
    fg.anchor_point = (0.5, 0.5)
    fg.anchored_position = (center_x, center_y)
    if role == "accent":
        accent_text_labels.append((fg, shadow))
    else:
        text_labels.append((fg, shadow))
    return shadow, fg


def cardinal_position(angle_deg, radius):
    """Return (x, y) at the given angle (0=top, clockwise) on a circle."""
    rad = math.radians(angle_deg)
    return (
        CENTER_X + int(radius * math.sin(rad)),
        CENTER_Y - int(radius * math.cos(rad)),
    )


# --- Build the static dial ---
static_group = displayio.Group()

# Intermediate tick dots at 45deg positions (NE/SE/SW/NW), themed dot color
for ang in (45, 135, 225, 315):
    x_dot, y_dot = cardinal_position(ang, DOT_RADIUS)
    static_group.append(
        vectorio.Circle(
            pixel_shader=themed_dot_palette(), radius=3, x=x_dot, y=y_dot,
        )
    )

# Cardinal letters (accent color)
for letter, ang in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
    lx, ly = cardinal_position(ang, CARDINAL_RADIUS)
    s_lbl, fg_lbl = make_shadow_label(letter, lx, ly, 3, "accent")
    static_group.append(s_lbl)
    static_group.append(fg_lbl)

# Header label: mode + heading (accent). Footer: heading number (text).
# The header is right-anchored just before the bolt (constant gap, long
# names grow left); the footer is centered in the opening.
header_shadow, header_fg = make_shadow_label(
    "Compass", HEADER_RIGHT_X, 20, 2, "accent",
)
# Re-anchor the header to its right edge so names extend leftward.
header_shadow.anchor_point = (1.0, 0.5)
header_shadow.anchored_position = (HEADER_RIGHT_X + 2, 20 + 2)
header_fg.anchor_point = (1.0, 0.5)
header_fg.anchored_position = (HEADER_RIGHT_X, 20)
heading_num_shadow, heading_num_fg = make_shadow_label(
    "---", FOOTER_CENTER_X, 300, 2, "text",
)

# --- Battery indicator ---
# Five charge bars over a gold backing, so the gaps between bars show the
# title's accent gold in both themes. A terminal nub, charging bolt, and
# % label sit on top.
battery_group = displayio.Group()

# Gold backing spanning the full bar row (including the inter-bar gaps),
# themed so the gaps match the title accent color in either theme.
BATT_ROW_W = BATT_BARS * BATT_BAR_W + (BATT_BARS - 1) * BATT_BAR_GAP
battery_group.append(
    vectorio.Rectangle(
        pixel_shader=themed_accent_palette(),
        width=BATT_ROW_W, height=BATT_BAR_H, x=BATT_X, y=BATT_Y,
    )
)

# Build the five bars left-to-right, each with its own palette so it can
# be recolored individually (green when filled, dark red when empty). They
# sit on the gold backing, so the 2px gaps between them show gold.
batt_bar_palettes = []
for bar_i in range(BATT_BARS):
    bar_palette = solid_palette(BATT_BAR_EMPTY)
    batt_bar_palettes.append(bar_palette)
    battery_group.append(
        vectorio.Rectangle(
            pixel_shader=bar_palette,
            width=BATT_BAR_W, height=BATT_BAR_H,
            x=BATT_X + bar_i * (BATT_BAR_W + BATT_BAR_GAP), y=BATT_Y,
        )
    )
# Terminal nub on the right end (themed accent, like a battery tip).
batt_nub_palette = themed_accent_palette()
battery_group.append(
    vectorio.Rectangle(
        pixel_shader=batt_nub_palette,
        width=BATT_NUB_W, height=BATT_NUB_H,
        x=BATT_X + BATT_BARS * (BATT_BAR_W + BATT_BAR_GAP),
        y=BATT_Y + (BATT_BAR_H - BATT_NUB_H) // 2,
    )
)

# Percentage overlaid on the bars, scale 2 to match the title font size.
# Fixed white in both themes (not theme-following): the green/red bars are
# the same in either theme, so the battery should look identical and white
# reads cleanly on both bar colors. This keeps the dark-theme look the user
# preferred when on the light theme too.
batt_pct_fg = label.Label(
    terminalio.FONT, text="--", color=0xFFFFFF, scale=2,
)
batt_pct_fg.anchor_point = (0.5, 0.5)
batt_pct_fg.anchored_position = (BATT_PCT_X, BATT_PCT_Y)
battery_group.append(batt_pct_fg)

# Charging bolt glyph: a small lightning zigzag drawn relative to
# (BOLT_X, BOLT_Y). A 1px-offset shadow in the title's amber-brown sits
# behind it so the gold bolt stays legible on the light theme's pale
# background. Both are hidden unless the gauge reports charging. Each
# polygon gets its OWN points list (vectorio can hold the list by
# reference, so sharing one object between two polygons is unsafe).
BOLT_POINTS = [
    (5, 0), (0, 12), (4, 12), (1, 22),
    (10, 9), (5, 9), (8, 0),
]
bolt_shadow = vectorio.Polygon(
    pixel_shader=solid_palette(0xB5660A),
    points=list(BOLT_POINTS), x=BOLT_X + 1, y=BOLT_Y + 1,
)
battery_group.append(bolt_shadow)
bolt_palette = solid_palette(BOLT_COLOR)
bolt_poly = vectorio.Polygon(
    pixel_shader=bolt_palette, points=list(BOLT_POINTS),
    x=BOLT_X, y=BOLT_Y,
)
battery_group.append(bolt_poly)
bolt_shadow.hidden = True
bolt_poly.hidden = True


def update_battery():
    """Read the fuel gauge and update the bar colors and percentage label.

    Fills bars left-to-right with green as charge rises; the rest stay dark
    red. Does nothing if no gauge is present (indicator stays hidden).
    """
    if not battery_present:
        return
    pct = max(0, min(100, int(battery.cell_percent)))
    # Each bar represents 20%, rounded to nearest: (pct+10)//20 green bars,
    # the rest dark red. Matches the reference set exactly (5%->0 green,
    # 20%->1, 40%->2, 60%->3, 80%->4, 99%->5).
    filled = min(BATT_BARS, (pct + 10) // 20)
    for idx, palette in enumerate(batt_bar_palettes):
        palette[0] = BATT_BAR_GREEN if idx < filled else BATT_BAR_EMPTY
    # Cap at 99 so the readout is always two digits, matching the reference
    # graphic and keeping the font large enough to align with the title.
    display_pct = min(99, pct)
    batt_pct_fg.text = f"{display_pct}"
    # Show the charging bolt (and its shadow) when the gauge reports a
    # positive charge rate (cable seated and charging). charge_rate is
    # percent/hour: positive = charging. A small deadband avoids flicker
    # near zero when the battery is full and barely trickling.
    charging = battery.charge_rate > 0.5
    bolt_poly.hidden = not charging
    bolt_shadow.hidden = not charging

# --- Build the rotating needle (rotozoom bitmap) ---
# The needle is a single pre-rendered pixel-art bitmap (needle.bmp, same
# look as the old block needle) rotated each frame with bitmaptools.rotozoom.
# Rotating one solid image avoids the seams that appeared when 16 separate
# polygons were rotated independently, and the RP2350's FPU makes rotozoom
# fast. A square source/dest (NEEDLE_SIZE) keeps the needle from clipping at
# any angle; the pivot is the bitmap center. The background palette index
# (NEEDLE_SKIP) is treated as transparent so the dial shows through.
NEEDLE_SIZE = 128
NEEDLE_SKIP = 0   # palette index 0 in needle.bmp is the transparent key
needle_group = displayio.Group()


def _read_bmp_palette(data, pal_offset, colors):
    """Build a displayio.Palette from a BMP's BGRA palette table."""
    palette = displayio.Palette(colors)
    for i in range(colors):
        blue = data[pal_offset + i * 4]
        green = data[pal_offset + i * 4 + 1]
        red = data[pal_offset + i * 4 + 2]
        palette[i] = (red << 16) | (green << 8) | blue
    return palette


def load_indexed_bmp(path):
    """Load a small uncompressed 8-bit indexed BMP into a Bitmap + Palette.

    rotozoom needs a real Bitmap, and OnDiskBitmap is neither rotozoom-able
    nor subscriptable, so the file is parsed directly. This handles the
    specific BMP we ship (8-bit, uncompressed, bottom-up); it is not a
    general decoder. Avoids depending on adafruit_imageload.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    pixel_offset = int.from_bytes(data[10:14], "little")
    header_size = int.from_bytes(data[14:18], "little")
    width = int.from_bytes(data[18:22], "little")
    height = int.from_bytes(data[22:26], "little")
    colors = int.from_bytes(data[46:50], "little") or 256
    palette = _read_bmp_palette(data, 14 + header_size, colors)
    # Rows are padded to a 4-byte boundary and stored bottom-up.
    row_size = ((width + 3) // 4) * 4
    bitmap = displayio.Bitmap(width, height, colors)
    for row in range(height):
        base = pixel_offset + (height - 1 - row) * row_size
        for col in range(width):
            bitmap[col, row] = data[base + col]
    return bitmap, palette


# rotozoom requires a real Bitmap source; load the needle file into one.
needle_source, needle_shader = load_indexed_bmp("/needle.bmp")
needle_shader.make_transparent(NEEDLE_SKIP)
# Dest bitmap rotozoom draws into each frame; shares the source palette.
needle_dest = displayio.Bitmap(NEEDLE_SIZE, NEEDLE_SIZE, len(needle_shader))
needle_tile = displayio.TileGrid(
    needle_dest, pixel_shader=needle_shader,
    x=CENTER_X - NEEDLE_SIZE // 2, y=CENTER_Y - NEEDLE_SIZE // 2,
)
needle_group.append(needle_tile)


def set_needle_heading(heading):
    """Rotate the needle bitmap so its red tip points at the given heading.

    Heading 0 = red tip up (toward the fixed N letter); 90 = tip right (E).
    rotozoom rotates the source needle into the dest bitmap about its
    center. The angle is negated so increasing heading turns the tip
    clockwise (matching the compass), and offset so 0 points up.
    """
    # Clear the dest to the transparent index, then draw the rotated needle.
    needle_dest.fill(NEEDLE_SKIP)
    bitmaptools.rotozoom(
        needle_dest, needle_source,
        angle=-math.radians(heading),
        scale=1.0,
        skip_index=NEEDLE_SKIP,
    )


# --- Inventory button (opens the waypoint list) ---
# A translucent-white rounded square with three dots, like Minecraft's
# inventory/menu button. vectorio has no real alpha, so a light grey
# approximates "translucent white" and reads on both themes.
inventory_group = displayio.Group()
inventory_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(0xC8C8C8),
        width=INV_BTN_SIZE, height=INV_BTN_SIZE,
        x=INV_BTN_X, y=INV_BTN_Y,
    )
)
# Three dark dots across the center, spaced to fit the smaller button.
_inv_dot_palette = solid_palette(0x303030)
for _dot in (-1, 0, 1):
    inventory_group.append(
        vectorio.Circle(
            pixel_shader=_inv_dot_palette, radius=INV_DOT_R,
            x=INV_BTN_X + INV_BTN_SIZE // 2 + _dot * 9,
            y=INV_BTN_Y + INV_BTN_SIZE // 2,
        )
    )


def read_touch():
    """Return (x, y) screen pixels for a current touch, or None.

    Reads the TSC2007 and scales raw coordinates into the 480x320 frame.
    Touches below the pressure threshold are treated as no touch.
    """
    if not touch.touched:
        return None
    point = touch.touch
    if point["pressure"] < TOUCH_PRESSURE_MIN:
        return None
    raw_x = point["x"]
    raw_y = point["y"]
    screen_x = int(
        (raw_x - TOUCH_MIN_X) * 480 / (TOUCH_MAX_X - TOUCH_MIN_X)
    )
    screen_y = int(
        (raw_y - TOUCH_MIN_Y) * 320 / (TOUCH_MAX_Y - TOUCH_MIN_Y)
    )
    screen_x = max(0, min(479, screen_x))
    screen_y = max(0, min(319, screen_y))
    # When the display is flipped 180 degrees, the touch panel is not, so
    # mirror the coordinates. Two corrections on top of the mirror: the
    # panel's slight Y calibration asymmetry shows as a ~22 px shift
    # (ROTATED_TOUCH_Y_FIX), and the root group is nudged left by
    # ROTATED_X_SHIFT to recenter the image, so add that back in X to keep
    # taps aligned with the (shifted) drawn elements.
    if rotation_flipped[0]:
        screen_x = min(479, max(0, 479 - screen_x + ROTATED_X_SHIFT))
        screen_y = min(319, max(0, 319 - screen_y + ROTATED_TOUCH_Y_FIX))
    return screen_x, screen_y


def point_in_rect(point, x, y, width, height):
    """True if point (px, py) lies within the rectangle."""
    px, py = point
    return x <= px <= x + width and y <= py <= y + height


def touched_inventory_button(point):
    """True if the touch point is on the inventory button."""
    return point_in_rect(
        point, INV_BTN_X, INV_BTN_Y, INV_BTN_SIZE, INV_BTN_SIZE
    )


# --- Waypoint list panel (Minecraft settings style) ---
# Built once, hidden by default. Shown over the dial when the inventory
# button is tapped. Rows are repopulated from `waypoints` each time it
# opens, scrolled by a window offset (list_scroll[0]).
list_group = displayio.Group()
list_scroll = [0]   # index of the first visible row
armed_delete = [-1]  # waypoint index armed for delete confirm, or -1 = none
armed_select = [-1]  # waypoint index armed for load confirm, or -1 = none

# Panel background + outline (outline drawn as a slightly larger rect).
list_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_OUTLINE),
        width=LIST_W, height=LIST_H, x=LIST_X, y=LIST_Y,
    )
)
list_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_PANEL_BG),
        width=LIST_W - 6, height=LIST_H - LIST_TITLE_H - 3,
        x=LIST_X + 3, y=LIST_Y + LIST_TITLE_H,
    )
)

# Title bar label.
_list_title = label.Label(
    terminalio.FONT, text="Waypoints", color=0xFFFFFF, scale=2,
)
_list_title.anchor_point = (0.0, 0.5)
_list_title.anchored_position = (LIST_X + LIST_PAD, LIST_Y + LIST_TITLE_H // 2)
list_group.append(_list_title)

# Close button (X) in the title bar, top-right.
LIST_CLOSE_X = LIST_X + LIST_W - LIST_PAD - LIST_CLOSE_SIZE
LIST_CLOSE_Y = LIST_Y + (LIST_TITLE_H - LIST_CLOSE_SIZE) // 2
_close_label = label.Label(
    terminalio.FONT, text="X", color=0xFFFFFF, scale=2,
)
_close_label.anchor_point = (0.5, 0.5)
_close_label.anchored_position = (
    LIST_CLOSE_X + LIST_CLOSE_SIZE // 2, LIST_CLOSE_Y + LIST_CLOSE_SIZE // 2,
)
list_group.append(_close_label)

# Row geometry helper.
LIST_ROWS_TOP = LIST_Y + LIST_TITLE_H + 4
LIST_ROW_X = LIST_X + LIST_PAD
LIST_ROW_W = LIST_W - 2 * LIST_PAD - LIST_ARROW_COL_W


def list_row_y(row_i):
    """Top y of the row at visible position row_i (0..VISIBLE-1)."""
    return LIST_ROWS_TOP + row_i * (LIST_ROW_H + LIST_ROW_GAP)


# Pre-create the visible row widgets (cell, name label, trash box). They
# are repopulated/hidden as the list scrolls and as waypoints change.
list_row_cells = []
list_row_labels = []
list_row_trash = []
list_trash_palettes = []   # per-row trash box palette (recolored when armed)
list_trash_glyphs = []     # (lid, body) per row, hidden with empty rows
list_cell_palettes = []    # per-row cell palette (highlighted when armed)
LIST_TRASH_X = LIST_ROW_X + LIST_ROW_W - LIST_TRASH_SIZE - 4
LIST_TRASH_ARMED = 0xD02020    # red when armed for delete confirmation
LIST_ROW_ARMED = 0xF0B000      # gold highlight when armed for load
for _r in range(LIST_VISIBLE_ROWS):
    _ry = list_row_y(_r)
    _cell_palette = solid_palette(LIST_ROW_BG)
    list_cell_palettes.append(_cell_palette)
    _cell = vectorio.Rectangle(
        pixel_shader=_cell_palette,
        width=LIST_ROW_W, height=LIST_ROW_H, x=LIST_ROW_X, y=_ry,
    )
    list_group.append(_cell)
    list_row_cells.append(_cell)
    _name = label.Label(
        terminalio.FONT, text="", color=LIST_ROW_TEXT, scale=2,
    )
    _name.anchor_point = (0.0, 0.5)
    _name.anchored_position = (LIST_ROW_X + 8, _ry + LIST_ROW_H // 2)
    list_group.append(_name)
    list_row_labels.append(_name)
    # Green trash box at the right end of the row (own palette so it can
    # turn red when armed for delete confirmation).
    _tx = LIST_TRASH_X
    _ty = _ry + (LIST_ROW_H - LIST_TRASH_SIZE) // 2
    _trash_palette = solid_palette(LIST_TRASH_BG)
    list_trash_palettes.append(_trash_palette)
    _trash = vectorio.Rectangle(
        pixel_shader=_trash_palette,
        width=LIST_TRASH_SIZE, height=LIST_TRASH_SIZE, x=_tx, y=_ty,
    )
    list_group.append(_trash)
    list_row_trash.append(_trash)
    # White trash glyph: a simple lid + body using small rectangles.
    _trash_lid = vectorio.Rectangle(
        pixel_shader=solid_palette(0xFFFFFF),
        width=LIST_TRASH_SIZE - 12, height=2,
        x=_tx + 6, y=_ty + 7,
    )
    list_group.append(_trash_lid)
    _trash_body = vectorio.Rectangle(
        pixel_shader=solid_palette(0xFFFFFF),
        width=LIST_TRASH_SIZE - 14, height=LIST_TRASH_SIZE - 14,
        x=_tx + 7, y=_ty + 10,
    )
    list_group.append(_trash_body)
    list_trash_glyphs.append((_trash_lid, _trash_body))

# Scroll arrows (grey triangles with a drop shadow) in the right column.
# Larger than typical so they are easy to tap on the resistive screen, and
# each gets a generous hit box (LIST_ARROW_HIT_W x _H) centered on it.
LIST_ARROW_X = LIST_X + LIST_W - LIST_PAD - 15
_ARROW_UP_Y = LIST_ROWS_TOP + 10
_ARROW_DN_Y = list_row_y(LIST_VISIBLE_ROWS - 1) + LIST_ROW_H - 10
LIST_ARROW_HALF_W = 12
LIST_ARROW_HEIGHT = 14
LIST_ARROW_HIT_W = 40
LIST_ARROW_HIT_H = 54


def _triangle_points(cx, cy, half_w, height, pointing_up):
    """Return three points for a triangle centered horizontally at cx."""
    if pointing_up:
        return [(cx, cy - height), (cx - half_w, cy), (cx + half_w, cy)]
    return [(cx, cy + height), (cx - half_w, cy), (cx + half_w, cy)]


def _add_arrow(cx, cy, pointing_up):
    """Append a grey triangle with a 1px drop shadow; return (shadow, fg)."""
    shadow = vectorio.Polygon(
        pixel_shader=solid_palette(0x101010),
        points=_triangle_points(
            cx + 1, cy + 1, LIST_ARROW_HALF_W, LIST_ARROW_HEIGHT, pointing_up
        ),
        x=0, y=0,
    )
    fg = vectorio.Polygon(
        pixel_shader=solid_palette(LIST_ARROW),
        points=_triangle_points(
            cx, cy, LIST_ARROW_HALF_W, LIST_ARROW_HEIGHT, pointing_up
        ),
        x=0, y=0,
    )
    list_group.append(shadow)
    list_group.append(fg)
    return shadow, fg


_arrow_up = _add_arrow(LIST_ARROW_X, _ARROW_UP_Y, True)
_arrow_dn = _add_arrow(LIST_ARROW_X, _ARROW_DN_Y, False)

list_group.hidden = True


def refresh_list_rows():
    """Populate the visible row widgets from `waypoints` and the scroll pos.

    Empty rows (past the end of the list) are hidden. The active waypoint's
    row name is marked with a leading '>'. A row armed for load is
    highlighted gold (also showing the '>' pointer); a row armed for delete
    shows a red trash box.
    """
    for row_i in range(LIST_VISIBLE_ROWS):
        wp_i = list_scroll[0] + row_i
        lid, body = list_trash_glyphs[row_i]
        if wp_i < len(waypoints):
            name = waypoints[wp_i][2]
            armed_load = wp_i == armed_select[0]
            marker = "> " if (wp_i == active_index[0] or armed_load) else ""
            list_row_labels[row_i].text = marker + name
            list_row_cells[row_i].hidden = False
            list_row_labels[row_i].hidden = False
            list_row_trash[row_i].hidden = False
            lid.hidden = False
            body.hidden = False
            # Gold cell when armed for load, normal light grey otherwise.
            list_cell_palettes[row_i][0] = (
                LIST_ROW_ARMED if armed_load else LIST_ROW_BG
            )
            armed = wp_i == armed_delete[0]
            list_trash_palettes[row_i][0] = (
                LIST_TRASH_ARMED if armed else LIST_TRASH_BG
            )
        else:
            list_row_labels[row_i].text = ""
            list_row_cells[row_i].hidden = True
            list_row_labels[row_i].hidden = True
            list_row_trash[row_i].hidden = True
            lid.hidden = True
            body.hidden = True
    # Arrows are visible only when scrolling is possible in that direction.
    can_up = list_scroll[0] > 0
    can_down = list_scroll[0] + LIST_VISIBLE_ROWS < len(waypoints)
    _arrow_up[0].hidden = not can_up
    _arrow_up[1].hidden = not can_up
    _arrow_dn[0].hidden = not can_down
    _arrow_dn[1].hidden = not can_down


def open_list():
    """Show the waypoint list, hiding the dial behind it."""
    list_scroll[0] = 0
    armed_delete[0] = -1
    armed_select[0] = -1
    refresh_list_rows()
    list_group.hidden = False


def close_list():
    """Hide the waypoint list, returning to the dial."""
    list_group.hidden = True


def touched_list_close(point):
    """True if the touch point is on the close (X) button."""
    return point_in_rect(
        point, LIST_CLOSE_X, LIST_CLOSE_Y, LIST_CLOSE_SIZE, LIST_CLOSE_SIZE
    )


def touched_scroll_up(point):
    """True if the touch point is on the up arrow (and it's active)."""
    if _arrow_up[1].hidden:
        return False
    return point_in_rect(
        point, LIST_ARROW_X - LIST_ARROW_HIT_W // 2,
        _ARROW_UP_Y - LIST_ARROW_HIT_H // 2,
        LIST_ARROW_HIT_W, LIST_ARROW_HIT_H,
    )


def touched_scroll_down(point):
    """True if the touch point is on the down arrow (and it's active)."""
    if _arrow_dn[1].hidden:
        return False
    return point_in_rect(
        point, LIST_ARROW_X - LIST_ARROW_HIT_W // 2,
        _ARROW_DN_Y - LIST_ARROW_HIT_H // 2,
        LIST_ARROW_HIT_W, LIST_ARROW_HIT_H,
    )


def touched_row(point):
    """Return the waypoint index for a tapped row, or None.

    Only the main row area counts as a select (the trash box is handled
    separately). Returns the absolute index into `waypoints`.
    """
    for row_i in range(LIST_VISIBLE_ROWS):
        wp_i = list_scroll[0] + row_i
        if wp_i >= len(waypoints):
            break
        row_y = list_row_y(row_i)
        # Main area excludes the trash box on the right.
        main_w = LIST_ROW_W - LIST_TRASH_SIZE - 8
        if point_in_rect(point, LIST_ROW_X, row_y, main_w, LIST_ROW_H):
            return wp_i
    return None


def touched_trash(point):
    """Return the waypoint index whose trash box was tapped, or None."""
    for row_i in range(LIST_VISIBLE_ROWS):
        wp_i = list_scroll[0] + row_i
        if wp_i >= len(waypoints):
            break
        row_y = list_row_y(row_i)
        ty = row_y + (LIST_ROW_H - LIST_TRASH_SIZE) // 2
        if point_in_rect(
            point, LIST_TRASH_X, ty, LIST_TRASH_SIZE, LIST_TRASH_SIZE
        ):
            return wp_i
    return None


def delete_waypoint(wp_index):
    """Remove the waypoint at wp_index, fix up the active index, persist."""
    del waypoints[wp_index]
    # Keep active_index pointing at a valid entry. If we removed the active
    # one or an earlier one, clamp/shift so it stays sensible.
    if active_index[0] >= len(waypoints):
        active_index[0] = max(0, len(waypoints) - 1)
    elif wp_index < active_index[0]:
        active_index[0] -= 1
    # Keep the scroll window valid as the list shrinks.
    max_scroll = max(0, len(waypoints) - LIST_VISIBLE_ROWS)
    if list_scroll[0] > max_scroll:
        list_scroll[0] = max_scroll
    try:
        save_waypoints()
    except OSError:
        pass  # deletion still applies this session


def handle_trash_tap(wp_index):
    """Arm a trash box on first tap, delete on second tap of the same box."""
    if armed_delete[0] == wp_index:
        # Second tap on the armed box: confirm delete.
        delete_waypoint(wp_index)
        armed_delete[0] = -1
    else:
        # First tap: arm this row for delete (turns the box red), and
        # clear any pending load arm so only one thing is armed at a time.
        armed_delete[0] = wp_index
        armed_select[0] = -1
    refresh_list_rows()


def handle_row_tap(wp_index):
    """Arm a row on first tap, load it on the second tap of the same row.

    Returns True if a waypoint was loaded (caller should close the list).
    """
    if armed_select[0] == wp_index:
        # Second tap on the armed row: confirm load.
        active_index[0] = wp_index
        armed_select[0] = -1
        try:
            save_waypoints()
        except OSError:
            pass  # selection still applies this session
        return True
    # First tap: arm this row (gold highlight), clear any delete arm.
    armed_select[0] = wp_index
    armed_delete[0] = -1
    refresh_list_rows()
    return False


def handle_scrolls(point):
    """Handle scroll-arrow taps. Returns True if a scroll was consumed."""
    if touched_scroll_up(point):
        if list_scroll[0] > 0:
            list_scroll[0] -= 1
            refresh_list_rows()
        return True
    if touched_scroll_down(point):
        if list_scroll[0] + LIST_VISIBLE_ROWS < len(waypoints):
            list_scroll[0] += 1
            refresh_list_rows()
        return True
    return False


def handle_list_touch(point):
    """Process a tap while the list is open. Returns True if it closed."""
    # A tap outside the panel, or on the X, closes the list.
    outside = not point_in_rect(point, LIST_X, LIST_Y, LIST_W, LIST_H)
    if outside or touched_list_close(point):
        close_list()
        return True
    # Scroll arrows and trash boxes are handled in place (list stays open).
    if handle_scrolls(point):
        return False
    trash_index = touched_trash(point)
    if trash_index is not None:
        handle_trash_tap(trash_index)
        return False
    row_index = touched_row(point)
    if row_index is not None:
        if handle_row_tap(row_index):
            close_list()
            apply_mode_header(MODE_WAYPOINT)
            # The selection always applies, but without a fix the needle
            # can't point anywhere yet, so let the user know it's waiting on
            # satellites rather than appearing broken.
            if not gps.has_fix:
                header_fg.text = "No fix yet"
                header_shadow.text = "No fix yet"
                display.refresh(minimum_frames_per_second=0)
                time.sleep(1.0)
                apply_mode_header(MODE_WAYPOINT)
            return True
        return False
    # A tap on empty panel space disarms any pending delete or load.
    if armed_delete[0] != -1 or armed_select[0] != -1:
        armed_delete[0] = -1
        armed_select[0] = -1
        refresh_list_rows()
    return False


# --- Name picker modal ---
# Shown after a save when a new waypoint needs a name. A grid of preset
# name cells; tapping one assigns it to the pending waypoint. Built once,
# hidden by default. pending_save holds the (lat, lon) awaiting a name.
picker_group = displayio.Group()
pending_save = []   # [(lat, lon)] when a save is awaiting a name, else []

PICK_X = LIST_X
PICK_Y = LIST_Y
PICK_W = LIST_W
PICK_H = LIST_H
picker_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_OUTLINE),
        width=PICK_W, height=PICK_H, x=PICK_X, y=PICK_Y,
    )
)
picker_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_PANEL_BG),
        width=PICK_W - 6, height=PICK_H - PICK_TITLE_H - 3,
        x=PICK_X + 3, y=PICK_Y + PICK_TITLE_H,
    )
)
_pick_title = label.Label(
    terminalio.FONT, text="Name it", color=0xFFFFFF, scale=2,
)
_pick_title.anchor_point = (0.0, 0.5)
_pick_title.anchored_position = (PICK_X + PICK_PAD, PICK_Y + PICK_TITLE_H // 2)
picker_group.append(_pick_title)

# Grid cell geometry.
PICK_GRID_TOP = PICK_Y + PICK_TITLE_H + 4
PICK_GRID_W = PICK_W - 2 * PICK_PAD
PICK_CELL_W = (PICK_GRID_W - (PICK_COLS - 1) * PICK_CELL_GAP) // PICK_COLS
PICK_GRID_H = PICK_H - PICK_TITLE_H - 4 - PICK_PAD
PICK_CELL_H = (PICK_GRID_H - (PICK_ROWS - 1) * PICK_CELL_GAP) // PICK_ROWS


def pick_cell_xy(index):
    """Return (x, y) top-left of the picker cell at the given name index."""
    col = index % PICK_COLS
    row = index // PICK_COLS
    cell_x = PICK_X + PICK_PAD + col * (PICK_CELL_W + PICK_CELL_GAP)
    cell_y = PICK_GRID_TOP + row * (PICK_CELL_H + PICK_CELL_GAP)
    return cell_x, cell_y


pick_cell_palettes = []
for _i, _pname in enumerate(PICK_NAMES):
    _cx, _cy = pick_cell_xy(_i)
    _pick_palette = solid_palette(PICK_CELL_BG)
    pick_cell_palettes.append(_pick_palette)
    picker_group.append(
        vectorio.Rectangle(
            pixel_shader=_pick_palette,
            width=PICK_CELL_W, height=PICK_CELL_H, x=_cx, y=_cy,
        )
    )
    _plabel = label.Label(
        terminalio.FONT, text=_pname, color=PICK_CELL_TEXT, scale=2,
    )
    _plabel.anchor_point = (0.5, 0.5)
    _plabel.anchored_position = (
        _cx + PICK_CELL_W // 2, _cy + PICK_CELL_H // 2,
    )
    picker_group.append(_plabel)

picker_group.hidden = True


def open_name_picker(lat, lon, keep_active):
    """Show the picker for a pending (lat, lon) save awaiting a name.

    lat/lon None means preview mode (opened without a GPS fix): the names
    can be browsed but selecting one saves nothing. keep_active True leaves
    the current navigation target unchanged when saved (Waypoint Mode
    breadcrumb); False makes the new point active (Compass Mode).
    """
    pending_save.clear()
    pending_save.append((lat, lon, keep_active))
    # Title hints whether this will save or is just a preview (no fix).
    _pick_title.text = "Name it" if lat is not None else "Names (no fix)"
    for palette in pick_cell_palettes:
        palette[0] = PICK_CELL_BG   # reset any prior highlight
    picker_group.hidden = False


def picked_name_index(point):
    """Return the index of the tapped preset name, or None."""
    for idx in range(len(PICK_NAMES)):
        cell_x, cell_y = pick_cell_xy(idx)
        if point_in_rect(point, cell_x, cell_y, PICK_CELL_W, PICK_CELL_H):
            return idx
    return None


def handle_picker_touch(point):
    """Assign the tapped name to the pending waypoint, or cancel the save.

    A tap outside the panel cancels (no waypoint saved); a tap on a name
    cell assigns it; a tap inside the panel but not on a name does nothing.
    """
    if not point_in_rect(point, PICK_X, PICK_Y, PICK_W, PICK_H):
        # Tapped outside the picker: cancel the pending save.
        pending_save.clear()
        picker_group.hidden = True
        apply_mode_header(mode)
        return
    idx = picked_name_index(point)
    if idx is None:
        return
    # Brief gold highlight on the tapped cell for tap feedback, matching
    # the armed-row look in the waypoint list.
    pick_cell_palettes[idx][0] = LIST_ROW_ARMED
    display.refresh(minimum_frames_per_second=0)
    time.sleep(0.15)
    lat, lon, keep_active = pending_save[0]
    pending_save.clear()
    picker_group.hidden = True
    if lat is None:
        # Preview mode (no fix when the picker opened): nothing to save.
        # Let the names be browsed, then report there's no fix yet.
        apply_mode_header(mode)
        header_fg.text = "No fix yet"
        header_shadow.text = "No fix yet"
        display.refresh(minimum_frames_per_second=0)
        time.sleep(1.0)
        apply_mode_header(mode)
        return
    name = PICK_NAMES[idx]
    waypoints.append((lat, lon, name))
    # Compass-mode saves make the new point active; waypoint-mode saves keep
    # navigating the current target and just add the breadcrumb to the list.
    if not keep_active:
        active_index[0] = len(waypoints) - 1
    try:
        save_waypoints()
    except OSError:
        pass  # name still applies this session
    apply_mode_header(mode)


# --- Settings gear button (Compass Mode footer) ---
# A small grey box with a gear-like glyph; tapping it opens the settings
# panel. Only shown in Compass Mode.
gear_group = displayio.Group()
gear_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(0xC8C8C8),
        width=GEAR_SIZE, height=GEAR_SIZE, x=GEAR_X, y=GEAR_Y,
    )
)
# Gear glyph: a dark ring (outer circle minus inner) approximated with a
# filled dark circle and a light center, plus four nub squares.
_GEAR_CX = GEAR_X + GEAR_SIZE // 2
_GEAR_CY = GEAR_Y + GEAR_SIZE // 2
gear_group.append(
    vectorio.Circle(
        pixel_shader=solid_palette(0x303030), radius=9,
        x=_GEAR_CX, y=_GEAR_CY,
    )
)
gear_group.append(
    vectorio.Circle(
        pixel_shader=solid_palette(0xC8C8C8), radius=4,
        x=_GEAR_CX, y=_GEAR_CY,
    )
)


def touched_gear(point):
    """True if the touch point is on the settings gear button."""
    return point_in_rect(point, GEAR_X, GEAR_Y, GEAR_SIZE, GEAR_SIZE)


# --- Settings panel (scrolling list) ---
# Five items shown 4-at-a-time with up/down scroll arrows, styled like the
# waypoint list. Order: Theme, Marine Mode, Units, Declination,
# Recalibrate (last, so the destructive action is out of the way). Each
# row is a uniform cell with a left label and a right state value. The
# Declination row adjusts by tapping its left (West) or right (East) half,
# with small chevron hints. A "?" icon in the title opens an info guide.
settings_group = displayio.Group()
settings_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_OUTLINE),
        width=SET_W, height=SET_H, x=SET_X, y=SET_Y,
    )
)
settings_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_PANEL_BG),
        width=SET_W - 6, height=SET_H - SET_TITLE_H - 3,
        x=SET_X + 3, y=SET_Y + SET_TITLE_H,
    )
)
_set_title = label.Label(
    terminalio.FONT, text="Settings", color=0xFFFFFF, scale=2,
)
_set_title.anchor_point = (0.0, 0.5)
_set_title.anchored_position = (SET_X + SET_PAD, SET_Y + SET_TITLE_H // 2)
settings_group.append(_set_title)

# Info "?" button and Close "X" button in the title bar (X far right, ?
# just left of it).
SET_CLOSE_X = SET_X + SET_W - SET_PAD - LIST_CLOSE_SIZE
SET_CLOSE_Y = SET_Y + (SET_TITLE_H - LIST_CLOSE_SIZE) // 2
SET_INFO_X = SET_CLOSE_X - LIST_CLOSE_SIZE - 14
SET_INFO_Y = SET_CLOSE_Y
_set_info = label.Label(
    terminalio.FONT, text="?", color=0xFFFFFF, scale=2,
)
_set_info.anchor_point = (0.5, 0.5)
_set_info.anchored_position = (
    SET_INFO_X + LIST_CLOSE_SIZE // 2, SET_INFO_Y + LIST_CLOSE_SIZE // 2,
)
settings_group.append(_set_info)
_set_close = label.Label(
    terminalio.FONT, text="X", color=0xFFFFFF, scale=2,
)
_set_close.anchor_point = (0.5, 0.5)
_set_close.anchored_position = (
    SET_CLOSE_X + LIST_CLOSE_SIZE // 2, SET_CLOSE_Y + LIST_CLOSE_SIZE // 2,
)
settings_group.append(_set_close)

# Setting item identifiers (also the order shown in the list).
SET_THEME = 0
SET_MARINE = 1
SET_UNITS = 2
SET_DECL = 3
SET_ROTATE = 4
SET_RECAL = 5
SETTING_LABELS = ("Theme", "Marine Mode", "Units", "Declination",
                  "Rotation", "Recalibrate")
SETTING_COUNT = len(SETTING_LABELS)

# List geometry, reusing the waypoint-list metrics.
SET_VISIBLE_ROWS = 4
SET_LIST_ROW_H = 32
SET_LIST_ROW_GAP = 3
SET_ROWS_TOP = SET_Y + SET_TITLE_H + 5
SET_ROW_X = SET_X + SET_PAD
SET_ARROW_COL_W = 30
SET_ROW_W = SET_W - 2 * SET_PAD - SET_ARROW_COL_W
settings_scroll = [0]   # index of the first visible setting
settings_armed = [-1]   # item index armed for confirm, or -1 = none


def set_list_row_y(row_i):
    """Top y of the visible settings row at position row_i."""
    return SET_ROWS_TOP + row_i * (SET_LIST_ROW_H + SET_LIST_ROW_GAP)


# Pre-create the visible row widgets (cell + left label + right state, plus
# edge chevrons used only by the Declination row to show its < / > taps).
set_row_palettes = []
set_row_labels = []
set_row_states = []
set_row_chevrons = []   # (left_chevron, right_chevron) per visible row
for _sr in range(SET_VISIBLE_ROWS):
    _sy = set_list_row_y(_sr)
    _sp = solid_palette(LIST_ROW_BG)
    set_row_palettes.append(_sp)
    settings_group.append(
        vectorio.Rectangle(
            pixel_shader=_sp, width=SET_ROW_W, height=SET_LIST_ROW_H,
            x=SET_ROW_X, y=_sy,
        )
    )
    _sl = label.Label(
        terminalio.FONT, text="", color=LIST_ROW_TEXT, scale=2,
    )
    _sl.anchor_point = (0.0, 0.5)
    _sl.anchored_position = (SET_ROW_X + 8, _sy + SET_LIST_ROW_H // 2)
    settings_group.append(_sl)
    set_row_labels.append(_sl)
    _ss = label.Label(
        terminalio.FONT, text="", color=LIST_ROW_TEXT, scale=2,
    )
    _ss.anchor_point = (1.0, 0.5)
    _ss.anchored_position = (
        SET_ROW_X + SET_ROW_W - 10, _sy + SET_LIST_ROW_H // 2,
    )
    settings_group.append(_ss)
    set_row_states.append(_ss)
    # Edge chevrons (hidden unless this row shows the Declination item).
    _lc = label.Label(terminalio.FONT, text="<", color=LIST_ROW_TEXT, scale=2)
    _lc.anchor_point = (0.0, 0.5)
    _lc.anchored_position = (SET_ROW_X + 8, _sy + SET_LIST_ROW_H // 2)
    settings_group.append(_lc)
    _rc = label.Label(terminalio.FONT, text=">", color=LIST_ROW_TEXT, scale=2)
    _rc.anchor_point = (1.0, 0.5)
    _rc.anchored_position = (
        SET_ROW_X + SET_ROW_W - 10, _sy + SET_LIST_ROW_H // 2,
    )
    settings_group.append(_rc)
    _lc.hidden = True
    _rc.hidden = True
    set_row_chevrons.append((_lc, _rc))

# Scroll arrows (reuse the waypoint-list arrow helper and metrics).
SET_ARROW_X = SET_X + SET_W - SET_PAD - 15
_SET_ARROW_UP_Y = SET_ROWS_TOP + 10
_SET_ARROW_DN_Y = set_list_row_y(SET_VISIBLE_ROWS - 1) + SET_LIST_ROW_H - 10


def _add_set_arrow(cx, cy, pointing_up):
    """Append a grey scroll triangle with shadow to settings; return (s,fg)."""
    shadow = vectorio.Polygon(
        pixel_shader=solid_palette(0x101010),
        points=_triangle_points(
            cx + 1, cy + 1, LIST_ARROW_HALF_W, LIST_ARROW_HEIGHT, pointing_up
        ),
        x=0, y=0,
    )
    fg = vectorio.Polygon(
        pixel_shader=solid_palette(LIST_ARROW),
        points=_triangle_points(
            cx, cy, LIST_ARROW_HALF_W, LIST_ARROW_HEIGHT, pointing_up
        ),
        x=0, y=0,
    )
    settings_group.append(shadow)
    settings_group.append(fg)
    return shadow, fg


_set_arrow_up = _add_set_arrow(SET_ARROW_X, _SET_ARROW_UP_Y, True)
_set_arrow_dn = _add_set_arrow(SET_ARROW_X, _SET_ARROW_DN_Y, False)

settings_group.hidden = True


def declination_text():
    """Human-readable declination, e.g. '6 W', '0', '10 E'."""
    deg = DECLINATION_OPTIONS[declination_index[0]]
    if deg > 0:
        return f"{deg} E"
    if deg < 0:
        return f"{-deg} W"
    return "0"


def setting_state_text(item):
    """Return the right-aligned state text for a setting item."""
    if item == SET_THEME:
        return "Light" if theme_index[0] == 1 else "Dark"
    if item == SET_MARINE:
        return "ON" if marine_mode[0] else "OFF"
    if item == SET_UNITS:
        return "mi" if units_imperial[0] else "km"
    if item == SET_DECL:
        return declination_text()
    if item == SET_ROTATE:
        return "180" if rotation_flipped[0] else "0"
    return ""   # Recalibrate has no state value


def refresh_settings():
    """Populate the visible settings rows from the scroll position."""
    for row_i in range(SET_VISIBLE_ROWS):
        item = settings_scroll[0] + row_i
        left_chevron, right_chevron = set_row_chevrons[row_i]
        row_y = set_list_row_y(row_i)
        mid_y = row_y + SET_LIST_ROW_H // 2
        is_decl = item == SET_DECL
        # The Declination row shows < and > at its edges; its label and value
        # shift inward to clear them. Other rows hide the chevrons and use
        # the normal label/value positions.
        left_chevron.hidden = not is_decl
        right_chevron.hidden = not is_decl
        inset = 26 if is_decl else 0
        set_row_labels[row_i].anchored_position = (SET_ROW_X + 8 + inset, mid_y)
        set_row_states[row_i].anchored_position = (
            SET_ROW_X + SET_ROW_W - 10 - inset, mid_y
        )
        if item < SETTING_COUNT:
            set_row_labels[row_i].hidden = False
            set_row_states[row_i].hidden = False
            armed = item == settings_armed[0]
            if item == SET_RECAL and armed:
                set_row_palettes[row_i][0] = LIST_TRASH_ARMED   # red alert
                set_row_labels[row_i].text = "Sure?"
            elif armed:
                set_row_palettes[row_i][0] = LIST_ROW_ARMED     # gold
                set_row_labels[row_i].text = SETTING_LABELS[item]
            else:
                set_row_palettes[row_i][0] = LIST_ROW_BG
                set_row_labels[row_i].text = SETTING_LABELS[item]
            set_row_states[row_i].text = setting_state_text(item)
        else:
            set_row_labels[row_i].hidden = True
            set_row_states[row_i].hidden = True
            left_chevron.hidden = True
            right_chevron.hidden = True
            set_row_palettes[row_i][0] = LIST_PANEL_BG
            set_row_labels[row_i].text = ""
            set_row_states[row_i].text = ""
    can_up = settings_scroll[0] > 0
    can_down = settings_scroll[0] + SET_VISIBLE_ROWS < SETTING_COUNT
    _set_arrow_up[0].hidden = not can_up
    _set_arrow_up[1].hidden = not can_up
    _set_arrow_dn[0].hidden = not can_down
    _set_arrow_dn[1].hidden = not can_down


def open_settings():
    """Show the settings panel over the dial."""
    settings_scroll[0] = 0
    settings_armed[0] = -1
    refresh_settings()
    settings_group.hidden = False


def close_settings():
    """Hide the settings panel."""
    settings_group.hidden = True


def touched_set_close(point):
    """True if the touch is on the settings close (X) button."""
    return point_in_rect(
        point, SET_CLOSE_X, SET_CLOSE_Y, LIST_CLOSE_SIZE, LIST_CLOSE_SIZE
    )


def touched_set_info(point):
    """True if the touch is on the info (?) button."""
    return point_in_rect(
        point, SET_INFO_X, SET_INFO_Y, LIST_CLOSE_SIZE, LIST_CLOSE_SIZE
    )


def touched_set_scroll_up(point):
    """True if the up scroll arrow is tapped and active."""
    if _set_arrow_up[1].hidden:
        return False
    return point_in_rect(
        point, SET_ARROW_X - LIST_ARROW_HIT_W // 2,
        _SET_ARROW_UP_Y - LIST_ARROW_HIT_H // 2,
        LIST_ARROW_HIT_W, LIST_ARROW_HIT_H,
    )


def touched_set_scroll_down(point):
    """True if the down scroll arrow is tapped and active."""
    if _set_arrow_dn[1].hidden:
        return False
    return point_in_rect(
        point, SET_ARROW_X - LIST_ARROW_HIT_W // 2,
        _SET_ARROW_DN_Y - LIST_ARROW_HIT_H // 2,
        LIST_ARROW_HIT_W, LIST_ARROW_HIT_H,
    )


def touched_setting_row(point):
    """Return (item, row_i) for a tapped settings row, or (None, None)."""
    for row_i in range(SET_VISIBLE_ROWS):
        item = settings_scroll[0] + row_i
        if item >= SETTING_COUNT:
            break
        if point_in_rect(
            point, SET_ROW_X, set_list_row_y(row_i), SET_ROW_W, SET_LIST_ROW_H
        ):
            return item, row_i
    return None, None


def adjust_declination(increase):
    """Step the declination toward East (increase) or West (decrease)."""
    # DECLINATION_OPTIONS runs East(+) to West(-); index 0 is most East,
    # so increasing declination (more East) means a lower index.
    if increase and declination_index[0] > 0:
        declination_index[0] -= 1
    elif not increase and declination_index[0] < len(DECLINATION_OPTIONS) - 1:
        declination_index[0] += 1
    microcontroller.nvm[NVM_DECLINATION_BYTE] = declination_index[0]


def trigger_recalibration():
    """Clear the saved calibration and hand off to calibration.py.

    Queues the boot.py NVM flags to delete settings.toml, then sets the
    next code file to calibration.py and reloads. boot.py runs on the
    reload, clears settings.toml, and calibration.py launches its guided
    setup. When calibration finishes it hands control back to code.py.
    No file renaming and no computer needed - works in the field.
    """
    microcontroller.nvm[0] = 1   # remount-writable flag for boot.py
    microcontroller.nvm[1] = 2   # action 2 = clear settings.toml
    _set_title.text = "Recalibrating..."
    display.refresh(minimum_frames_per_second=0)
    time.sleep(0.8)
    supervisor.set_next_code_file("calibration.py")
    supervisor.reload()


def commit_setting(item):
    """Apply a confirmed toggle for Theme/Marine/Units/Rotation and persist."""
    if item == SET_THEME:
        toggle_theme()
    elif item == SET_MARINE:
        marine_mode[0] = not marine_mode[0]
        microcontroller.nvm[NVM_MARINE_BYTE] = 1 if marine_mode[0] else 0
    elif item == SET_UNITS:
        units_imperial[0] = not units_imperial[0]
        microcontroller.nvm[NVM_UNITS_BYTE] = 1 if units_imperial[0] else 0
    elif item == SET_ROTATE:
        rotation_flipped[0] = not rotation_flipped[0]
        microcontroller.nvm[NVM_ROTATION_BYTE] = 1 if rotation_flipped[0] else 0
        apply_rotation()


def handle_armed_row(item, point):
    """Handle a tap on a row that is already armed (awaiting confirm).

    Declination stays armed so < / > can step repeatedly; the others
    commit once and disarm. Recalibrate reboots (never returns).
    """
    if item == SET_RECAL:
        trigger_recalibration()   # does not return (reboots)
    elif item == SET_DECL:
        # Armed declination: < / > step freely without re-arming, so a
        # value can be dialed in quickly. Row stays armed until the user
        # taps elsewhere.
        adjust_declination(point[0] >= SET_ROW_X + SET_ROW_W // 2)
        refresh_settings()
    else:
        commit_setting(item)
        settings_armed[0] = -1
        refresh_settings()


def handle_settings_touch(point):
    """Process a tap while settings is open. Returns True if it closed."""
    outside = not point_in_rect(point, SET_X, SET_Y, SET_W, SET_H)
    if outside or touched_set_close(point):
        close_settings()
        return True
    if touched_set_info(point):
        settings_armed[0] = -1
        open_info()
        return False
    if touched_set_scroll_up(point):
        if settings_scroll[0] > 0:
            settings_scroll[0] -= 1
            settings_armed[0] = -1
            refresh_settings()
        return False
    if touched_set_scroll_down(point):
        if settings_scroll[0] + SET_VISIBLE_ROWS < SETTING_COUNT:
            settings_scroll[0] += 1
            settings_armed[0] = -1
            refresh_settings()
        return False
    item, _row_i = touched_setting_row(point)
    if item is None:
        # Tap on empty panel space disarms any pending selection.
        if settings_armed[0] != -1:
            settings_armed[0] = -1
            refresh_settings()
        return False
    if settings_armed[0] == item:
        handle_armed_row(item, point)        # second tap: confirm / step
    else:
        settings_armed[0] = item             # first tap: arm this row
        refresh_settings()
    return False


# --- Info guide overlay ---
# A full-panel help screen reached from the settings "?" button. Covers
# the boot modes, button actions, and magnetic declination, with a simple
# E/W chevron diagram standing in for the isogonic map. Tap anywhere to
# close back to settings.
info_group = displayio.Group()
info_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_OUTLINE),
        width=SET_W, height=SET_H, x=SET_X, y=SET_Y,
    )
)
info_group.append(
    vectorio.Rectangle(
        pixel_shader=solid_palette(LIST_PANEL_BG),
        width=SET_W - 6, height=SET_H - SET_TITLE_H - 3,
        x=SET_X + 3, y=SET_Y + SET_TITLE_H,
    )
)
_info_title = label.Label(
    terminalio.FONT, text="Guide", color=0xFFFFFF, scale=2,
)
_info_title.anchor_point = (0.0, 0.5)
_info_title.anchored_position = (SET_X + SET_PAD, SET_Y + SET_TITLE_H // 2)
info_group.append(_info_title)
_info_close = label.Label(
    terminalio.FONT, text="X", color=0xFFFFFF, scale=2,
)
_info_close.anchor_point = (0.5, 0.5)
_info_close.anchored_position = (
    SET_CLOSE_X + LIST_CLOSE_SIZE // 2, SET_CLOSE_Y + LIST_CLOSE_SIZE // 2,
)
info_group.append(_info_close)

# Content: a "Button" section and a "Declination" section, each with a
# gold header (h1-style) and short body lines, then a compact declination
# diagram. Sized to fit the panel without scrolling.
INFO_HEADER = 0xFFAA00   # gold, reads well on the dark panel
INFO_BODY = 0xE0E0E0
INFO_X = SET_X + SET_PAD
_info_cursor = [SET_Y + SET_TITLE_H + 12]   # running y for stacked lines


def _add_info_line(text, color, scale, step):
    """Append a left-aligned info line at the running y, then advance y."""
    line = label.Label(terminalio.FONT, text=text, color=color, scale=scale)
    line.anchor_point = (0.0, 0.5)
    line.anchored_position = (INFO_X, _info_cursor[0])
    info_group.append(line)
    _info_cursor[0] += step


_add_info_line("Button", INFO_HEADER, 2, 18)
_add_info_line("Press: switch mode", INFO_BODY, 1, 13)
_add_info_line("Hold: save waypoint", INFO_BODY, 1, 20)
_add_info_line("Declination", INFO_HEADER, 2, 18)
_add_info_line("Angle from true north", INFO_BODY, 1, 13)
_add_info_line("Tap < or > to set yours", INFO_BODY, 1, 18)
_add_info_line("Tap below for your area's value", INFO_HEADER, 1, 0)

# The text lines above are page 1. The declination map is page 2, shown as
# its own full image. info_text_group holds the page-1 labels (everything
# appended to info_group so far besides the panel frame and title); we
# track page state and toggle the map's visibility.
info_page = [0]   # 0 = text page, 1 = map page

# Map page: load the declination map BMP from CIRCUITPY and center it in
# the panel. OnDiskBitmap needs an uncompressed BMP (this one is 8-bit
# uncompressed, 321x170). If the file is missing, the map page is skipped.
DECL_MAP_FILE = "/d-map.bmp"
map_tilegrid = None
try:
    _map_bmp = displayio.OnDiskBitmap(DECL_MAP_FILE)
    _map_x = SET_X + (SET_W - _map_bmp.width) // 2
    _map_y = SET_Y + SET_TITLE_H + (SET_H - SET_TITLE_H - _map_bmp.height) // 2
    map_tilegrid = displayio.TileGrid(
        _map_bmp, pixel_shader=_map_bmp.pixel_shader, x=_map_x, y=_map_y,
    )
    info_group.append(map_tilegrid)
    map_tilegrid.hidden = True
except OSError:
    map_tilegrid = None   # file not on CIRCUITPY yet; text page still works

# The page-1 text labels are all the info_group children after the frame
# (outline rect, bg rect), title, and close label (indices 0-3) up to (but
# not including) the map tilegrid. Track that slice so we can hide/show it
# while keeping the frame, title, and close X visible on both pages.
_INFO_TEXT_START = 4
_info_text_end = len(info_group)
if map_tilegrid is not None:
    _info_text_end -= 1   # exclude the map tilegrid


def _set_info_page(page):
    """Show page 0 (text) or page 1 (map), toggling child visibility."""
    info_page[0] = page
    show_map = page == 1 and map_tilegrid is not None
    for idx in range(_INFO_TEXT_START, _info_text_end):
        info_group[idx].hidden = show_map
    if map_tilegrid is not None:
        map_tilegrid.hidden = not show_map
    _info_title.text = "Map" if show_map else "Guide"


info_group.hidden = True


def open_info():
    """Show the info guide (text page first) over the settings panel."""
    _set_info_page(0)
    info_group.hidden = False


def handle_info_touch(point):
    """Tap the X or outside the panel returns to settings; tap inside the
    panel flips between the text and map pages (when a map is loaded)."""
    outside = not point_in_rect(point, SET_X, SET_Y, SET_W, SET_H)
    if outside or touched_set_close(point):
        info_group.hidden = True   # back to the settings panel beneath
        return False
    # Inside the panel: flip text/map pages if a map is available.
    if map_tilegrid is not None:
        _set_info_page(1 - info_page[0])
    return False


# Assemble the scene (z-order: static, needle, text, battery, inventory)
root.append(static_group)
root.append(needle_group)
root.append(header_shadow)
root.append(header_fg)
root.append(heading_num_shadow)
root.append(heading_num_fg)
root.append(battery_group)
root.append(inventory_group)
root.append(gear_group)
root.append(list_group)
root.append(picker_group)
root.append(settings_group)
root.append(info_group)

# Hide the battery indicator entirely if no fuel gauge is mounted yet.
battery_group.hidden = not battery_present

# Apply the loaded theme to everything now that the UI exists.
apply_theme()

# --- Phase routing ---
# If there is no calibration yet, hand off to the calibration program
# rather than dead-ending. supervisor runs calibration.py on the reload;
# when it finishes it hands control back to code.py. This is what makes
# field recalibration work with no computer or file renaming.
cal = load_calibration()
if cal is None:
    print("No calibration found - launching calibration.py")
    supervisor.set_next_code_file("calibration.py")
    supervisor.reload()
    # reload() is not instant; stop here so nothing runs with cal=None.
    while True:
        time.sleep(0.1)

heading_offset = cal[6]
load_waypoints()  # restore any saved waypoint from a previous session
print("Dial preview running.")
print(f"Heading offset: {heading_offset:0.2f} deg")
print("Tap: switch mode.  Hold 1.5s: save waypoint.  Hold 3.5s: theme.")

mode = MODE_COMPASS
last_needle_update = 0.0
last_text_update = 0.0
last_gps_update = 0.0
last_battery_update = 0.0
last_footer_text = [""]   # last footer string, to skip no-op text updates
smoothed_heading = [None]  # low-pass filtered heading (None until first read)
drawn_needle_angle = [None]  # last angle actually drawn, for the deadband
touch_was_down = [False]  # tracks touch state across polls for tap edges
update_battery()  # initial read so the icon is correct on first frame


def apply_mode_header(active_mode):
    """Update the header label and inventory button for the active mode."""
    if active_mode == MODE_WAYPOINT:
        current = active_waypoint()
        text = current[2] if current is not None else "Waypoint"
    else:
        text = MODE_NAMES[MODE_COMPASS]
    header_fg.text = text
    header_shadow.text = text
    # The inventory/list button only applies in Waypoint Mode; the settings
    # gear only in Compass Mode. Each is hidden in the other to keep the
    # views clean.
    inventory_group.hidden = active_mode != MODE_WAYPOINT
    gear_group.hidden = active_mode != MODE_COMPASS


# Cached navigation state, refreshed only when GPS data is polled (slow),
# then used every frame to compute the needle angle against the live
# heading (fast). nav_state[0] is one of "searching", "no_waypoint",
# "navigating"; the rest hold the latest bearing/distance/sat values.
nav_state = ["searching", 0.0, 0.0, 0]  # state, mag_bearing, dist_m, sats


def update_nav_target():
    """Refresh cached navigation state from the GPS. Call when GPS polls.

    Sets nav_state in place. Heading is NOT used here; the needle angle is
    derived each frame from the cached bearing and the live heading so the
    needle stays smooth even though GPS only updates a few times a second.
    """
    if not gps.has_fix:
        nav_state[0] = "searching"
        nav_state[3] = gps.satellites if gps.satellites is not None else 0
        return
    waypoint = active_waypoint()
    if waypoint is None:
        nav_state[0] = "no_waypoint"
        return
    dist = haversine_distance(
        gps.latitude, gps.longitude, waypoint[0], waypoint[1]
    )
    true_bearing = initial_bearing(
        gps.latitude, gps.longitude, waypoint[0], waypoint[1]
    )
    nav_state[0] = "navigating"
    nav_state[1] = (true_bearing - MAGNETIC_DECLINATION) % 360
    nav_state[2] = dist


def waypoint_needle_and_footer(heading):
    """Return (needle_angle, footer) for Waypoint Mode using cached nav.

    Cheap to call every frame: only the needle angle depends on the live
    heading, so the needle tracks head movement smoothly between GPS polls.
    """
    state = nav_state[0]
    if state == "searching":
        spin = (time.monotonic() * 60.0) % 360  # smooth idle rotation
        return spin, f"sats {nav_state[3]}..."
    if state == "no_waypoint":
        return (0.0 - heading) % 360, "No waypoint"
    mag_bearing = nav_state[1]
    needle = (mag_bearing - heading) % 360
    # The needle already shows direction, so the footer just shows distance
    # (the key "are we close?" readout) - kept short to clear the corner
    # button and stay kid-friendly.
    return needle, format_distance(nav_state[2])


def handle_save_waypoint():
    """Open the name picker to capture the current fix, or preview it.

    With a fix, the picker assigns a name and the waypoint is saved. Without
    a fix the picker still opens so the names can be browsed (a preview of
    what locations can be called), but tapping one saves nothing and just
    reports there is no fix yet. A full list is the one hard block.
    """
    if len(waypoints) >= MAX_WAYPOINTS:
        header_fg.text = "List full"
        header_shadow.text = "List full"
        display.refresh(minimum_frames_per_second=0)
        time.sleep(1.0)
        return
    if not gps.has_fix:
        # Preview mode: open the picker with no coordinates. Selecting a name
        # won't save (handled in handle_picker_touch); it alerts instead.
        open_name_picker(None, None, keep_active=mode == MODE_WAYPOINT)
        return
    # Capture the fix now and let the picker assign the name. In Waypoint
    # Mode keep the current target active (breadcrumb save); in Compass Mode
    # make the new point active.
    open_name_picker(gps.latitude, gps.longitude,
                     keep_active=mode == MODE_WAYPOINT)


apply_mode_header(mode)

while True:
    now = time.monotonic()
    # Set True by anything that changes the screen this iteration; the
    # single display.refresh() at the bottom fires only when it's True.
    needs_refresh = False

    # GPS reads are expensive: the adafruit_gps GtopI2C driver reads one
    # byte per I2C transaction, so one NMEA sentence is ~70 locked
    # transactions (~300-500 ms). Position only changes at 1 Hz for walking,
    # so read once per second instead of 4x - the unavoidable stall then
    # happens 4x less often. (A faster fix would need a custom bulk-I2C
    # reader, which the stock library does not provide.)
    if now - last_gps_update >= 1.0:
        gps.update()
        update_nav_target()
        last_gps_update = now

    event = poll_button()

    # Touch: route to whichever overlay is open (picker, list, settings),
    # else to the mode's button (inventory in Waypoint, gear in Compass).
    # Acts once per tap on the press edge.
    touch_point = read_touch()
    if touch_point is not None and not touch_was_down[0]:
        touch_was_down[0] = True
        if not info_group.hidden:
            handle_info_touch(touch_point)
        elif not picker_group.hidden:
            handle_picker_touch(touch_point)
        elif not list_group.hidden:
            handle_list_touch(touch_point)
        elif not settings_group.hidden:
            handle_settings_touch(touch_point)
        elif mode == MODE_WAYPOINT and touched_inventory_button(touch_point):
            open_list()
        elif mode == MODE_COMPASS and touched_gear(touch_point):
            open_settings()
        needs_refresh = True   # a tap may have changed an overlay/menu
    elif touch_point is None:
        touch_was_down[0] = False

    # While an overlay is open, the physical button closes it (matching the
    # tap-outside behavior) rather than switching modes or saving behind it.
    # A short press closes the topmost overlay; holds are ignored so a
    # hold-to-save/theme can't fire behind a menu.
    any_overlay = not (list_group.hidden and picker_group.hidden
                       and settings_group.hidden and info_group.hidden)
    if any_overlay:
        if event == "short":
            if not info_group.hidden:
                info_group.hidden = True          # info closes back to settings
            elif not picker_group.hidden:
                pending_save.clear()               # cancel pending save
                picker_group.hidden = True
                apply_mode_header(mode)
            elif not settings_group.hidden:
                close_settings()
            elif not list_group.hidden:
                close_list()
            needs_refresh = True
        event = "none"   # never fall through to mode-switch/save while open

    if event == "short":
        mode = MODE_WAYPOINT if mode == MODE_COMPASS else MODE_COMPASS
        apply_mode_header(mode)
        needs_refresh = True
    elif event == "enter_save":
        # Crossed the save threshold while holding; show what release does.
        header_fg.text = "Save?"
        header_shadow.text = "Save?"
        needs_refresh = True
    elif event == "enter_theme":
        # Kept holding into the theme tier; show what release does now.
        header_fg.text = "Theme?"
        header_shadow.text = "Theme?"
        needs_refresh = True
    elif event == "save":
        # Hold-to-save works in both modes. In Compass Mode the new point
        # becomes the active target (you saved it to go to it). In Waypoint
        # Mode it's saved as a breadcrumb without redirecting the navigation
        # you're already following - select it from the list to switch.
        handle_save_waypoint()
        apply_mode_header(mode)
        needs_refresh = True
    elif event == "theme":
        toggle_theme()
        theme_name = "Light" if theme_index[0] == 1 else "Dark"
        header_fg.text = theme_name
        header_shadow.text = theme_name
        display.refresh(minimum_frames_per_second=0)
        time.sleep(0.6)
        apply_mode_header(mode)
        needs_refresh = True

    # Sensor reads (I2C) and heading math are the loop's most expensive
    # work, so do them only when we actually update the needle (30 Hz)
    # rather than every ~5 ms loop.
    if now - last_needle_update >= 0.033:  # 30 Hz
        mag_cal = read_mag_calibrated(cal)
        accel = read_accel()
        # corrected_heading is magnetic; add declination (E positive) to
        # get true heading so compass and waypoint bearings read true north.
        declination = DECLINATION_OPTIONS[declination_index[0]]
        raw_heading = (
            corrected_heading(mag_cal, accel, heading_offset) + declination
        ) % 360
        # Low-pass the heading so magnetometer noise doesn't make the needle
        # twitch. Jitter both looks bad and forces a large dirty region
        # (slow refresh), so smoothing helps the look and the frame rate.
        smoothed_heading[0] = smooth_heading(
            raw_heading, smoothed_heading[0], HEADING_SMOOTHING
        )
        heading_deg = smoothed_heading[0]

        # When the case is built button-at-bottom, the display is flipped
        # 180 and the IMU is physically turned 180 with it, so the same
        # facing reads a heading 180 off. Correct it so N still reads N.
        if rotation_flipped[0]:
            heading_deg = (heading_deg + 180) % 360

        if mode == MODE_WAYPOINT:
            needle_angle, footer_text = waypoint_needle_and_footer(heading_deg)
        else:
            # Marine mode: needle always points to true north. Intuitive
            # mode (default): needle points at the cardinal you face.
            if marine_mode[0]:
                needle_angle = (0.0 - heading_deg) % 360
            else:
                needle_angle = heading_deg
            footer_text = (
                f"{heading_deg:3.0f} deg  {cardinal_from_heading(heading_deg)}"
            )

        # Only redraw the needle when it actually moved beyond a small
        # deadband. Holding still then does almost no refreshing (the needle
        # bitmap clear+rotozoom and the SPI push are the costly steps), and
        # tiny sub-degree wobble is ignored.
        if (drawn_needle_angle[0] is None
                or abs(angle_diff(needle_angle, drawn_needle_angle[0]))
                >= NEEDLE_DEADBAND_DEG):
            set_needle_heading(needle_angle)
            drawn_needle_angle[0] = needle_angle
            needs_refresh = True
        last_needle_update = now

        if now - last_text_update >= 0.2:  # 5 Hz text update
            # Only touch the labels when the string actually changed. The
            # footer is far from the needle, so a footer change forces a
            # refresh spanning both (the ~158 ms spikes); skipping no-op
            # updates keeps most frames to the needle-only ~76 ms path.
            if footer_text != last_footer_text[0]:
                heading_num_fg.text = footer_text
                heading_num_shadow.text = footer_text
                last_footer_text[0] = footer_text
                needs_refresh = True
            last_text_update = now

    if now - last_battery_update >= 10.0:  # battery changes slowly
        update_battery()
        last_battery_update = now
        needs_refresh = True

    # Refresh only when something actually changed (at most the 30 Hz needle
    # rate), not every ~5 ms loop. Refreshing every loop was pushing the SPI
    # display ~200x/sec for no reason, throttling the whole loop.
    if needs_refresh:
        display.refresh(minimum_frames_per_second=0)

    # Collect garbage at a controlled point each loop so GC pauses stay
    # small and regular instead of building up and firing mid-render (which
    # showed as the needle going smooth-then-choppy and laggy taps).
    gc.collect()

    time.sleep(0.005)
