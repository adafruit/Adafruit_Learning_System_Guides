# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Waypoint list and name picker overlays for the Minecraft Compass.

The waypoint list shows saved locations with per-row load (arm-then-confirm)
and delete, scrolled when there are more than fit. The name picker is the
grid of preset names shown when saving a location. Both are built at import
and shown or hidden over the dial. Shared display primitives (palettes,
the injected display objects, hit-testing) come from mc_ui; state and
storage come from mc_compass.
"""

import time

import displayio
import terminalio
import vectorio
from adafruit_display_text import label

import mc_compass
from mc_compass import active_index, mode, waypoints
from mc_config import (
    LIST_ARROW, LIST_ARROW_COL_W, LIST_ARROW_HALF_W, LIST_ARROW_HEIGHT,
    LIST_ARROW_HIT_H, LIST_ARROW_HIT_W, LIST_CLOSE_SIZE, LIST_H, LIST_OUTLINE,
    LIST_PAD, LIST_PANEL_BG, LIST_ROW_ARMED, LIST_ROW_BG, LIST_ROW_GAP,
    LIST_ROW_H,
    LIST_ROW_TEXT, LIST_TITLE_H, LIST_TRASH_ARMED, LIST_TRASH_BG,
    LIST_TRASH_SIZE,
    LIST_VISIBLE_ROWS, LIST_W, LIST_X, LIST_Y, MODE_WAYPOINT,
    PICK_CELL_BG, PICK_CELL_GAP, PICK_CELL_TEXT, PICK_COLS, PICK_NAMES,
    PICK_PAD, PICK_ROWS, PICK_TITLE_H,
)
from mc_ui import (
    apply_mode_header, flash_message, point_in_rect, solid_palette,
    triangle_points, ui,
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




def _add_arrow(cx, cy, pointing_up):
    """Append a grey triangle with a 1px drop shadow; return (shadow, fg)."""
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
        mc_compass.save_waypoints()
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
            mc_compass.save_waypoints()
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
            if not mc_compass.hw["gps"].has_fix:
                flash_message("No fix yet")
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
        apply_mode_header(mode[0])
        return
    idx = picked_name_index(point)
    if idx is None:
        return
    # Brief gold highlight on the tapped cell for tap feedback, matching
    # the armed-row look in the waypoint list.
    pick_cell_palettes[idx][0] = LIST_ROW_ARMED
    ui["display"].refresh(minimum_frames_per_second=0)
    time.sleep(0.15)
    lat, lon, keep_active = pending_save[0]
    pending_save.clear()
    picker_group.hidden = True
    if lat is None:
        # Preview mode (no fix when the picker opened): nothing to save.
        # Let the names be browsed, then report there's no fix yet.
        apply_mode_header(mode[0])
        flash_message("No fix yet")
        return
    name = PICK_NAMES[idx]
    waypoints.append((lat, lon, name))
    # Compass-mode saves make the new point active; waypoint-mode saves keep
    # navigating the current target and just add the breadcrumb to the list.
    if not keep_active:
        active_index[0] = len(waypoints) - 1
    try:
        mc_compass.save_waypoints()
    except OSError:
        pass  # name still applies this session
    apply_mode_header(mode[0])
