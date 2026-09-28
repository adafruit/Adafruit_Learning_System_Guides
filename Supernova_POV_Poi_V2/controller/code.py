# SPDX-FileCopyrightText: 2026 Erin St Blaine for Adafruit Industries
# SPDX-License-Identifier: MIT

# pylint: disable=too-many-lines,global-statement,redefined-outer-name,too-many-locals,too-many-branches,too-many-statements,too-many-return-statements,too-many-boolean-expressions

"""
Wireless POV Controller

Hardware:
    Feather RP2040 RFM69
    3.5" TFT FeatherWing V2
    TSC2007 touchscreen
    Mini I2C Gamepad

Tabs:
    LIBRARY
    SHOW
    SETTINGS

Radio packet:
    S,folder,image,running,brightness,speed,auto,interval

LIBRARY:
    Main live-performance screen
    9 thumbnails per page in a 3 x 3 grid
    Tap a thumbnail to play it on all POIs
    Current image gets a cyan border
    LEFT/RIGHT joystick = previous/next image
    UP/DOWN joystick = one thumbnail row up/down

SHOW:
    Record timed image cues
    Name and save performances in persistent NVM
    Replay saved performances with timing compensation

SETTINGS:
    Brightness
    Speed
    Autoplay interval
    Toggle autoplay

Gamepad buttons:
    A = context action / STOP
    B = brightness down
    Y = toggle autoplay
    X = brightness up

Storage:
    Controller image library lives on CIRCUITPY at /img/<folder>/.
    Folder names and alphabetical BMP order should match the POIs.
"""

import gc
import os
import time

import board
import digitalio
import displayio
import terminalio
import microcontroller
import vectorio

from micropython import const

import adafruit_hx8357
import adafruit_rfm69
import adafruit_tsc2007
from adafruit_seesaw.seesaw import Seesaw

from adafruit_display_text import label

try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire


# ===========================================================================
# SETTINGS
# ===========================================================================

IMAGE_ROOT = "/img"
DEFAULT_FOLDER = "default"

RADIO_FREQ_MHZ = 915.0

DEFAULT_BRIGHTNESS = 25
DEFAULT_SPEED = 500
DEFAULT_INTERVAL = 8

MIN_SPEED = 100
MAX_SPEED = 1500

COMMAND_REPEATS = 6
COMMAND_REPEAT_DELAY = 0.04

HEARTBEAT_SECONDS = 1.0

TOUCH_MIN = 250
TOUCH_MAX = 3820

LIBRARY_PAGE_SIZE = 9

# Saved performances are kept in the Feather's persistent NVM.
SHOW_PAGE_SIZE = 4
SHOW_NAME_MAX = 16
SHOW_MAGIC = "SUPERNOVA_SHOWS_V1"

# Send recorded image cues slightly early so the POIs' BMP load/render time
# lands the visible image change closer to the recorded musical beat.
SHOW_PLAYBACK_LEAD_MS = 500


# ===========================================================================
# COLORS
# ===========================================================================

BG = 0x101825
PANEL = 0x203047
PANEL_ACTIVE = 0x315673

CYAN = 0x28D7E8
WHITE = 0xF0F4FA
MUTED = 0xA7B6C9
GRAY = 0x5A6675

GREEN = 0x19754E
RED = 0xA52D45
BLUE = 0x285C91


# ===========================================================================
# HELPERS
# ===========================================================================

def clamp(value, low, high):

    return max(
        low,
        min(
            high,
            value,
        ),
    )


# ===========================================================================
# DISPLAY / SPI
# ===========================================================================

displayio.release_displays()

# The RFM69 and TFT share the SPI bus. Keep the radio deselected while
# the display is initialized.

radio_cs = digitalio.DigitalInOut(
    board.RFM_CS
)

radio_cs.switch_to_output(
    value=True
)

spi = board.SPI()
# ===========================================================================
# DISPLAY
# ===========================================================================

display_bus = FourWire(
    spi,
    command=board.D10,
    chip_select=board.D9,
    baudrate=16_000_000,
)

display = adafruit_hx8357.HX8357(
    display_bus,
    width=480,
    height=320,
    rotation=0,
)


# ===========================================================================
# TOUCHSCREEN + MINI I2C GAMEPAD
# ===========================================================================

# The TFT touchscreen and Mini I2C Gamepad share the Feather's I2C bus.
i2c_bus = board.STEMMA_I2C()

touchscreen = adafruit_tsc2007.TSC2007(
    i2c_bus
)


# Mini I2C Gamepad (Adafruit product 5743 / seesaw address 0x50)
BUTTON_X = const(6)
BUTTON_Y = const(2)
BUTTON_A = const(5)
BUTTON_B = const(1)
BUTTON_SELECT = const(0)
BUTTON_START = const(16)

BUTTON_MASK = const(
    (1 << BUTTON_X)
    | (1 << BUTTON_Y)
    | (1 << BUTTON_A)
    | (1 << BUTTON_B)
    | (1 << BUTTON_SELECT)
    | (1 << BUTTON_START)
)

gamepad = Seesaw(
    i2c_bus,
    addr=0x50,
)

gamepad.pin_mode_bulk(
    BUTTON_MASK,
    gamepad.INPUT_PULLUP,
)

gamepad_product = (
    gamepad.get_version()
    >> 16
) & 0xFFFF

print(
    "Gamepad product:",
    gamepad_product,
)

# Joystick readings are 0-1023 after reversal. The gamepad is intended to
# be mounted 90 degrees clockwise on the side of the controller.
#
# Physical controls in that mounted orientation:
#   LEFT/RIGHT = previous/next image
#   UP/DOWN    = brightness up/down
#
# If you physically mount the gamepad the opposite way, change this to False.
GAMEPAD_ROTATED_CLOCKWISE = True

JOYSTICK_LOW = 300
JOYSTICK_HIGH = 700
BRIGHTNESS_STEP = 5


# ===========================================================================
# RADIO
# ===========================================================================

radio_reset = digitalio.DigitalInOut(
    board.RFM_RST
)

rfm69 = adafruit_rfm69.RFM69(
    spi,
    radio_cs,
    radio_reset,
    RADIO_FREQ_MHZ,
)

rfm69.tx_power = 20

print(
    "RFM69 ready at",
    rfm69.frequency_mhz,
    "MHz",
)

print(
    "TX power:",
    rfm69.tx_power,
    "dBm",
)


# ===========================================================================
# FOLDER + IMAGE LIBRARY
# ===========================================================================

def is_directory(path):
    """Return True when path is a directory."""

    try:
        return bool(
            os.stat(path)[0]
            & 0x4000
        )

    except OSError:
        return False


def find_folders():
    """Return image-library folders from CIRCUITPY."""

    try:
        names = os.listdir(
            IMAGE_ROOT
        )

    except OSError as error:
        raise RuntimeError(
            f"Could not read {IMAGE_ROOT}: {error}"
        ) from error

    found = []

    for name in names:

        if name.startswith("."):
            continue

        path = (
            IMAGE_ROOT
            + "/"
            + name
        )

        if is_directory(path):
            found.append(
                name
            )

    found.sort()

    return found


def folder_path(folder_name):
    """Return the CIRCUITPY path for one image folder."""

    return (
        IMAGE_ROOT
        + "/"
        + folder_name
    )


def find_images_in_folder(folder_name):
    """Return BMP files in one folder, alphabetically."""

    path = folder_path(
        folder_name
    )

    try:
        names = os.listdir(
            path
        )

    except OSError:
        return []

    found = []

    for name in names:

        if name.startswith("."):
            continue

        if not name.lower().endswith(
            ".bmp"
        ):
            continue

        full_path = (
            path
            + "/"
            + name
        )

        if not is_directory(
            full_path
        ):

            found.append(
                name
            )

    found.sort()

    return found


folders = find_folders()

if not folders:

    raise RuntimeError(
        "No image folders found in /img. "
        "Create folders such as /img/default and /img/halloween."
    )


if DEFAULT_FOLDER in folders:

    current_folder = (
        DEFAULT_FOLDER
    )

else:

    current_folder = (
        folders[0]
    )


IMAGE_DIR = folder_path(
    current_folder
)

images = find_images_in_folder(
    current_folder
)

if not images:

    raise RuntimeError(
        f"No BMP images found in {IMAGE_DIR}"
    )


print(
    "Found folders:",
    folders,
)

print(
    "Starting folder:",
    current_folder,
)

print(
    "Controller library:",
    len(folders),
    "folders,",
    len(images),
    "images in",
    current_folder,
)


# ===========================================================================
# IMAGE SELECTION
# ===========================================================================

# Image indices are alphabetical within the current folder. Every POI should
# contain matching folder names and matching image order.

order_position = 0


def set_current_folder(
    folder_name
):
    """
    Change the controller's active folder.

    This only changes what the controller is browsing.
    The POIs receive the folder name the next time state is transmitted.
    """

    global current_folder
    global IMAGE_DIR
    global images
    global order_position

    if folder_name not in folders:
        return False

    new_images = (
        find_images_in_folder(
            folder_name
        )
    )

    if not new_images:

        print(
            "Folder has no BMP images:",
            folder_name,
        )

        return False

    current_folder = (
        folder_name
    )

    IMAGE_DIR = folder_path(
        current_folder
    )

    images = (
        new_images
    )

    order_position = 0

    print(
        "Selected folder:",
        current_folder,
        "-",
        len(images),
        "images",
    )

    return True


def current_file_index():
    """Return the selected image index in the current folder."""

    return (
        order_position
        % len(images)
    )


def current_filename():
    """Return the selected image filename."""

    return images[
        current_file_index()
    ]


# ===========================================================================
# STATE
# ===========================================================================

running = False
autoplay = False

brightness = DEFAULT_BRIGHTNESS
speed = DEFAULT_SPEED
interval = DEFAULT_INTERVAL

last_advance = (
    time.monotonic()
)

last_heartbeat = (
    time.monotonic()
)

current_tab = "library"

library_page = 0
folder_page = 0
library_mode = "images"


# ===========================================================================
# SHOW RECORDER STATE
# ===========================================================================

saved_shows = []
selected_show_index = None
show_page = 0
show_mode = "list"

record_pending = False
recording = False
recording_start = 0.0
recorded_folder = ""
recorded_cues = []
recorded_duration_ms = 0

show_name_buffer = ""
show_name_label = None

delete_confirm_index = None

show_playing = False
show_playback_start = 0.0
show_playback_index = 0
show_time_label = None
show_now_label = None
last_show_display_update = 0.0


# ===========================================================================
# DISPLAY HELPERS
# ===========================================================================

root = displayio.Group()

display.root_group = root


def rect(
    parent,
    x,
    y,
    width,
    height,
    color,
):

    # vectorio.Rectangle is much more memory-efficient than creating a
    # displayio.Bitmap as large as every solid UI rectangle.
    palette = displayio.Palette(
        1
    )

    palette[0] = color

    shape = vectorio.Rectangle(
        pixel_shader=palette,
        width=width,
        height=height,
        x=x,
        y=y,
    )

    parent.append(
        shape
    )

    return (
        shape,
        palette,
    )


def text(
    parent,
    message,
    x,
    y,
    color=WHITE,
    scale=2,
):

    item = label.Label(
        terminalio.FONT,
        text=message,
        color=color,
        scale=scale,
        x=x,
        y=y,
    )

    parent.append(
        item
    )

    return item


def centered_text(
    parent,
    message,
    x,
    y,
    width,
    height,
    color=WHITE,
    scale=1,
):

    item = text(
        parent,
        message,
        0,
        0,
        color,
        scale,
    )

    item.anchor_point = (
        0.5,
        0.5,
    )

    item.anchored_position = (
        x + width // 2,
        y + height // 2,
    )

    return item


# Permanent background

rect(
    root,
    0,
    0,
    480,
    320,
    BG,
)


# ===========================================================================
# PAGE GROUP
# ===========================================================================

dynamic_group = displayio.Group()

root.append(
    dynamic_group
)

dynamic_buttons = []


# ===========================================================================
# TAB BAR
# ===========================================================================

TAB_Y = 282
TAB_H = 38

tab_buttons = []


def make_tab(
    name,
    caption,
    x,
    width,
):

    _, palette = rect(
        root,
        x,
        TAB_Y,
        width,
        TAB_H,
        PANEL,
    )

    centered_text(
        root,
        caption,
        x,
        TAB_Y,
        width,
        TAB_H,
        WHITE,
        1,
    )

    tab_buttons.append(
        (
            name,
            x,
            TAB_Y,
            width,
            TAB_H,
            palette,
        )
    )


make_tab(
    "library",
    "LIBRARY",
    0,
    160,
)

make_tab(
    "show",
    "SHOW",
    160,
    160,
)

make_tab(
    "settings",
    "SETTINGS",
    320,
    160,
)


# ===========================================================================
# RECORDING STATUS OVERLAY
# ===========================================================================

record_overlay_group = displayio.Group()
root.append(record_overlay_group)

rect(
    record_overlay_group,
    0,
    0,
    480,
    42,
    RED,
)

record_status_label = text(
    record_overlay_group,
    "",
    12,
    24,
    WHITE,
    1,
)

record_stop_label = centered_text(
    record_overlay_group,
    "STOP REC",
    360,
    0,
    120,
    42,
    WHITE,
    1,
)

record_overlay_group.hidden = True


# ===========================================================================
# GENERIC THUMBNAIL CREATOR
# ===========================================================================

# All thumbnails share this small 16-color RGB palette.
# The source BMPs remain untouched; colors are remapped only for the preview.
THUMBNAIL_PALETTE = displayio.Palette(
    16
)

for _thumb_index in range(
    16
):

    _thumb_r = (
        255
        if _thumb_index & 0x08
        else 0
    )

    _thumb_g = (
        (
            _thumb_index >> 1
        )
        & 0x03
    ) * 85

    _thumb_b = (
        255
        if _thumb_index & 0x01
        else 0
    )

    THUMBNAIL_PALETTE[
        _thumb_index
    ] = (
        (_thumb_r << 16)
        | (_thumb_g << 8)
        | _thumb_b
    )


def _bmp_u16(data, offset):
    """Read a little-endian unsigned 16-bit value."""

    return (
        data[offset]
        | (
            data[offset + 1]
            << 8
        )
    )


def _bmp_u32(data, offset):
    """Read a little-endian unsigned 32-bit value."""

    return (
        data[offset]
        | (
            data[offset + 1]
            << 8
        )
        | (
            data[offset + 2]
            << 16
        )
        | (
            data[offset + 3]
            << 24
        )
    )


def _bmp_s32(data, offset):
    """Read a little-endian signed 32-bit value."""

    value = _bmp_u32(
        data,
        offset,
    )

    if value & 0x80000000:
        value -= 0x100000000

    return value


def create_thumbnail(
    parent,
    file_index,
    box_x,
    box_y,
    box_width,
    box_height,
):
    """
    Build a thumbnail directly from an indexed uncompressed BMP on CIRCUITPY.

    Unlike adafruit_imageload.load(), this does NOT load the full source
    bitmap into RAM. It reads only the BMP header, palette, and one source
    row at a time. This keeps six Library thumbnails reliable on RP2040.
    """

    filename = images[
        file_index
    ]

    path = (
        IMAGE_DIR
        + "/"
        + filename
    )

    gc.collect()

    with open(
        path,
        "rb",
    ) as bmp_file:

        header = bmp_file.read(
            54
        )

        if (
            len(header) < 54
            or header[0] != 0x42
            or header[1] != 0x4D
        ):
            raise ValueError(
                "Not a standard BMP file"
            )

        pixel_offset = _bmp_u32(
            header,
            10,
        )

        dib_size = _bmp_u32(
            header,
            14,
        )

        source_width = _bmp_s32(
            header,
            18,
        )

        raw_height = _bmp_s32(
            header,
            22,
        )

        planes = _bmp_u16(
            header,
            26,
        )

        bits_per_pixel = _bmp_u16(
            header,
            28,
        )

        compression = _bmp_u32(
            header,
            30,
        )

        colors_used = _bmp_u32(
            header,
            46,
        )

        if (
            dib_size < 40
            or planes != 1
        ):
            raise ValueError(
                "Unsupported BMP header"
            )

        if bits_per_pixel not in (
            1,
            4,
            8,
        ):
            raise ValueError(
                "Thumbnail BMP must be 1-, 4-, or 8-bit indexed"
            )

        if compression != 0:
            raise ValueError(
                "Thumbnail BMP must be uncompressed"
            )

        if (
            source_width <= 0
            or raw_height == 0
        ):
            raise ValueError(
                "Invalid BMP dimensions"
            )

        source_height = abs(
            raw_height
        )

        bottom_up = (
            raw_height > 0
        )

        # ---------------------------------------------------------------
        # THUMBNAIL SIZE
        # ---------------------------------------------------------------

        if colors_used <= 0:
            colors_used = (
                1 << bits_per_pixel
            )

        colors_used = min(
            colors_used,
            256,
        )

        usable_width = max(
            1,
            box_width - 6,
        )

        usable_height = max(
            1,
            box_height - 6,
        )

        # Never enlarge the source. Fit proportionally inside the box.
        thumb_width = min(
            source_width,
            usable_width,
        )

        thumb_height = max(
            1,
            (
                source_height
                * thumb_width
            )
            // source_width,
        )

        if thumb_height > usable_height:

            thumb_height = (
                usable_height
            )

            thumb_width = max(
                1,
                (
                    source_width
                    * thumb_height
                )
                // source_height,
            )

        # Allocate the bitmap BEFORE the palette. The bitmap is the largest
        # contiguous block on 256-color images, so doing this first makes
        # allocation much less sensitive to heap fragmentation.
        gc.collect()

        gc.collect()

        thumbnail = displayio.Bitmap(
            thumb_width,
            thumb_height,
            16,
        )

        # ---------------------------------------------------------------
        # SOURCE PALETTE -> SHARED 16-COLOR THUMBNAIL PALETTE
        # ---------------------------------------------------------------

        # Store only a one-byte lookup per source palette entry instead of
        # allocating a separate displayio.Palette for every thumbnail.
        palette_map = bytearray(
            colors_used
        )

        palette_offset = (
            14
            + dib_size
        )

        bmp_file.seek(
            palette_offset
        )

        for color_index in range(
            colors_used
        ):

            entry = bmp_file.read(
                4
            )

            if len(entry) != 4:
                raise ValueError(
                    "BMP palette is truncated"
                )

            # BMP palette order is B, G, R, reserved.
            red = entry[2]
            green = entry[1]
            blue = entry[0]

            # RGB121: 1 red bit, 2 green bits, 1 blue bit = 16 colors.
            palette_map[
                color_index
            ] = (
                (
                    red >> 7
                ) << 3
                | (
                    green >> 6
                ) << 1
                | (
                    blue >> 7
                )
            )

        # BMP rows are padded to a multiple of four bytes.
        row_stride = (
            (
                source_width
                * bits_per_pixel
                + 31
            )
            // 32
        ) * 4

        # ---------------------------------------------------------------
        # SAMPLE DIRECTLY FROM THE FILE
        # ---------------------------------------------------------------

        for y in range(
            thumb_height
        ):

            source_y = min(
                source_height - 1,
                (
                    y
                    * source_height
                )
                // thumb_height,
            )

            if bottom_up:

                file_y = (
                    source_height
                    - 1
                    - source_y
                )

            else:

                file_y = (
                    source_y
                )

            bmp_file.seek(
                pixel_offset
                + file_y
                * row_stride
            )

            row_data = bmp_file.read(
                row_stride
            )

            if len(row_data) < row_stride:
                raise ValueError(
                    "BMP pixel data is truncated"
                )

            for x in range(
                thumb_width
            ):

                source_x = min(
                    source_width - 1,
                    (
                        x
                        * source_width
                    )
                    // thumb_width,
                )

                if bits_per_pixel == 8:

                    pixel_value = (
                        row_data[
                            source_x
                        ]
                    )

                elif bits_per_pixel == 4:

                    packed = (
                        row_data[
                            source_x // 2
                        ]
                    )

                    if (
                        source_x % 2
                        == 0
                    ):
                        pixel_value = (
                            packed >> 4
                        )
                    else:
                        pixel_value = (
                            packed & 0x0F
                        )

                else:

                    packed = (
                        row_data[
                            source_x // 8
                        ]
                    )

                    shift = (
                        7
                        - (
                            source_x % 8
                        )
                    )

                    pixel_value = (
                        packed >> shift
                    ) & 0x01

                thumbnail[
                    x,
                    y,
                ] = (
                    palette_map[
                        pixel_value
                    ]
                )

    gc.collect()

    tile = displayio.TileGrid(
        thumbnail,
        pixel_shader=THUMBNAIL_PALETTE,
    )

    tile.x = (
        box_x
        + box_width // 2
        - thumb_width // 2
    )

    tile.y = (
        box_y
        + box_height // 2
        - thumb_height // 2
    )

    parent.append(
        tile
    )

    return THUMBNAIL_PALETTE


# ===========================================================================
# RADIO
# ===========================================================================

def build_state_message():

    # Folder name travels with every state packet, including heartbeats.
    # This lets an out-of-range POI resync to the correct folder later.
    return (
        f"S,{current_folder},{current_file_index()},{int(running)},"
        f"{brightness},{speed},{int(autoplay)},{interval}"
    )


def send_state(
    repeats=COMMAND_REPEATS
):

    message = (
        build_state_message()
    )

    data = message.encode(
        "ascii"
    )

    for repeat in range(
        repeats
    ):

        rfm69.send(
            data
        )

        if (
            repeat
            < repeats - 1
        ):

            time.sleep(
                COMMAND_REPEAT_DELAY
            )

    print(
        "RF SEND:",
        message,
        "x",
        repeats,
    )


def report_state():

    print(
        "CONTROLLER:",
        current_folder,
        "/",
        current_filename(),
        "running",
        running,
        "brightness",
        brightness,
        "speed",
        speed,
        "auto",
        autoplay,
        "interval",
        interval,
    )


# ===========================================================================
# IMAGE CHANGES
# ===========================================================================

def change_image(
    amount
):

    global order_position
    global running
    global last_advance

    order_position = (
        order_position
        + amount
    ) % len(
        images
    )

    last_advance = (
        time.monotonic()
    )

    # While armed, browse/select the first cue without waking the POIs.
    if record_pending:

        if current_tab == "library":
            refresh_library_selection()

        print(
            "ARMED selection:",
            current_filename(),
        )

        return

    running = True

    report_state()

    send_state()

    record_current_cue()

    if current_tab == "library":

        refresh_library_selection()



def select_file_index(
    file_index
):

    global order_position
    global running
    global last_advance

    if not (
        0
        <= file_index
        < len(images)
    ):

        return

    order_position = (
        file_index
    )

    last_advance = (
        time.monotonic()
    )

    # While armed, change only the controller's selected first cue.
    if record_pending:

        if current_tab == "library":
            refresh_library_selection()

        print(
            "ARMED selection:",
            current_filename(),
        )

        return

    running = True

    report_state()

    send_state()

    record_current_cue()

    if current_tab == "library":

        refresh_library_selection()



# ===========================================================================
# DYNAMIC PAGE HELPERS
# ===========================================================================

def clear_dynamic():

    dynamic_buttons.clear()

    while len(
        dynamic_group
    ):

        dynamic_group.pop()

    gc.collect()


def add_dynamic_button(
    name,
    caption,
    x,
    y,
    width,
    height,
    color=PANEL,
    scale=1,
):

    _, palette = rect(
        dynamic_group,
        x,
        y,
        width,
        height,
        color,
    )

    item = centered_text(
        dynamic_group,
        caption,
        x,
        y,
        width,
        height,
        WHITE,
        scale,
    )

    dynamic_buttons.append(
        (
            name,
            x,
            y,
            width,
            height,
            palette,
            item,
        )
    )


# ===========================================================================
# LIBRARY
# ===========================================================================

# One small background/highlight rectangle per visible thumbnail.
# Changing its palette color is much faster than rebuilding all thumbnails.
library_highlight_palettes = []
library_highlight_indices = []

FOLDER_PAGE_SIZE = 6


def library_page_count():

    return max(
        1,
        (
            len(images)
            + LIBRARY_PAGE_SIZE
            - 1
        ) // LIBRARY_PAGE_SIZE,
    )


def folder_page_count():

    return max(
        1,
        (
            len(folders)
            + FOLDER_PAGE_SIZE
            - 1
        ) // FOLDER_PAGE_SIZE,
    )


def build_folder_page():
    """Show image-library folders from CIRCUITPY."""

    global library_highlight_palettes
    global library_highlight_indices

    clear_dynamic()

    library_highlight_palettes = []
    library_highlight_indices = []

    gc.collect()

    text(
        dynamic_group,
        "LIBRARY",
        12,
        17,
        CYAN,
    )

    text(
        dynamic_group,
        "CHOOSE FOLDER",
        105,
        17,
        WHITE,
        1,
    )

    total_pages = (
        folder_page_count()
    )

    text(
        dynamic_group,
        f"{folder_page + 1}/{total_pages}",
        440,
        17,
        MUTED,
        1,
    )

    start = (
        folder_page
        * FOLDER_PAGE_SIZE
    )

    end = min(
        start
        + FOLDER_PAGE_SIZE,
        len(folders),
    )

    column_x = (
        12,
        246,
    )

    row_y = (
        52,
        112,
        172,
    )

    for slot, folder_index in enumerate(
        range(
            start,
            end,
        )
    ):

        row = (
            slot // 2
        )

        column = (
            slot % 2
        )

        folder_name = (
            folders[
                folder_index
            ]
        )

        caption = (
            folder_name.upper()
        )

        if len(caption) > 22:

            caption = (
                caption[:19]
                + "..."
            )

        color = (
            PANEL_ACTIVE
            if folder_name
            == current_folder
            else PANEL
        )

        add_dynamic_button(
            f"folder_{folder_index}",
            caption,
            column_x[
                column
            ],
            row_y[
                row
            ],
            222,
            46,
            color,
            1,
        )

    add_dynamic_button(
        "folder_prev_page",
        "< PAGE",
        12,
        244,
        105,
        30,
        PANEL,
        1,
    )

    centered_text(
        dynamic_group,
        f"{folder_page + 1} / {total_pages}",
        175,
        244,
        130,
        30,
        MUTED,
        1,
    )

    add_dynamic_button(
        "folder_next_page",
        "PAGE >",
        363,
        244,
        105,
        30,
        PANEL,
        1,
    )

    gc.collect()


def update_library_highlight():
    """Update only the selection border colors on the current Library page."""

    if (
        current_tab != "library"
        or library_mode != "images"
    ):
        return

    selected_index = (
        current_file_index()
    )

    for index, palette in zip(
        library_highlight_indices,
        library_highlight_palettes,
    ):

        palette[0] = (
            CYAN
            if index == selected_index
            else BG
        )


def refresh_library_selection():
    """Move the highlight quickly, rebuilding only when the page changes."""

    global library_page

    if (
        current_tab != "library"
        or library_mode != "images"
    ):
        return

    new_page = (
        current_file_index()
        // LIBRARY_PAGE_SIZE
    )

    if new_page != library_page:

        library_page = (
            new_page
        )

        build_library_page()

    else:

        update_library_highlight()


def build_image_library_page():
    """Show thumbnails inside the currently selected folder."""

    global library_highlight_palettes
    global library_highlight_indices

    clear_dynamic()

    library_highlight_palettes = []
    library_highlight_indices = []

    gc.collect()

    print(
        "Free RAM before Library:",
        gc.mem_free(),
    )

    text(
        dynamic_group,
        "LIBRARY",
        12,
        17,
        CYAN,
    )

    folder_caption = (
        current_folder.upper()
    )

    if len(folder_caption) > 22:

        folder_caption = (
            folder_caption[:19]
            + "..."
        )

    text(
        dynamic_group,
        folder_caption,
        105,
        17,
        WHITE,
        1,
    )

    total_pages = (
        library_page_count()
    )

    text(
        dynamic_group,
        f"{library_page + 1}/{total_pages}",
        440,
        17,
        MUTED,
        1,
    )

    CELL_W = 152
    CELL_H = 61

    THUMB_W = 68
    THUMB_H = 28

    COLUMN_X = (
        2,
        164,
        326,
    )

    ROW_Y = (
        45,
        107,
        169,
    )

    start = (
        library_page
        * LIBRARY_PAGE_SIZE
    )

    end = min(
        start
        + LIBRARY_PAGE_SIZE,
        len(images),
    )

    for slot, file_index in enumerate(
        range(
            start,
            end,
        )
    ):

        row = (
            slot // 3
        )

        column = (
            slot % 3
        )

        cell_x = (
            COLUMN_X[
                column
            ]
        )

        cell_y = (
            ROW_Y[
                row
            ]
        )

        thumb_x = (
            cell_x
            + (
                CELL_W
                - THUMB_W
            )
            // 2
        )

        thumb_y = (
            cell_y
            + 8
        )

        # One backplate gives us a 3-pixel selection border around the
        # thumbnail. Later we only change this palette between BG and CYAN.
        _, highlight_palette = rect(
            dynamic_group,
            thumb_x - 3,
            thumb_y - 3,
            THUMB_W + 6,
            THUMB_H + 6,
            CYAN
            if file_index == current_file_index()
            else BG,
        )

        library_highlight_palettes.append(
            highlight_palette
        )

        library_highlight_indices.append(
            file_index
        )

        try:

            create_thumbnail(
                dynamic_group,
                file_index,
                thumb_x,
                thumb_y,
                THUMB_W,
                THUMB_H,
            )

        except (
            OSError,
            ValueError,
            RuntimeError,
            MemoryError,
        ) as error:

            print(
                "Library thumbnail failed:",
                images[
                    file_index
                ],
                error,
            )

            fallback_name = images[
                file_index
            ]

            if fallback_name.lower().endswith(
                ".bmp"
            ):
                fallback_name = (
                    fallback_name[:-4]
                )

            if len(fallback_name) > 14:
                fallback_name = (
                    fallback_name[:11]
                    + "..."
                )

            centered_text(
                dynamic_group,
                fallback_name,
                thumb_x,
                thumb_y,
                THUMB_W,
                THUMB_H,
                MUTED,
                1,
            )

        gc.collect()

        dynamic_buttons.append(
            (
                f"library_image_{file_index}",
                cell_x,
                cell_y,
                CELL_W,
                CELL_H,
                None,
                None,
            )
        )

    if library_page > 0:

        add_dynamic_button(
            "library_prev_page",
            "< PAGE",
            12,
            244,
            105,
            30,
            PANEL,
            1,
        )

    else:

        rect(
            dynamic_group,
            12,
            244,
            105,
            30,
            GRAY,
        )

        centered_text(
            dynamic_group,
            "< PAGE",
            12,
            244,
            105,
            30,
            MUTED,
            1,
        )

    add_dynamic_button(
        "library_back",
        "FOLDERS",
        175,
        244,
        130,
        30,
        BLUE,
        1,
    )

    if library_page < total_pages - 1:

        add_dynamic_button(
            "library_next_page",
            "PAGE >",
            363,
            244,
            105,
            30,
            PANEL,
            1,
        )

    else:

        rect(
            dynamic_group,
            363,
            244,
            105,
            30,
            GRAY,
        )

        centered_text(
            dynamic_group,
            "PAGE >",
            363,
            244,
            105,
            30,
            MUTED,
            1,
        )

    gc.collect()

    print(
        "Free RAM after Library:",
        gc.mem_free(),
    )



def build_library_page():

    if library_mode == "folders":

        build_folder_page()

    else:

        build_image_library_page()


# ===========================================================================
# SHOW STORAGE
# ===========================================================================

def _show_storage_text():
    """Return the serialized show database stored in microcontroller.nvm."""

    nvm = microcontroller.nvm

    if len(nvm) < 4:
        return ""

    size = (
        nvm[0]
        | (
            nvm[1]
            << 8
        )
    )

    if (
        size <= 0
        or size > len(nvm) - 2
    ):
        return ""

    try:
        return bytes(
            nvm[
                2:2 + size
            ]
        ).decode("utf-8")

    except (
        UnicodeError,
        ValueError,
    ):
        return ""


def load_saved_shows():
    """Load all recorded performances from persistent NVM."""

    loaded = []
    data = _show_storage_text()

    if not data:
        return loaded

    lines = data.splitlines()

    if (
        not lines
        or lines[0] != SHOW_MAGIC
    ):
        return loaded

    for line in lines[1:]:

        if not line:
            continue

        parts = line.split(
            "|",
            3,
        )

        if len(parts) != 4:
            continue

        name = parts[0]
        folder_name = parts[1]

        try:
            duration_ms = int(
                parts[2]
            )

        except ValueError:
            continue

        cues = []

        if parts[3]:

            for cue_text in parts[3].split(
                ";"
            ):

                cue_parts = cue_text.split(
                    ",",
                    1,
                )

                if len(cue_parts) != 2:
                    continue

                try:
                    cue_ms = int(
                        cue_parts[0]
                    )
                    image_index = int(
                        cue_parts[1]
                    )

                except ValueError:
                    continue

                cues.append(
                    (
                        cue_ms,
                        image_index,
                    )
                )

        loaded.append(
            (
                name,
                folder_name,
                duration_ms,
                cues,
            )
        )

    return loaded


def serialize_saved_shows():
    """Serialize saved shows into a compact text representation."""

    lines = [
        SHOW_MAGIC
    ]

    for (
        name,
        folder_name,
        duration_ms,
        cues,
    ) in saved_shows:

        cue_text = ";".join(
            f"{cue_ms},{image_index}"
            for (
                cue_ms,
                image_index,
            ) in cues
        )

        lines.append(
            f"{name}|{folder_name}|{duration_ms}|{cue_text}"
        )

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


def save_show_database():
    """Write the complete show database to persistent NVM."""

    data = serialize_saved_shows().encode(
        "utf-8"
    )

    nvm = microcontroller.nvm
    capacity = len(nvm) - 2

    if len(data) > capacity:

        print(
            "SHOW SAVE FAILED: database needs",
            len(data),
            "bytes but NVM has",
            capacity,
        )

        return False

    nvm[0] = (
        len(data)
        & 0xFF
    )

    nvm[1] = (
        len(data)
        >> 8
    ) & 0xFF

    nvm[
        2:2 + len(data)
    ] = data

    print(
        "Saved",
        len(saved_shows),
        "show(s) using",
        len(data),
        "bytes of NVM",
    )

    return True


# ===========================================================================
# SHOW HELPERS
# ===========================================================================

def format_show_time(milliseconds):
    """Format milliseconds as M:SS.t."""

    total_seconds = max(
        0,
        milliseconds,
    ) // 1000

    tenths = (
        max(
            0,
            milliseconds,
        )
        % 1000
    ) // 100

    minutes = (
        total_seconds
        // 60
    )

    seconds = (
        total_seconds
        % 60
    )

    return f"{minutes}:{seconds:02d}.{tenths}"


def record_current_cue():
    """Record the current image selection when a show is being recorded."""

    if not recording:
        return

    cue_ms = int(
        (
            time.monotonic()
            - recording_start
        )
        * 1000
    )

    recorded_cues.append(
        (
            cue_ms,
            current_file_index(),
        )
    )

    print(
        "REC CUE:",
        cue_ms,
        current_filename(),
    )


def update_record_overlay(now):
    """Update the armed/recording status bar without rebuilding thumbnails."""

    if record_pending:

        if record_status_label.text != "ARMED - choose folder/image":
            record_status_label.text = (
                "ARMED - choose folder/image"
            )

        record_stop_label.text = (
            "START REC"
        )

        return

    if recording:

        elapsed_ms = int(
            (
                now
                - recording_start
            )
            * 1000
        )

        message = (
            "REC  "
            + format_show_time(
                elapsed_ms
            )
        )

        if record_status_label.text != message:
            record_status_label.text = (
                message
            )

        record_stop_label.text = (
            "STOP REC"
        )


def begin_recording_now():
    """Start recording immediately using the currently selected image."""

    global record_pending
    global recording
    global recording_start
    global running
    global recorded_folder

    if not record_pending:
        return

    if library_mode != "images":

        record_status_label.text = (
            "CHOOSE AN IMAGE FIRST"
        )

        return

    record_pending = False
    recording = True
    recording_start = (
        time.monotonic()
    )

    # Lock the chosen folder only when recording actually starts.
    recorded_folder = (
        current_folder
    )

    # The selected first image becomes cue zero exactly when START is pressed.
    running = True

    recorded_cues.append(
        (
            0,
            current_file_index(),
        )
    )

    report_state()
    send_state()

    record_status_label.text = (
        "REC  0:00.0"
    )

    record_stop_label.text = (
        "STOP REC"
    )

    print(
        "SHOW RECORDING STARTED:",
        current_filename(),
        "at 0 ms",
    )


def start_show_recording():
    """Arm recording, open the current folder, and wait for START."""

    global autoplay
    global running
    global last_advance
    global library_mode
    global library_page
    global record_pending
    global recording
    global recorded_folder
    global recorded_cues
    global recorded_duration_ms

    autoplay = False

    # Put all POIs into ready/standby mode while the first cue is selected.
    running = False

    last_advance = (
        time.monotonic()
    )

    report_state()
    send_state()

    recorded_folder = ""

    recorded_cues = []
    recorded_duration_ms = 0

    record_pending = True
    recording = False

    library_mode = (
        "images"
    )

    library_page = (
        current_file_index()
        // LIBRARY_PAGE_SIZE
    )

    show_tab(
        "library"
    )

    record_overlay_group.hidden = (
        False
    )

    update_record_overlay(
        time.monotonic()
    )

    print(
        "SHOW ARMED - choose first image, then press A or START REC"
    )


def cancel_show_recording():
    """Cancel the countdown or current recording without saving it."""

    global record_pending
    global recording
    global recorded_cues
    global show_mode

    record_pending = False
    recording = False
    recorded_cues = []

    record_overlay_group.hidden = (
        True
    )

    show_mode = "list"

    show_tab(
        "show"
    )


def finish_show_recording():
    """Finish recording and open the on-screen naming page."""

    global record_pending
    global recording
    global recorded_duration_ms
    global show_name_buffer
    global show_mode
    global current_tab

    if record_pending:

        cancel_show_recording()
        return

    if not recording:
        return

    recorded_duration_ms = int(
        (
            time.monotonic()
            - recording_start
        )
        * 1000
    )

    recording = False
    record_pending = False

    record_overlay_group.hidden = (
        True
    )

    show_name_buffer = ""
    show_mode = "naming"
    current_tab = "show"

    update_tab_colors()
    build_show_name_page()

    print(
        "SHOW RECORDING STOPPED:",
        len(recorded_cues),
        "cues,",
        recorded_duration_ms,
        "ms",
    )


def add_keyboard_key(
    caption,
    name,
    x,
    y,
    width,
    height,
):
    """Add a lightweight text key and touch target."""

    centered_text(
        dynamic_group,
        caption,
        x,
        y,
        width,
        height,
        WHITE,
        2,
    )

    dynamic_buttons.append(
        (
            name,
            x,
            y,
            width,
            height,
            None,
            None,
        )
    )


def build_show_name_page():
    """Draw the lightweight on-screen keyboard used after recording."""

    global show_name_label

    clear_dynamic()

    gc.collect()

    text(
        dynamic_group,
        "NAME SHOW",
        12,
        17,
        CYAN,
    )

    rect(
        dynamic_group,
        12,
        38,
        456,
        42,
        PANEL,
    )

    show_name_label = centered_text(
        dynamic_group,
        show_name_buffer
        if show_name_buffer
        else "_",
        12,
        38,
        456,
        42,
        WHITE,
        2,
    )

    keyboard_rows = (
        (
            "QWERTYUIOP",
            30,
            92,
        ),
        (
            "ASDFGHJKL",
            51,
            137,
        ),
        (
            "ZXCVBNM",
            93,
            182,
        ),
    )

    for (
        letters,
        start_x,
        key_y,
    ) in keyboard_rows:

        for key_number, letter in enumerate(
            letters
        ):

            key_x = (
                start_x
                + key_number * 42
            )

            add_keyboard_key(
                letter,
                "name_key_" + letter,
                key_x,
                key_y,
                38,
                38,
            )

    add_dynamic_button(
        "name_back",
        "BACK",
        12,
        232,
        90,
        42,
        PANEL,
        1,
    )

    add_dynamic_button(
        "name_space",
        "SPACE",
        112,
        232,
        130,
        42,
        PANEL,
        1,
    )

    add_dynamic_button(
        "name_cancel",
        "CANCEL",
        252,
        232,
        96,
        42,
        PANEL,
        1,
    )

    add_dynamic_button(
        "name_save",
        "SAVE",
        358,
        232,
        110,
        42,
        GREEN,
        1,
    )

    gc.collect()


def show_page_count():
    """Return the number of pages needed for saved shows."""

    return max(
        1,
        (
            len(saved_shows)
            + SHOW_PAGE_SIZE
            - 1
        )
        // SHOW_PAGE_SIZE,
    )


def build_show_page():
    """Draw saved performances and recording/playback controls."""

    global show_time_label
    global show_now_label

    clear_dynamic()

    show_time_label = None
    show_now_label = None

    gc.collect()

    text(
        dynamic_group,
        "SHOW",
        12,
        17,
        CYAN,
    )

    if show_playing:

        (
            show_name,
            _folder_name,
            duration_ms,
            cues,
        ) = saved_shows[
            selected_show_index
        ]

        text(
            dynamic_group,
            show_name[:24],
            92,
            17,
            WHITE,
            1,
        )

        show_time_label = centered_text(
            dynamic_group,
            "0:00.0",
            20,
            58,
            300,
            64,
            CYAN,
            3,
        )

        show_now_label = centered_text(
            dynamic_group,
            "",
            20,
            132,
            300,
            34,
            WHITE,
            1,
        )

        text(
            dynamic_group,
            "Duration "
            + format_show_time(
                duration_ms
            ),
            20,
            188,
            MUTED,
            1,
        )

        text(
            dynamic_group,
            f"{len(cues)} cues",
            20,
            211,
            MUTED,
            1,
        )

        add_dynamic_button(
            "show_restart",
            "RESTART",
            338,
            70,
            130,
            54,
            BLUE,
            1,
        )

        add_dynamic_button(
            "show_stop",
            "STOP SHOW",
            338,
            138,
            130,
            54,
            RED,
            1,
        )

        return

    add_dynamic_button(
        "show_record",
        "RECORD SHOW",
        315,
        8,
        153,
        34,
        RED,
        1,
    )

    if not saved_shows:

        centered_text(
            dynamic_group,
            "NO SAVED SHOWS",
            20,
            95,
            280,
            70,
            MUTED,
            1,
        )

        text(
            dynamic_group,
            "Record a performance to begin.",
            20,
            177,
            MUTED,
            1,
        )

        return

    total_pages = (
        show_page_count()
    )

    start = (
        show_page
        * SHOW_PAGE_SIZE
    )

    end = min(
        start + SHOW_PAGE_SIZE,
        len(saved_shows),
    )

    row_y = (
        54,
        100,
        146,
        192,
    )

    for slot, show_index in enumerate(
        range(
            start,
            end,
        )
    ):

        show_name = (
            saved_shows[
                show_index
            ][0]
        )

        color = (
            PANEL_ACTIVE
            if show_index
            == selected_show_index
            else PANEL
        )

        add_dynamic_button(
            f"show_item_{show_index}",
            show_name[:22],
            12,
            row_y[
                slot
            ],
            310,
            38,
            color,
            1,
        )

    play_color = (
        GREEN
        if selected_show_index
        is not None
        else GRAY
    )

    add_dynamic_button(
        "show_play",
        "PLAY",
        340,
        60,
        128,
        58,
        play_color,
        2,
    )

    delete_color = (
        RED
        if selected_show_index
        is not None
        else GRAY
    )

    add_dynamic_button(
        "show_delete",
        "DELETE",
        340,
        132,
        128,
        44,
        delete_color,
        1,
    )

    if show_page > 0:

        add_dynamic_button(
            "show_prev_page",
            "< PAGE",
            12,
            244,
            105,
            30,
            PANEL,
            1,
        )

    centered_text(
        dynamic_group,
        f"{show_page + 1}/{total_pages}",
        175,
        244,
        130,
        30,
        MUTED,
        1,
    )

    if show_page < total_pages - 1:

        add_dynamic_button(
            "show_next_page",
            "PAGE >",
            363,
            244,
            105,
            30,
            PANEL,
            1,
        )

    gc.collect()


def save_recorded_show():
    """Add the just-recorded show to NVM."""

    global selected_show_index
    global show_page
    global show_mode

    if not show_name_buffer:
        return

    new_show = (
        show_name_buffer,
        recorded_folder,
        recorded_duration_ms,
        list(
            recorded_cues
        ),
    )

    saved_shows.append(
        new_show
    )

    if not save_show_database():

        saved_shows.pop()

        text(
            dynamic_group,
            "NOT ENOUGH NVM SPACE",
            12,
            88,
            RED,
            1,
        )

        return

    selected_show_index = (
        len(saved_shows) - 1
    )

    show_page = (
        selected_show_index
        // SHOW_PAGE_SIZE
    )

    show_mode = "list"
    build_show_page()


def build_delete_confirm_page():
    """Ask for confirmation before deleting the selected show."""

    clear_dynamic()

    gc.collect()

    if (
        delete_confirm_index is None
        or delete_confirm_index < 0
        or delete_confirm_index >= len(saved_shows)
    ):
        build_show_page()
        return

    show_name = (
        saved_shows[
            delete_confirm_index
        ][0]
    )

    text(
        dynamic_group,
        "DELETE SHOW",
        12,
        17,
        CYAN,
    )

    centered_text(
        dynamic_group,
        "Delete",
        30,
        68,
        420,
        30,
        WHITE,
        2,
    )

    centered_text(
        dynamic_group,
        show_name[:28] + "?",
        30,
        106,
        420,
        42,
        WHITE,
        2,
    )

    add_dynamic_button(
        "delete_no",
        "NO",
        70,
        190,
        140,
        60,
        PANEL,
        2,
    )

    add_dynamic_button(
        "delete_yes",
        "YES",
        270,
        190,
        140,
        60,
        RED,
        2,
    )

    gc.collect()


def request_delete_selected_show():
    """Open a confirmation screen before deleting a saved show."""

    global delete_confirm_index
    global show_mode

    if (
        selected_show_index is None
        or selected_show_index < 0
        or selected_show_index >= len(saved_shows)
    ):
        return

    delete_confirm_index = (
        selected_show_index
    )

    show_mode = (
        "delete_confirm"
    )

    build_delete_confirm_page()


def delete_selected_show():
    """Delete the selected saved performance from persistent storage."""

    global selected_show_index
    global show_page
    global delete_confirm_index
    global show_mode

    if (
        delete_confirm_index is None
        or delete_confirm_index < 0
        or delete_confirm_index
        >= len(saved_shows)
    ):
        return

    deleted_index = int(
        delete_confirm_index
    )

    deleted_name = (
        saved_shows[
            deleted_index
        ][0]
    )

    saved_shows.pop(
        deleted_index
    )

    if not save_show_database():

        print(
            "WARNING: show list changed in RAM but NVM save failed"
        )

    if saved_shows:

        selected_show_index = min(
            deleted_index,
            len(saved_shows) - 1,
        )

        show_page = (
            selected_show_index
            // SHOW_PAGE_SIZE
        )

    else:

        selected_show_index = None
        show_page = 0

    delete_confirm_index = None
    show_mode = "list"

    print(
        "Deleted show:",
        deleted_name,
    )

    build_show_page()


def restart_saved_show():
    """Restart the current saved performance from time zero."""

    global running
    global autoplay
    global show_playing
    global show_playback_start
    global show_playback_index
    global last_advance

    if (
        selected_show_index is None
        or selected_show_index < 0
        or selected_show_index
        >= len(saved_shows)
    ):
        return

    (
        _show_name,
        folder_name,
        _duration_ms,
        cues,
    ) = saved_shows[
        selected_show_index
    ]

    if not cues:
        return

    if current_folder != folder_name:

        if not set_current_folder(
            folder_name
        ):

            print(
                "SHOW RESTART FAILED: folder not found:",
                folder_name,
            )

            return

    autoplay = False
    running = True

    last_advance = (
        time.monotonic()
    )

    show_playback_index = 0
    show_playback_start = (
        time.monotonic()
    )

    show_playing = True

    build_show_page()

    print(
        "SHOW RESTART"
    )


def start_saved_show():
    """Start timed playback of the selected recorded performance."""

    global autoplay
    global running
    global show_playing
    global show_playback_start
    global show_playback_index
    global last_advance

    if (
        selected_show_index is None
        or selected_show_index < 0
        or selected_show_index
        >= len(saved_shows)
    ):
        return

    (
        _show_name,
        folder_name,
        _duration_ms,
        cues,
    ) = saved_shows[
        selected_show_index
    ]

    if not cues:
        return

    if not set_current_folder(
        folder_name
    ):

        print(
            "SHOW PLAY FAILED: folder not found:",
            folder_name,
        )

        return

    autoplay = False
    running = True

    last_advance = (
        time.monotonic()
    )

    show_playback_index = 0
    show_playback_start = (
        time.monotonic()
    )

    show_playing = True

    build_show_page()

    print(
        "SHOW PLAY:",
        saved_shows[
            selected_show_index
        ][0],
    )


def stop_saved_show():
    """Stop timed show playback and return the POIs to ready mode."""

    global running
    global show_playing
    global show_playback_index

    show_playing = False
    show_playback_index = 0

    running = False

    report_state()
    send_state()

    if current_tab == "show":
        build_show_page()


def service_show_playback(now):
    """Send every cue whose absolute show time has arrived."""

    global running
    global show_playback_index
    global show_playing
    global last_show_display_update

    if not show_playing:
        return

    (
        _show_name,
        _folder_name,
        duration_ms,
        cues,
    ) = saved_shows[
        selected_show_index
    ]

    elapsed_ms = int(
        (
            now
            - show_playback_start
        )
        * 1000
    )

    while (
        show_playback_index
        < len(cues)
        and (
            cues[
                show_playback_index
            ][0] == 0
            or cues[
                show_playback_index
            ][0] - SHOW_PLAYBACK_LEAD_MS
            <= elapsed_ms
        )
    ):

        (
            _cue_ms,
            image_index,
        ) = cues[
            show_playback_index
        ]

        if (
            0
            <= image_index
            < len(images)
        ):

            select_file_index(
                image_index
            )

            if (
                current_tab == "show"
                and show_now_label
                is not None
            ):

                filename = images[
                    image_index
                ]

                if filename.lower().endswith(
                    ".bmp"
                ):

                    filename = (
                        filename[:-4]
                    )

                show_now_label.text = (
                    filename[:24]
                )

        else:

            print(
                "SHOW CUE SKIPPED: image index",
                image_index,
                "is not in folder",
                current_folder,
            )

        show_playback_index += 1

    if (
        current_tab == "show"
        and show_time_label
        is not None
        and now
        - last_show_display_update
        >= 0.1
    ):

        last_show_display_update = (
            now
        )

        show_time_label.text = (
            format_show_time(
                elapsed_ms
            )
        )

    if (
        elapsed_ms >= duration_ms
        and show_playback_index
        >= len(cues)
    ):

        show_playing = False
        show_playback_index = 0

        running = False

        report_state()
        send_state()

        if current_tab == "show":
            build_show_page()

        print(
            "SHOW COMPLETE - POIs READY"
        )


# ===========================================================================
# SETTINGS
# ===========================================================================

BRIGHT_SLIDER_X = 150
BRIGHT_SLIDER_Y = 70
BRIGHT_SLIDER_W = 260

SPEED_SLIDER_X = 150
SPEED_SLIDER_Y = 135
SPEED_SLIDER_W = 260


def build_settings_page():

    clear_dynamic()

    gc.collect()

    text(
        dynamic_group,
        "SETTINGS",
        12,
        17,
        CYAN,
    )


    # -----------------------------------------------------------------------
    # BRIGHTNESS
    # -----------------------------------------------------------------------

    text(
        dynamic_group,
        "Brightness",
        12,
        75,
        WHITE,
        1,
    )

    rect(
        dynamic_group,
        BRIGHT_SLIDER_X,
        BRIGHT_SLIDER_Y,
        BRIGHT_SLIDER_W,
        8,
        PANEL,
    )

    bright_x = (
        BRIGHT_SLIDER_X
        + brightness
        * BRIGHT_SLIDER_W
        // 100
    )

    rect(
        dynamic_group,
        bright_x - 5,
        BRIGHT_SLIDER_Y - 7,
        10,
        22,
        CYAN,
    )

    text(
        dynamic_group,
        f"{brightness}%",
        425,
        75,
        CYAN,
        1,
    )


    # -----------------------------------------------------------------------
    # SPEED
    # -----------------------------------------------------------------------

    text(
        dynamic_group,
        "Speed",
        12,
        140,
        WHITE,
        1,
    )

    rect(
        dynamic_group,
        SPEED_SLIDER_X,
        SPEED_SLIDER_Y,
        SPEED_SLIDER_W,
        8,
        PANEL,
    )

    speed_x = (
        SPEED_SLIDER_X
        + (
            speed
            - MIN_SPEED
        )
        * SPEED_SLIDER_W
        // (
            MAX_SPEED
            - MIN_SPEED
        )
    )

    rect(
        dynamic_group,
        speed_x - 5,
        SPEED_SLIDER_Y - 7,
        10,
        22,
        CYAN,
    )

    text(
        dynamic_group,
        str(
            speed
        ),
        425,
        140,
        CYAN,
        1,
    )

    text(
        dynamic_group,
        "columns/sec",
        12,
        158,
        MUTED,
        1,
    )


    # -----------------------------------------------------------------------
    # AUTOPLAY INTERVAL
    # -----------------------------------------------------------------------

    text(
        dynamic_group,
        "Image interval",
        12,
        213,
        WHITE,
        1,
    )

    add_dynamic_button(
        "interval_minus",
        "-",
        170,
        190,
        50,
        48,
        PANEL,
        2,
    )

    text(
        dynamic_group,
        f"{interval} sec",
        245,
        215,
        CYAN,
        2,
    )

    add_dynamic_button(
        "interval_plus",
        "+",
        350,
        190,
        50,
        48,
        PANEL,
        2,
    )

    add_dynamic_button(
        "auto",
        "Toggle Autoplay (Y)",
        12,
        244,
        300,
        30,
        GREEN
        if autoplay
        else RED,
        1,
    )

    centered_text(
        dynamic_group,
        "ON"
        if autoplay
        else "OFF",
        330,
        244,
        138,
        30,
        GREEN
        if autoplay
        else RED,
        1,
    )

    gc.collect()

    print(
        "Free RAM after Settings:",
        gc.mem_free(),
    )


# ===========================================================================
# TAB MANAGEMENT
# ===========================================================================

def update_tab_colors():

    for (
        name,
        _x,
        _y,
        _w,
        _h,
        palette,
    ) in tab_buttons:

        palette[0] = (
            PANEL_ACTIVE
            if name
            == current_tab
            else PANEL
        )


def show_tab(
    tab_name
):

    global current_tab

    current_tab = (
        tab_name
    )

    update_tab_colors()

    if current_tab == "library":

        build_library_page()

    elif current_tab == "show":

        if show_mode == "naming":
            build_show_name_page()

        elif show_mode == "delete_confirm":
            build_delete_confirm_page()

        else:
            build_show_page()

    elif current_tab == "settings":

        build_settings_page()


# ===========================================================================
# SETTINGS INPUT
# ===========================================================================

def set_brightness_from_x(
    x
):

    global brightness

    fraction = (
        clamp(
            x
            - BRIGHT_SLIDER_X,
            0,
            BRIGHT_SLIDER_W,
        )
        / BRIGHT_SLIDER_W
    )

    value = int(
        round(
            fraction
            * 100
            / 5
        )
        * 5
    )

    brightness = clamp(
        value,
        0,
        100,
    )


def set_speed_from_x(
    x
):

    global speed

    fraction = (
        clamp(
            x
            - SPEED_SLIDER_X,
            0,
            SPEED_SLIDER_W,
        )
        / SPEED_SLIDER_W
    )

    value = (
        MIN_SPEED
        + fraction
        * (
            MAX_SPEED
            - MIN_SPEED
        )
    )

    value = int(
        round(
            value
            / 25
        )
        * 25
    )

    speed = clamp(
        value,
        MIN_SPEED,
        MAX_SPEED,
    )


# ===========================================================================
# TOUCH
# ===========================================================================

def read_touch():

    if not touchscreen.touched:

        return None

    point = (
        touchscreen.touch
    )

    if point is None:

        return None

    x = (
        point["y"]
        - TOUCH_MIN
    ) * 479 // (
        TOUCH_MAX
        - TOUCH_MIN
    )

    y = (
        4096
        - point["x"]
        - TOUCH_MIN
    ) * 319 // (
        TOUCH_MAX
        - TOUCH_MIN
    )

    return (
        clamp(
            x,
            0,
            479,
        ),
        clamp(
            y,
            0,
            319,
        ),
    )


def button_hit(
    registry,
    x,
    y,
):

    for (
        name,
        bx,
        by,
        width,
        height,
        _palette,
        _item,
    ) in registry:

        if (
            bx <= x
            < bx + width
            and
            by <= y
            < by + height
        ):

            return name

    return None


def hit_test(
    x,
    y,
):

    # -----------------------------------------------------------------------
    # RECORDING OVERLAY FIRST
    # -----------------------------------------------------------------------

    if (
        record_pending
        or recording
    ):

        if (
            360 <= x < 480
            and 0 <= y < 42
        ):

            return (
                "button",
                "record_stop",
            )

        # Keep the performer in the image Library while recording.
        if y >= TAB_Y:

            return (
                "none",
                None,
            )


    # -----------------------------------------------------------------------
    # TABS FIRST
    # -----------------------------------------------------------------------

    for (
        name,
        bx,
        by,
        width,
        height,
        _palette,
    ) in tab_buttons:

        if (
            bx <= x
            < bx + width
            and
            by <= y
            < by + height
        ):

            return (
                "tab",
                name,
            )


    # -----------------------------------------------------------------------
    # DYNAMIC BUTTONS
    # -----------------------------------------------------------------------

    name = button_hit(
        dynamic_buttons,
        x,
        y,
    )

    if name:

        return (
            "button",
            name,
        )


    # -----------------------------------------------------------------------
    # SETTINGS SLIDERS
    # -----------------------------------------------------------------------

    if current_tab == "settings":

        if (
            BRIGHT_SLIDER_X - 15
            <= x
            <= BRIGHT_SLIDER_X
            + BRIGHT_SLIDER_W
            + 15
            and
            BRIGHT_SLIDER_Y - 20
            <= y
            <= BRIGHT_SLIDER_Y + 25
        ):

            return (
                "slider",
                "brightness",
            )

        if (
            SPEED_SLIDER_X - 15
            <= x
            <= SPEED_SLIDER_X
            + SPEED_SLIDER_W
            + 15
            and
            SPEED_SLIDER_Y - 20
            <= y
            <= SPEED_SLIDER_Y + 25
        ):

            return (
                "slider",
                "speed",
            )

    return (
        "none",
        None,
    )


# ===========================================================================
# BUTTON ACTIONS
# ===========================================================================

def do_button(
    name
):

    global running
    global autoplay
    global interval
    global library_page
    global folder_page
    global library_mode
    global last_advance
    global selected_show_index
    global show_page
    global show_name_buffer
    global show_mode
    global delete_confirm_index


    # -----------------------------------------------------------------------
    # SHOW RECORDING / PLAYBACK
    # -----------------------------------------------------------------------

    if name == "show_record":

        start_show_recording()

        return


    if name == "record_stop":

        if record_pending:
            begin_recording_now()
        elif recording:
            finish_show_recording()

        return


    if name == "show_play":

        start_saved_show()

        return


    if name == "show_restart":

        restart_saved_show()

        return


    if name == "show_stop":

        stop_saved_show()

        return


    if name == "show_delete":

        request_delete_selected_show()

        return


    if name == "delete_yes":

        delete_selected_show()

        return


    if name == "delete_no":

        delete_confirm_index = None
        show_mode = "list"

        build_show_page()

        return


    if name.startswith(
        "show_item_"
    ):

        try:

            show_index = int(
                name.split(
                    "_"
                )[-1]
            )

        except ValueError:

            return

        if (
            0
            <= show_index
            < len(saved_shows)
        ):

            selected_show_index = (
                show_index
            )

            build_show_page()

        return


    if name == "show_prev_page":

        show_page = max(
            0,
            show_page - 1,
        )

        build_show_page()

        return


    if name == "show_next_page":

        show_page = min(
            show_page_count() - 1,
            show_page + 1,
        )

        build_show_page()

        return


    # -----------------------------------------------------------------------
    # SHOW NAMING KEYBOARD
    # -----------------------------------------------------------------------

    if name.startswith(
        "name_key_"
    ):

        if len(show_name_buffer) < SHOW_NAME_MAX:

            show_name_buffer += (
                name[-1]
            )

            if show_name_label is not None:
                show_name_label.text = (
                    show_name_buffer
                )

        return


    if name == "name_space":

        if (
            show_name_buffer
            and len(show_name_buffer)
            < SHOW_NAME_MAX
        ):

            show_name_buffer += " "

            if show_name_label is not None:
                show_name_label.text = (
                    show_name_buffer
                )

        return


    if name == "name_back":

        show_name_buffer = (
            show_name_buffer[:-1]
        )

        if show_name_label is not None:
            show_name_label.text = (
                show_name_buffer
                if show_name_buffer
                else "_"
            )

        return


    if name == "name_cancel":

        show_mode = "list"

        build_show_page()

        return


    if name == "name_save":

        save_recorded_show()

        return


    # -----------------------------------------------------------------------
    # PREVIOUS
    # -----------------------------------------------------------------------

    if name == "previous":

        change_image(
            -1
        )

        return


    # -----------------------------------------------------------------------
    # NEXT
    # -----------------------------------------------------------------------

    if name == "next":

        change_image(
            1
        )

        return


    # -----------------------------------------------------------------------
    # STOP
    # -----------------------------------------------------------------------

    if name == "stop":

        running = False

        report_state()

        send_state()

        return


    # -----------------------------------------------------------------------
    # AUTOPLAY
    # -----------------------------------------------------------------------

    if name == "auto":

        autoplay = (
            not autoplay
        )

        last_advance = (
            time.monotonic()
        )

        if current_tab == "settings":
            build_settings_page()

        report_state()

        send_state()

        return


    # -----------------------------------------------------------------------
    # FOLDER SELECTION
    # -----------------------------------------------------------------------

    if name.startswith(
        "folder_"
    ) and name not in (
        "folder_prev_page",
        "folder_next_page",
    ):

        try:

            folder_index = int(
                name.split(
                    "_"
                )[-1]
            )

        except ValueError:

            return

        if (
            0
            <= folder_index
            < len(folders)
        ):

            if set_current_folder(
                folders[
                    folder_index
                ]
            ):

                library_mode = (
                    "images"
                )

                build_library_page()

        return


    if name == "folder_prev_page":

        folder_page = max(
            0,
            folder_page - 1,
        )

        build_library_page()

        return


    if name == "folder_next_page":

        folder_page = min(
            folder_page_count() - 1,
            folder_page + 1,
        )

        build_library_page()

        return


    if name == "library_back":

        if recording:
            return

        library_mode = (
            "folders"
        )

        build_library_page()

        return


    # -----------------------------------------------------------------------
    # LIBRARY IMAGE
    # -----------------------------------------------------------------------

    if name.startswith(
        "library_image_"
    ):

        try:

            file_index = int(
                name.split(
                    "_"
                )[-1]
            )

        except ValueError:

            return

        select_file_index(
            file_index
        )

        return


    # -----------------------------------------------------------------------
    # LIBRARY PREVIOUS PAGE
    # -----------------------------------------------------------------------

    if name == "library_prev_page":

        new_page = max(
            0,
            library_page - 1,
        )

        if new_page != library_page:

            library_page = (
                new_page
            )

            build_library_page()

        return


    # -----------------------------------------------------------------------
    # LIBRARY NEXT PAGE
    # -----------------------------------------------------------------------

    if name == "library_next_page":

        new_page = min(
            library_page_count() - 1,
            library_page + 1,
        )

        if new_page != library_page:

            library_page = (
                new_page
            )

            build_library_page()

        return


    # -----------------------------------------------------------------------
    # INTERVAL -
    # -----------------------------------------------------------------------

    if name == "interval_minus":

        interval = max(
            1,
            interval - 1,
        )

        last_advance = (
            time.monotonic()
        )

        build_settings_page()

        report_state()

        send_state()

        return


    # -----------------------------------------------------------------------
    # INTERVAL +
    # -----------------------------------------------------------------------

    if name == "interval_plus":

        interval = min(
            60,
            interval + 1,
        )

        last_advance = (
            time.monotonic()
        )

        build_settings_page()

        report_state()

        send_state()

        return


# ===========================================================================
# GAMEPAD INPUT
# ===========================================================================

def gamepad_joystick_direction():
    """Return one physical joystick direction, or None in the dead zone."""

    # Reverse the seesaw values so normal board orientation is:
    # left/down = 0 and right/up = 1023.
    joy_x = (
        1023
        - gamepad.analog_read(14)
    )

    joy_y = (
        1023
        - gamepad.analog_read(15)
    )

    if GAMEPAD_ROTATED_CLOCKWISE:

        # Board rotated 90 degrees clockwise:
        # original left  -> physical up
        # original right -> physical down
        # original down  -> physical left
        # original up    -> physical right
        if joy_x < JOYSTICK_LOW:
            return "up"

        if joy_x > JOYSTICK_HIGH:
            return "down"

        if joy_y < JOYSTICK_LOW:
            return "left"

        if joy_y > JOYSTICK_HIGH:
            return "right"

    else:

        # Same board mounted 90 degrees counter-clockwise.
        if joy_x > JOYSTICK_HIGH:
            return "up"

        if joy_x < JOYSTICK_LOW:
            return "down"

        if joy_y > JOYSTICK_HIGH:
            return "left"

        if joy_y < JOYSTICK_LOW:
            return "right"

    return None


def change_brightness_from_gamepad(amount):
    """Change brightness in 5% steps and immediately transmit it."""

    global brightness

    new_brightness = clamp(
        brightness + amount,
        0,
        100,
    )

    if new_brightness == brightness:
        return

    brightness = new_brightness

    if current_tab == "settings":
        build_settings_page()

    report_state()
    send_state()


def library_move_row(row_delta):
    """Move one thumbnail row up/down, continuing across Library pages."""

    if (
        current_tab != "library"
        or library_mode != "images"
    ):
        return

    current_index = (
        current_file_index()
    )

    target_index = (
        current_index
        + row_delta * 3
    )

    if (
        target_index < 0
        or target_index >= len(images)
    ):
        return

    select_file_index(
        target_index
    )



def gamepad_change_image(amount):
    """Change image and keep the Library selection/page synchronized."""

    change_image(
        amount
    )



def gamepad_button_action(button_pin):
    """Handle one newly pressed physical gamepad button."""

    # A is always the context/action button.
    if button_pin == BUTTON_A:

        if (
            record_pending
            or recording
        ):

            if record_pending:
                begin_recording_now()
            else:
                finish_show_recording()

            return

        if current_tab == "show":

            if show_playing:
                restart_saved_show()
            else:
                start_saved_show()

            return

        # Normal live-use behavior: stop the POI display.
        do_button(
            "stop"
        )

        return

    # B/X are dedicated brightness controls.
    if button_pin == BUTTON_B:

        change_brightness_from_gamepad(
            -BRIGHTNESS_STEP
        )

        return

    if button_pin == BUTTON_X:

        change_brightness_from_gamepad(
            BRIGHTNESS_STEP
        )

        return

    # Y toggles autoplay during normal use. Keep it disabled while actively
    # arming/recording a show so automatic changes do not contaminate cues.
    if button_pin == BUTTON_Y:

        if not (
            record_pending
            or recording
        ):
            do_button(
                "auto"
            )

        return

    # START and SELECT are intentionally unused.




# ===========================================================================
# STARTUP
# ===========================================================================

print()

print(
    "POI CONTROLLER"
)

print(
    "Found",
    len(images),
    "BMP images",
)

print(
    "Free RAM before UI:",
    gc.mem_free(),
)

saved_shows = (
    load_saved_shows()
)

if saved_shows:

    selected_show_index = 0

print(
    "Saved shows:",
    len(saved_shows),
)

build_library_page()

update_tab_colors()

report_state()

print(
    "Free RAM after LIBRARY UI:",
    gc.mem_free(),
)

send_state()


# ===========================================================================
# TOUCH STATE
# ===========================================================================

active_type = None
active_name = None

last_seen = 0

slider_changed = False

# Gamepad edge/latch state.  Buttons act once per press and the joystick acts
# once per deflection, then must return to center before another action.
last_gamepad_pressed = 0
joystick_latched = False


# ===========================================================================
# MAIN LOOP
# ===========================================================================

while True:

    now = (
        time.monotonic()
    )

    # -----------------------------------------------------------------------
    # MINI I2C GAMEPAD
    # -----------------------------------------------------------------------

    # Buttons are active-low. Trigger each action only on a new press.
    raw_buttons = gamepad.digital_read_bulk(
        BUTTON_MASK
    )

    gamepad_pressed = (
        (~raw_buttons)
        & BUTTON_MASK
    )

    new_button_presses = (
        gamepad_pressed
        & ~last_gamepad_pressed
    )

    if new_button_presses:

        for button_pin in (
            BUTTON_Y,
            BUTTON_A,
            BUTTON_B,
            BUTTON_X,
            BUTTON_SELECT,
            BUTTON_START,
        ):

            if new_button_presses & (
                1 << button_pin
            ):
                gamepad_button_action(
                    button_pin
                )

    last_gamepad_pressed = (
        gamepad_pressed
    )

    # One joystick action per deflection. It must return to center first.
    joy_direction = (
        gamepad_joystick_direction()
    )

    if joy_direction is None:

        joystick_latched = False

    elif not joystick_latched:

        joystick_latched = True

        if joy_direction == "up":
            # Move one thumbnail row up. Crossing the top continues onto
            # the previous 3x3 Library page.
            library_move_row(
                -1
            )

        elif joy_direction == "down":
            # Move one thumbnail row down. Crossing the bottom continues onto
            # the next 3x3 Library page.
            library_move_row(
                1
            )

        elif joy_direction == "left":
            # Previous image in reading order.
            gamepad_change_image(
                -1
            )

        elif joy_direction == "right":
            # Next image in reading order.
            gamepad_change_image(
                1
            )


    point = (
        read_touch()
    )


    # -----------------------------------------------------------------------
    # TOUCH RELEASE
    # -----------------------------------------------------------------------

    if point is None:

        if (
            active_type is not None
            and
            now - last_seen > 0.12
        ):

            if (
                active_type == "slider"
                and
                slider_changed
            ):

                if current_tab == "settings":
                    build_settings_page()

                report_state()

                send_state()

            active_type = None
            active_name = None
            slider_changed = False


    # -----------------------------------------------------------------------
    # TOUCH ACTIVE
    # -----------------------------------------------------------------------

    else:

        last_seen = (
            now
        )

        x, y = (
            point
        )


        # -------------------------------------------------------------------
        # NEW TOUCH
        # -------------------------------------------------------------------

        if active_type is None:

            active_type, active_name = (
                hit_test(
                    x,
                    y,
                )
            )

            slider_changed = False


            # ---------------------------------------------------------------
            # TAB
            # ---------------------------------------------------------------

            if active_type == "tab":

                show_tab(
                    active_name
                )


            # ---------------------------------------------------------------
            # BUTTON
            # ---------------------------------------------------------------

            elif active_type == "button":

                do_button(
                    active_name
                )


            # ---------------------------------------------------------------
            # SLIDER
            # ---------------------------------------------------------------

            elif active_type == "slider":

                old_brightness = (
                    brightness
                )

                old_speed = (
                    speed
                )

                if active_name == "brightness":

                    set_brightness_from_x(
                        x
                    )

                elif active_name == "speed":

                    set_speed_from_x(
                        x
                    )

                if (
                    brightness
                    != old_brightness
                    or
                    speed
                    != old_speed
                ):

                    slider_changed = (
                        True
                    )

                    build_settings_page()


        # -------------------------------------------------------------------
        # HELD SLIDER
        # -------------------------------------------------------------------

        elif active_type == "slider":

            old_brightness = (
                brightness
            )

            old_speed = (
                speed
            )

            if active_name == "brightness":

                set_brightness_from_x(
                    x
                )

            elif active_name == "speed":

                set_speed_from_x(
                    x
                )

            if (
                brightness
                != old_brightness
                or
                speed
                != old_speed
            ):

                slider_changed = (
                    True
                )

                build_settings_page()


    # -----------------------------------------------------------------------
    # SHOW RECORDING / PLAYBACK
    # -----------------------------------------------------------------------

    if (
        record_pending
        or recording
    ):

        update_record_overlay(
            now
        )

    if show_playing:

        service_show_playback(
            now
        )


    # -----------------------------------------------------------------------
    # AUTOPLAY
    # -----------------------------------------------------------------------

    if (
        running
        and
        autoplay
        and
        not show_playing
        and
        not recording
        and
        len(images) > 1
        and
        active_type is None
        and
        (
            now
            - last_advance
            >= interval
        )
    ):

        order_position = (
            order_position + 1
        ) % len(
            images
        )

        last_advance = (
            time.monotonic()
        )


        # Update only what changed on the visible Library page.
        # Nine thumbnails stay resident; only the selection border changes
        # unless autoplay crosses onto another 3x3 page.

        if current_tab == "library":

            refresh_library_selection()


        report_state()

        send_state()


    # -----------------------------------------------------------------------
    # HEARTBEAT
    # -----------------------------------------------------------------------

    if (
        now
        - last_heartbeat
        >= HEARTBEAT_SECONDS
    ):

        last_heartbeat = (
            now
        )

        send_state(
            repeats=1
        )


    time.sleep(
        0.02
    )
