# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Settings panel and info guide overlays for the Minecraft Compass.

The settings panel is a scrolling, arm-then-confirm list: theme, marine
mode, units, declination, display rotation, and recalibrate. The info guide
is a two-page help overlay (controls and a magnetic-declination map) reached
from the settings "?" button. Both are built at import and shown over the
dial. Shared display primitives come from mc_ui; persisted settings and
state come from mc_compass.
"""

import time
import microcontroller
import supervisor

import displayio
import terminalio
import vectorio
from adafruit_display_text import label

from mc_compass import (
    declination_index, marine_mode, rotation_flipped, theme_index,
    units_imperial,
)
from mc_config import (
    DECLINATION_OPTIONS, LIST_ARROW, LIST_ARROW_HALF_W,
    LIST_ARROW_HEIGHT, LIST_ARROW_HIT_H, LIST_ARROW_HIT_W, LIST_CLOSE_SIZE, LIST_OUTLINE,
    LIST_PANEL_BG, LIST_ROW_ARMED, LIST_ROW_BG, LIST_ROW_TEXT,
    LIST_TRASH_ARMED, NVM_DECLINATION_BYTE,
    NVM_MARINE_BYTE, NVM_ROTATION_BYTE, NVM_UNITS_BYTE, SET_H, SET_PAD,
    SET_TITLE_H, SET_W, SET_X, SET_Y,
)
from mc_ui import (
    triangle_points, apply_rotation, point_in_rect, solid_palette,
    toggle_theme, ui,
)


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

# Info "?" button and Close "X" button in the title bar (X far right,
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
        points=triangle_points(
            cx + 1, cy + 1, LIST_ARROW_HALF_W, LIST_ARROW_HEIGHT, pointing_up
        ),
        x=0, y=0,
    )
    fg = vectorio.Polygon(
        pixel_shader=solid_palette(LIST_ARROW),
        points=triangle_points(
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
    ui["display"].refresh(minimum_frames_per_second=0)
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
