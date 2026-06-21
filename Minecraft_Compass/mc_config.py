# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Configuration and tunable constants for the Minecraft Compass.

Everything you are likely to customize lives in the EDITABLE SETTINGS block
at the top: the preset waypoint names, magnetic declination, the feel of the
needle, and the hardware-fit offsets for your printed case. The INTERNAL
LAYOUT block below holds colors, geometry, and styling you can change but
usually will not need to.

This module has no hardware dependencies (except the button pin), so it is
safe to import from anywhere without circular-import worries.
"""

import board

# =====================================================================
# EDITABLE SETTINGS - the things you are most likely to change
# =====================================================================

# Preset waypoint names shown in the "name it" picker when you save a
# location. Pick the ones that match your adventure. KEEP NAMES SHORT:
# about 10 characters max - "Stronghold" (10) is the longest that fits the
# header cleanly before it would crowd the battery icon. Longer names get
# clipped or collide. There are 10 slots (a 2-column, 5-row grid); change
# the words freely, just keep them short.
PICK_NAMES = (
    "Home", "Spawn", "Portal", "Mine", "Castle",
    "Nether", "End", "Stronghold", "Outpost", "Camp",
)

# Magnetic declination, degrees, east positive. This is the angle between
# true north and magnetic north for your area. It is also adjustable on the
# device (Settings > Declination), so you normally leave this at 0 and set
# it there. Central Florida is about -6 (i.e. 6 W). Look yours up on an
# isogonic map (see the in-app guide page).
MAGNETIC_DECLINATION = 0.0

# Button hold timing (seconds): a short tap switches mode, a medium hold
# saves a waypoint, a long hold toggles the light/dark theme.
LONG_PRESS_S = 1.5         # hold this long = save waypoint
EXTRA_LONG_PRESS_S = 3.5   # keep holding this long = toggle theme
BUTTON_PIN = board.D5

# Needle feel. ACCEL/HEADING smoothing low-pass the sensor jitter (lower =
# smoother but laggier, higher = snappier but twitchier). The deadband skips
# redrawing the needle for sub-degree wobble, which keeps it steady when you
# hold still and keeps the frame rate up.
ACCEL_SMOOTHING = 0.2
HEADING_SMOOTHING = 0.25    # 0 = frozen, 1 = raw/no smoothing
NEEDLE_DEADBAND_DEG = 1.5   # don't redraw if the needle moved less than this

# Case-fit offsets. These compensate for the printed enclosure and the
# display panel, and were tuned with calipers for this build. If you design
# a different case, nudge these so the on-screen content lines up with your
# cutout. ROTATED_* only apply when the display is flipped 180 (button at
# the bottom); the touch panel is not flipped, so its coordinates are
# mirrored and these correct the small panel asymmetry.
ROTATED_TOUCH_Y_FIX = 22    # px added to flipped-touch Y (panel asymmetry)
ROTATED_X_SHIFT = 21        # px the UI shifts left when flipped, to recenter
HEADER_RIGHT_X = 254        # right edge of the header text (grows leftward)
FOOTER_CENTER_X = 208       # center of the footer heading text
BATT_X = 277                # left edge of the battery bars
BOLT_X = 264                # left edge of the charging bolt

# Waypoint storage. waypoints persist to WAYPOINTS_FILE as JSON; up to
# MAX_WAYPOINTS can be saved. Coordinates are true-north (e.g. from Google
# Maps); declination is applied at display time.
WAYPOINTS_FILE = "/waypoints.json"
MAX_WAYPOINTS = 8

# =====================================================================
# INTERNAL LAYOUT - colors, geometry, styling (change if you want, but
# you usually will not need to)
# =====================================================================

# Modes
MODE_COMPASS = 0
MODE_WAYPOINT = 1
MODE_NAMES = ("Compass", "Waypoint")

# Earth radius for haversine distance (metres)
EARTH_RADIUS_M = 6371000.0

# Dial layout
CENTER_X = 240
CENTER_Y = 160
CARDINAL_RADIUS = 92
DOT_RADIUS = 100
CARDINALS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")

# Battery indicator: a row of vertical bars (Minecraft-style), filling
# left-to-right with green; unfilled bars are dark red, percentage in white.
BATT_BARS = 5
BATT_BAR_W = 7
BATT_BAR_GAP = 2
BATT_BAR_H = 22
BATT_Y = 10
BATT_NUB_W = 4
BATT_NUB_H = 10
BATT_BAR_GREEN = 0x35C035
BATT_BAR_EMPTY = 0x7A1010
BATT_PCT_X = BATT_X + (BATT_BARS * (BATT_BAR_W + BATT_BAR_GAP)) // 2
BATT_PCT_Y = BATT_Y + BATT_BAR_H // 2

# Charging bolt, shown left of the battery when charging.
BOLT_Y = BATT_Y
BOLT_COLOR = 0xFFD000

# Touch calibration: TSC2007 raw ranges mapped to screen pixels.
TOUCH_MIN_X = 300
TOUCH_MAX_X = 3800
TOUCH_MIN_Y = 185
TOUCH_MAX_Y = 3700
TOUCH_PRESSURE_MIN = 100   # ignore feather-light/false touches below this

# Inventory button (Waypoint Mode footer, bottom-right): opens the list.
INV_BTN_SIZE = 30
INV_BTN_X = 316
INV_BTN_Y = 284
INV_DOT_R = 3

# Waypoint list panel (Minecraft settings style).
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
LIST_CLOSE_SIZE = 20
LIST_TRASH_SIZE = 24
LIST_OUTLINE = 0x3A3A3A
LIST_PANEL_BG = 0x202022
LIST_ROW_BG = 0xC6C6C6
LIST_ROW_TEXT = 0x2A2A2A
LIST_TRASH_BG = 0x35C035
LIST_ARROW = 0x9A9A9A
LIST_ROW_ARMED = 0xF0B000      # gold highlight when a row is armed
LIST_TRASH_ARMED = 0xD02020    # red when armed for delete confirmation
# Scroll-arrow triangle geometry, shared by the list and settings panels.
LIST_ARROW_HALF_W = 12
LIST_ARROW_HEIGHT = 14
LIST_ARROW_HIT_W = 40
LIST_ARROW_HIT_H = 54

# Name picker modal (2-column, 5-row grid of PICK_NAMES).
PICK_COLS = 2
PICK_ROWS = 5
PICK_PAD = 10
PICK_TITLE_H = 26
PICK_CELL_GAP = 6
PICK_CELL_BG = 0xC6C6C6
PICK_CELL_TEXT = 0x2A2A2A

# Settings gear button (Compass Mode footer, bottom-right).
GEAR_SIZE = 30
GEAR_X = 316
GEAR_Y = 284

# Settings panel: reuses the list panel footprint and styling.
SET_X = LIST_X
SET_Y = LIST_Y
SET_W = LIST_W
SET_H = LIST_H
SET_PAD = 10
SET_TITLE_H = 28
SET_ROW_H = 30
SET_ROW_GAP = 5

# Pixel-art needle layout. This is the source-of-truth for the pre-rendered
# needle.bmp (the rotozoom needle rotates that bitmap each frame); the cells
# are kept so the bitmap can be regenerated if the art changes. Coordinates
# are art-pixel units relative to the pivot; red points up at heading 0.
PIXEL = 16
STROKE = 3
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

# Fixed needle colors (same in both themes).
RED = 0xD63A2E
GREY = 0x707070
BLOCK_OUTLINE = 0x101010

# Themes: dark (default, indoor/low light) and light (bright sunlight).
THEME_DARK = {
    "bg": 0x000000,
    "accent": 0xFFAA00,
    "dot": 0x8A5A00,
    "text": 0xFFFFFF,
    "shadow": 0x000000,
}
THEME_LIGHT = {
    "bg": 0xF2F2F2,
    "accent": 0xB5660A,
    "dot": 0xC08A2A,
    "text": 0x101010,
    "shadow": 0xFFFFFF,
}
THEMES = (THEME_DARK, THEME_LIGHT)

# Magnetic declination options offered in Settings (east positive).
DECLINATION_OPTIONS = (20, 15, 10, 5, 0, -5, -10, -15, -20)
DECLINATION_DEFAULT_INDEX = 4   # 0 degrees

# NVM byte assignments for persisted settings (survive power cycles).
NVM_THEME_BYTE = 30
NVM_MARINE_BYTE = 31
NVM_UNITS_BYTE = 32
NVM_DECLINATION_BYTE = 33
NVM_ROTATION_BYTE = 34
