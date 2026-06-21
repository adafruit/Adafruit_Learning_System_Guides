# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Core display for the Minecraft Compass: dial, needle, battery, touch.

This is the shared UI foundation. It builds the compass dial, the rotozoom
needle, the battery gauge, the inventory and gear footer buttons, and the
header/footer labels, and it owns the theme system, the touch reader, and
the per-frame display helpers. The overlay modules (mc_waypoints and
mc_settings) import the primitives defined here (solid_palette,
make_shadow_label, apply_theme, point_in_rect, the injected ui objects).

The three display-side objects (display, root group, touch) are injected by
code.py via setup(); widget construction below only builds displayio Groups
in memory, so it needs no hardware and runs at import. State and sensor
reads live in mc_compass; constants live in mc_config.
"""

import math
import time
import microcontroller

import bitmaptools
import displayio
import terminalio
import vectorio
from adafruit_display_text import label

import mc_compass
from mc_compass import rotation_flipped, theme_index
from mc_config import (
    BATT_BARS, BATT_BAR_EMPTY, BATT_BAR_GAP, BATT_BAR_GREEN, BATT_BAR_H,
    BATT_BAR_W, BATT_NUB_H, BATT_NUB_W, BATT_PCT_X, BATT_PCT_Y, BATT_X,
    BATT_Y, BOLT_COLOR, BOLT_X, BOLT_Y, CARDINAL_RADIUS, CENTER_X, CENTER_Y,
    DOT_RADIUS, FOOTER_CENTER_X, GEAR_SIZE, GEAR_X, GEAR_Y, HEADER_RIGHT_X,
    INV_BTN_SIZE, INV_BTN_X, INV_BTN_Y, INV_DOT_R,
    MAGNETIC_DECLINATION,
    MODE_COMPASS, MODE_NAMES, MODE_WAYPOINT, NVM_THEME_BYTE,
    ROTATED_TOUCH_Y_FIX, ROTATED_X_SHIFT, THEMES, TOUCH_MAX_X, TOUCH_MAX_Y,
    TOUCH_MIN_X, TOUCH_MIN_Y, TOUCH_PRESSURE_MIN,
)

# Display-side objects injected by code.py via setup(). They are only used
# by read_touch() (touch), apply_rotation() (display, root), and build_ui()
# (root, for scene assembly), so widget construction below needs none of
# them and can run safely at import.
ui = {"display": None, "root": None, "touch": None}

# Theme element registries, populated as widgets are built so a theme change
# can recolor everything at once.
accent_palettes = []
dot_palettes = []
accent_text_labels = []
text_labels = []


def setup(display, root, touch):
    """Receive the display, root group, and touch controller from code.py."""
    ui["display"] = display
    ui["root"] = root
    ui["touch"] = touch


# --- Palette + theme system ---

def solid_palette(color):
    """Return a 1-entry displayio.Palette filled with the given color."""
    pal = displayio.Palette(1)
    pal[0] = color
    return pal


# Full-screen background rectangle, drawn first (behind everything). Its
# palette entry is mutated on theme change. Oversized and offset negative so
# that shifting the root group (rotation X correction) never exposes an
# unfilled edge.
bg_palette = displayio.Palette(1)
bg_palette[0] = THEMES[0]["bg"]
bg_rect = vectorio.Rectangle(
    pixel_shader=bg_palette, width=560, height=400, x=-40, y=-40,
)


def apply_rotation():
    """Set display rotation and the matching root X shift for the flip.

    At 180 the panel drifts the image right a few px, so nudge the whole
    root group left by ROTATED_X_SHIFT to recenter. The oversized
    background keeps the shifted edge filled.
    """
    if rotation_flipped[0]:
        ui["display"].rotation = 180
        ui["root"].x = -ROTATED_X_SHIFT
    else:
        ui["display"].rotation = 0
        ui["root"].x = 0


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


def triangle_points(cx, cy, half_w, height, pointing_up):
    """Return three points for a triangle centered horizontally at cx."""
    if pointing_up:
        return [(cx, cy - height), (cx - half_w, cy), (cx + half_w, cy)]
    return [(cx, cy + height), (cx - half_w, cy), (cx + half_w, cy)]


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
    if not mc_compass.hw["battery_present"]:
        return
    pct = max(0, min(100, int(mc_compass.hw["battery"].cell_percent)))
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
    charging = mc_compass.hw["battery"].charge_rate > 0.5
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
    if not ui["touch"].touched:
        return None
    point = ui["touch"].touch
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


# --- Settings gear (Compass Mode footer) ---
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


def apply_mode_header(active_mode):
    """Update the header label and inventory button for the active mode."""
    if active_mode == MODE_WAYPOINT:
        current = mc_compass.active_waypoint()
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
    if not mc_compass.hw["gps"].has_fix:
        nav_state[0] = "searching"
        sats = mc_compass.hw["gps"].satellites
        nav_state[3] = sats if sats is not None else 0
        return
    waypoint = mc_compass.active_waypoint()
    if waypoint is None:
        nav_state[0] = "no_waypoint"
        return
    dist = mc_compass.haversine_distance(
        mc_compass.hw["gps"].latitude, mc_compass.hw["gps"].longitude, waypoint[0], waypoint[1]
    )
    true_bearing = mc_compass.initial_bearing(
        mc_compass.hw["gps"].latitude, mc_compass.hw["gps"].longitude, waypoint[0], waypoint[1]
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
    return needle, mc_compass.format_distance(nav_state[2])
