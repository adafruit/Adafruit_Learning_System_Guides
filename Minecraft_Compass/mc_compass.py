# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Sensors, heading math, and storage for the Minecraft Compass.

This module owns the sensor-side runtime state (the waypoint list, the
active target, and the persisted setting flags) and the math that turns raw
IMU/GPS data into a heading and navigation. It holds the hardware objects in
module-level handles that code.py fills in by calling setup() once after it
creates them, which keeps all hardware construction in code.py and avoids
circular imports (this module never imports the UI).

State lists use the one-element-list idiom (e.g. active_index[0]) so other
modules can both read and mutate them through the shared reference.
"""

import json
import math
import os
import time
import microcontroller

from mc_config import (
    ACCEL_SMOOTHING, CARDINALS, DECLINATION_DEFAULT_INDEX, DECLINATION_OPTIONS,
    EARTH_RADIUS_M, EXTRA_LONG_PRESS_S, LONG_PRESS_S, MAX_WAYPOINTS, MODE_COMPASS,
    NVM_DECLINATION_BYTE, NVM_MARINE_BYTE, NVM_ROTATION_BYTE, NVM_THEME_BYTE,
    NVM_UNITS_BYTE, THEMES, WAYPOINTS_FILE,
)

# Hardware handles, filled in by setup() from code.py. A plain dict (rather
# than module globals) keeps them writable from setup() without a global
# statement; other modules read them as hw["imu"], hw["gps"], etc.
hw = {
    "imu": None,
    "mag": None,
    "gps": None,
    "battery": None,
    "battery_present": False,
    "button": None,
}

# --- Shared runtime state (read and mutated across modules) ---
waypoints = []        # list of (lat, lon, name)
active_index = [0]    # index into waypoints of the active nav target
mode = [MODE_COMPASS]  # current view: MODE_COMPASS or MODE_WAYPOINT
theme_index = [1]     # index into THEMES (set properly in setup)
marine_mode = [False]
units_imperial = [False]
declination_index = [DECLINATION_DEFAULT_INDEX]
rotation_flipped = [False]


def setup(imu_obj, mag_obj, gps_obj, battery_obj, button_obj):
    """Inject the hardware objects and load persisted settings from NVM.

    Called once by code.py after it has constructed the sensors. Loads the
    saved theme, marine/units/declination/rotation settings, and the saved
    waypoints so the device comes up where it left off.
    """
    hw["imu"] = imu_obj
    hw["mag"] = mag_obj
    hw["gps"] = gps_obj
    hw["battery"] = battery_obj
    hw["battery_present"] = battery_obj is not None
    hw["button"] = button_obj
    theme_index[0] = load_theme_index()
    marine_mode[0] = load_marine_mode()
    units_imperial[0] = load_units_imperial()
    declination_index[0] = load_declination_index()
    rotation_flipped[0] = load_rotation_flipped()
    load_waypoints()


# --- Pure math helpers ---

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


def _planar_mag(mag_vec, roll, pitch):
    """Project the magnetometer vector into the horizontal plane."""
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


# --- Calibration + waypoint storage ---

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


# --- Persisted settings (NVM) ---

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


# --- Live sensor reads ---

_accel_smooth = [0.0, 0.0, 0.0]
_accel_ready = [False]


def read_accel():
    """Read the accelerometer, correcting for the IMU's 180-deg X mounting.

    The board mounts the LSM6DSOX rotated 180 about X, so ay and az are
    negated; ax is unchanged.
    """
    a_x, a_y, a_z = hw["imu"].acceleration
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
    m_x, m_y, m_z = hw["mag"].magnetic
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
    hw["button"].update()

    if hw["button"].fell:
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

    if hw["button"].rose and _press_state[0] is not None:
        tier = _hold_tier[0]
        _press_state[0] = None
        _hold_tier[0] = 0
        result = ("short", "save", "theme")[tier]

    return result
