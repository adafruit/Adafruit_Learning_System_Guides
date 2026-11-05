# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Screen layout: every size and position the screens use, for the 320x240
2.8" TFT Touch Shield on the Metro ESP32-P4 (docs/PLAN-v2.md).

Screens read L's attributes when they build. Rects are (x, y, w, h).
v1's 480x320 layout for the Feather is at the tag v1-feather-final.
"""


class Layout:
    def set(self, values):
        for k, v in values.items():
            setattr(self, k, v)


def _values():
    return dict(
    W=320, H=240,
    TAG_BTN=(6, 5, 70, 26),
    FAV_TAB=(82, 5, 34, 26),
    SORT_BTN=(122, 5, 64, 26),
    FM1_RIGHT=312,
    HEADER_Y=18,
    CONNECT_BTN=(192, 5, 122, 26),
    TABS_ZONE=(0, 189),
    CONNECT_ZONE_X=189,
    COLS=3, ROWS=2,
    CARD_W=100, CARD_H=82, GAP=4,
    GRID_X=6, GRID_Y=36,
    THUMB=40,
    CARD_THUMB_Y=8,
    CARD_NAME_Y=52,
    CARD_VERSION_Y=68,
    EMPTY_Y=110,
    ROW_W=152, ROW_H=26, ROW_PITCH=28,
    LIST_ROWS=6,
    ROW_HEART_DY=8,
    PREV=(6, 208, 40, 28),
    NEXT=(274, 208, 40, 28),
    VIEW=(52, 208, 32, 28),
    VIEW_ICON_DY=8,
    PAGE_Y=222,
    SETTINGS_BTN=(90, 208, 32, 28),
    UPDATE_BTN=(128, 208, 60, 28),
    BACK_BTN=(6, 6, 64, 26),
    HEART_BTN=(270, 6, 44, 26),
    REMOVE_BTN=(190, 6, 74, 26),
    HEART_AT=(285, 13),
    PIC=("thumb.bmp", 80),
    PIC_AT=(8, 38),
    DETAIL_X=98,
    NAME_W_PAD=8,
    DESC_BOTTOM=198,
    PIC_BOTTOM=124,
    DESC_LEFT=8,
    DESC_LAST_W=200,
    INSTALL_BTN=(196, 204, 118, 30),
    NOTE_AT=(8, 212),
    NOTE_W=180,
    CONFIRM_PANEL=(6, 6, 308, 228),
    CONFIRM_TITLE_AT=(18, 22),
    CONFIRM_W=284,
    CONFIRM_TEXT_Y=56,
    CONFIRM_LINES=6,
    CANCEL_BTN=(18, 182, 132, 40),
    GO_BTN=(170, 182, 132, 40),
    PROGRESS_TITLE_Y=24,
    PROGRESS_TITLE_W=300,
    PROGRESS_SUB_Y=54,
    BAR=(16, 100, 288, 24),
    PROGRESS_NOTE_Y=160,
    OK_BTN=(196, 204, 118, 30),  # where Install is on the details: not over the list's Catalog
    # settings
    SETTINGS_TITLE_Y=19,
    SETTINGS_TEXT_Y=52,
)


L = Layout()
L.set(_values())


def use(width, height):
    """Check the display is the one the layout is for."""
    if (width, height) != (L.W, L.H):
        raise ValueError("no layout for a %dx%d display" % (width, height))
