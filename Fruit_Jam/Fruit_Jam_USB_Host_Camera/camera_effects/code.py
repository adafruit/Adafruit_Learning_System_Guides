# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""USB webcam with live filters on the Fruit Jam.

Frames come from a UVC webcam on a USB host port (adafruit_usb_host_camera),
are decoded with jpegio, run through the currently selected bitmapfilter effect,
and shown on the DVI output with picogame.

Taking a photo saves the camera's JPEG as-is; when an effect is selected the
filtered picture is written alongside it as a .bmp. Photos go to the SD card
when one is mounted, otherwise to /saves (the CPSAVES drive).

Controls, from a USB keyboard on the other host port (or the serial console):
  right / left arrow -> next / previous effect
  up arrow           -> show the plain picture (no effect), keeping the
                        place in the list
  down arrow         -> back to the effect at that place in the list
  1-9, 0             -> shortcuts to every other effect: 1 is the first
                        effect, 2 the third, ... 0 the nineteenth
  space or enter     -> take a photo
  R                  -> remount CPSAVES so the computer sees the new photos

The Fruit Jam's own buttons work without a keyboard: button 1 and button 2
step down and up the list of effects, and button 3 takes a photo.
"""

import binascii
import gc
import os
import struct
import sys
import time

import bitmapfilter
import bitmaptools
import board
import displayio
import jpegio
import keypad
import picodvi
import picogame
import storage
import supervisor
import terminalio
from ulab import numpy as np

import adafruit_usb_host_camera

# pylint: disable=too-many-locals, global-statement

WIDTH, HEIGHT = 320, 240
LABEL_HEIGHT = 14
LABEL_SECONDS = 2

KEY_UP = "\x1b[A"
KEY_DOWN = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT = "\x1b[D"
KEYS_SHUTTER = (" ", "\r", "\n")
# Number keys jump to every other effect: 1 -> effects[1], 2 -> effects[3], ...
# 0 comes after 9, like on the keyboard.
KEYS_NUMBER = "1234567890"

displayio.release_displays()
framebuffer = picodvi.Framebuffer(
    WIDTH,
    HEIGHT,
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
    color_depth=16,
)
# jpegio decodes into `bitmap`, the effects change it in place, and picogame
# draws that same memory straight into the DVI scanout buffer.
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 65535)
sprite = picogame.Sprite(picogame.Bitmap(bitmap, WIDTH, HEIGHT), x=0, y=0)
target = picogame.Framebuffer(framebuffer, WIDTH, HEIGHT, native_rgb565=True)

WHITE = picogame.rgb565(255, 255, 255)
GREEN = picogame.rgb565(0, 221, 0)
RED = picogame.rgb565(255, 0, 0)
BLACK = picogame.rgb565(0, 0, 0)
CLEAR = picogame.rgb565(255, 0, 255)  # stands for "transparent" in the label

# A strip along the bottom of the screen for the effect name and messages
label = picogame.Canvas(WIDTH, LABEL_HEIGHT, transparent=CLEAR)
label.move(0, HEIGHT - LABEL_HEIGHT)
label.clear(CLEAR)
label_until = 0
picture_layers = [sprite]  # the color grids swap in their four panels


def refresh():
    layers = picture_layers
    if time.monotonic() < label_until:
        layers = layers + [label]
    picogame.render(target, layers, None, 0, 0, WIDTH, HEIGHT)


def display_message(text, color=WHITE, seconds=LABEL_SECONDS):
    """Show ``text`` over the bottom of the picture for a while."""
    global label_until  # noqa: PLW0603
    label.clear(CLEAR)
    label.text(4, 1, " %s " % text, color, terminalio.FONT, BLACK)
    label_until = time.monotonic() + seconds
    refresh()


# --- Effects -----------------------------------------------------------------
# These are the adafruit_pycamera.imageprocessing effects. That package needs
# the PyCamera's hardware to import, so the ones used here are repeated.

greyscale_weights = bitmapfilter.ChannelMixer(
    0.299, 0.587, 0.114,
    0.299, 0.587, 0.114,
    0.299, 0.587, 0.114,
)  # fmt: skip
inverse_greyscale_weights = bitmapfilter.ChannelMixer(
    1 - 0.299, 1 - 0.587, 1 - 0.114,
    1 - 0.299, 1 - 0.587, 1 - 0.114,
    1 - 0.299, 1 - 0.587, 1 - 0.114,
)  # fmt: skip
sepia_weights = bitmapfilter.ChannelMixer(
    0.393, 0.769, 0.189,
    0.349, 0.686, 0.168,
    0.272, 0.534, 0.131,
)  # fmt: skip
negative_weights = bitmapfilter.ChannelScaleOffset(-1, 1, -1, 1, -1, 1)
red_weights = bitmapfilter.ChannelScale(1, 0.5, 0.5)
green_weights = bitmapfilter.ChannelScale(0.5, 1, 0.5)
blue_weights = bitmapfilter.ChannelScale(0.5, 0.5, 1)
bright_weights = bitmapfilter.ChannelScale(2.0, 2.0, 2.0)
low_contrast_weights = bitmapfilter.ChannelScaleOffset(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
swap_rb_weights = bitmapfilter.ChannelMixer(0, 0, 1, 0, 1, 0, 1, 0, 0)
swap_bg_weights = bitmapfilter.ChannelMixer(1, 0, 0, 0, 0, 1, 0, 1, 0)
swap_rg_weights = bitmapfilter.ChannelMixer(0, 1, 0, 1, 0, 0, 0, 0, 1)

blur_weights = (1, 2, 1, 2, 4, 2, 1, 2, 1)
sharpen_weights = (-1, -2, -1, -2, 13, -2, -1, -2, -1)
emboss_weights = (-2, -1, 0, -1, 0, 1, 0, 1, 2)
blur_more = [
    4, 15, 24, 15, 4,
    15, 61, 97, 61, 15,
    24, 97, 154, 97, 24,
    15, 61, 97, 61, 15,
    4, 15, 24, 15, 4,
]  # fmt: skip

# The 'ironbow' false color palette, three bytes (R, G, B) per entry
_IRONBOW = binascii.unhexlify(
    "fffffffffffffffefff7fef7f7fdf7f7fdf7f7fcf7effcefefffefefffefeffaefe7fae7"
    "e7fde7e7fde7e7f8e7def8dedeffdedeffdedefeded6fed6d6f5d6d6f5d6d6f4d6cef4ce"
    "ceffceceffcecefacec6fac6c6f5c6c6f5c6c6f0c6bdf0bdbdbfbdbdbfbdbdbebdb5beb5"
    "b5bdb5b5bdb5b5bcb5b5bcb5adafadadafadadaaadadaaada5ada5a5ada5a5a8a5a5a8a5"
    "9cbf9c9cbf9c9cbe9c9cbe9c94b59494b59494b49494b4948caf8c8caf8c8caa8c8caa8c"
    "84a58484a58484a08484a0847b7f7b7b7f7b7b7e7b7b7e7b737d73737d73737c73737c73"
    "6b7f6b6b7f6b6b7a6b6b7a6b637d63637d636378636378635a5f5a5a5f5a5a5e5a5a5e5a"
    "5255525255525254525254524a5f4a4a5f4a4a5a4a4a5a4a4a554a425542425042425042"
    "423f42393f39393e39393e39393d39313d31313c31313c31312f31292f29292a29292a29"
    "292d29212d21212821212821211f21181f18181e18181e18181518101510101410101410"
    "100f10080f08080a08080a08080508000500000000000000000008000010000018080021"
    "08002908002908003110003910004210004a18005218005a18006318006b21006b210073"
    "21007b29007b31007b31007b39007b39007b42007b4a007b4a00845200845200845a0084"
    "6300846300846b00846b008473008c7b008c7b008c84008c84058c8c058c94058c94058c"
    "9c058c9c058ca5058ca5058cad058cb5058cb50a8cbd0a8cbd0a8cbd0f84c6147bc6157b"
    "c61573c61e6bce1f6bce2863ce2863ce2d5ad62a52d62f52d62f4ade3c42de3d42de3e39"
    "de3e31de3f31de5029e75529e75a29e75a21e75f21e75421e75521e75e18e75f18e75f18"
    "ef7810ef7d10ef7a10ef7f08ef7c08ef7d08ef7d08ef7e08ef7f08efa008efa508f7aa08"
    "f7af10f7b410f7b510f7be10f7bf10f7a810f7a810f7ad10f7aa10f7af10f7bc10f7bd10"
    "f7be10f7bf10f7bf10fff018fff518fffa18ffff18fff418fff518fffe18fffe21ffff21"
    "fff829fffd31fffd42fffa52fffa63fffa6bffff7bffff8cfffc94fffca5fffdb5fffdbd"
    "fffecefffedeffffefffff18"
)
ironbow_palette = displayio.Palette(256)
for _i in range(256):
    ironbow_palette[_i] = tuple(_IRONBOW[3 * _i : 3 * _i + 3])
del _IRONBOW


def color_dodge_func(a, b):
    return a / (1 - b) if b != 1 else 1


color_dodge = bitmapfilter.blend_precompute(color_dodge_func)

# Scratch copy of the frame for "sketch"
aux = displayio.Bitmap(WIDTH, HEIGHT, 65535)


def sketch(b):
    bitmapfilter.mix(b, inverse_greyscale_weights)
    memoryview(aux)[:] = memoryview(b)
    bitmapfilter.morph(aux, blur_more)
    bitmapfilter.blend(b, aux, b, color_dodge)
    bitmapfilter.mix(b, inverse_greyscale_weights)


# --- Color grids -------------------------------------------------------------
# The frame is decoded at half size and shown four times, each panel gets
# painted with its own colors.

GRID_WIDTH, GRID_HEIGHT = WIDTH // 2, HEIGHT // 2
GRID_QUANTILES = (18, 46, 76)  # where the bands split, in percent of the pixels
GRID_SOFT = 64  # 0 paints flat bands .. 255 blends each fully into the next
GRID_EDGE_SLACK = 4  # keep the palettes until a band edge moves this far

GRID_SETS = (
    (
        (0x1B0A1E, 0xE6007E, 0xFFD400, 0x22C1C3),
        (0x06131F, 0x0057FF, 0x00E5A0, 0xFFF35C),
        (0x1F0606, 0xFF2E00, 0xFF9E00, 0xFFE9C4),
        (0x0D0518, 0x6A00F4, 0xE040FB, 0xB8FF5C),
    ),
    (
        (0x14100C, 0xC8102E, 0xF5F0E1, 0xE8C547),
        (0x0C1014, 0x1D3F8F, 0xF5F0E1, 0xE8C547),
        (0x0C1410, 0x2E8B57, 0xF5F0E1, 0xE8C547),
        (0x140C14, 0x6B2D5C, 0xF5F0E1, 0xE8C547),
    ),
    (
        (0x0A1A0A, 0xFF2D95, 0xFFE14D, 0x1F6B3A),
        (0x0A1A0A, 0xFF6A00, 0xFFF2B0, 0x1F6B3A),
        (0x0A1A0A, 0x00B3FF, 0xD6FAFF, 0x1F6B3A),
        (0x0A1A0A, 0xB026FF, 0xFFD6FF, 0x1F6B3A),
    ),
    (
        (0x06131F, 0x0057FF, 0x00E5A0, 0xFFF35C),
        (0x1A0016, 0xFF0080, 0x00FFF0, 0xFFFFFF),
        (0x001A0E, 0x00FF6A, 0x003CFF, 0xFFFB00),
        (0x120014, 0xFF4D00, 0xFF00C8, 0x8CFFFF),
    ),
    (
        (0x0A0A0A, 0x3D3D3D, 0x8A8A8A, 0xF0F0F0),
        (0x0A1018, 0x2A4A6A, 0x6A9AC0, 0xE8F4FF),
        (0x180A0A, 0x6A2A2A, 0xC08A6A, 0xFFF0E0),
        (0x0A180F, 0x2A6A3D, 0x8AC0A0, 0xE8FFF0),
    ),
)

grid_source = displayio.Bitmap(GRID_WIDTH, GRID_HEIGHT, 65535)
grid_pixels = np.frombuffer(grid_source, dtype=np.uint8)
grid_panels = []
grid_palettes = []
grid_layers = []
for _i in range(4):
    _panel = displayio.Bitmap(GRID_WIDTH, GRID_HEIGHT, 65535)
    grid_panels.append(_panel)
    grid_palettes.append(displayio.Palette(256))
    grid_layers.append(
        picogame.Sprite(
            picogame.Bitmap(_panel, GRID_WIDTH, GRID_HEIGHT),
            x=(_i % 2) * GRID_WIDTH,
            y=(_i // 2) * GRID_HEIGHT,
        )
    )
grid_edges = None  # the band edges the palettes were built for
grid_loaded = None  # and the palette set


def grid_band_edges():
    """Brightness (0-255) at each of GRID_QUANTILES, from a sample of the
    pixels of grid_source."""
    step = 2 * 13  # every 13th pixel; each is two bytes, RRRRRGGG GGGBBBBB
    high = grid_pixels[0::step]
    low = grid_pixels[1::step]
    red = high // 8
    green_low = low // 32
    green = (high - red * 8) * 8 + green_low
    blue = low - green_low * 32
    luma = np.sort(red * (8 * 0.299) + green * (4 * 0.587) + blue * (8 * 0.114))
    return [0] + [int(luma[len(luma) * q // 100]) for q in GRID_QUANTILES] + [256]


def grid_build_palette(palette, colors, edges):
    """Spread a panel's four colors over the brightness bands."""
    for level in range(4):
        a = colors[level]
        b = colors[min(level + 1, 3)]
        ar, ag, ab = a >> 16, (a >> 8) & 0xFF, a & 0xFF
        dr, dg, db = (b >> 16) - ar, ((b >> 8) & 0xFF) - ag, (b & 0xFF) - ab
        low, high = edges[level], edges[level + 1]
        for y in range(low, high):
            # how far through the band, softened toward the flat color
            t = (y - low) * GRID_SOFT // (high - low)
            palette[y] = (
                (ar + (dr * t >> 8)) << 16
                | (ag + (dg * t >> 8)) << 8
                | (ab + (db * t >> 8))
            )


def color_grid(set_index):
    """Make the effect that paints grid_source into the four panels."""

    def effect(_):
        global grid_edges, grid_loaded  # noqa: PLW0603
        edges = grid_band_edges()
        # Building the palettes is the slow part, so keep them while the
        # picture's brightness holds steady.
        if grid_loaded != set_index or any(
            abs(new - old) >= GRID_EDGE_SLACK for new, old in zip(edges, grid_edges)
        ):
            for palette, colors in zip(grid_palettes, GRID_SETS[set_index]):
                grid_build_palette(palette, colors, edges)
            grid_edges = edges
            grid_loaded = set_index
        source = memoryview(grid_source)
        for panel, palette in zip(grid_panels, grid_palettes):
            memoryview(panel)[:] = source
            bitmapfilter.false_color(panel, palette)

    return effect


# The swap grid's panels: plain, then each pair of color channels traded
SWAP_GRID_WEIGHTS = (None, swap_rb_weights, swap_bg_weights, swap_rg_weights)


def swap_grid(_):
    """Paint grid_source into the four panels, the top left one as it is and
    the others with two of their color channels swapped."""
    source = memoryview(grid_source)
    for panel, weights in zip(grid_panels, SWAP_GRID_WEIGHTS):
        memoryview(panel)[:] = source
        if weights is not None:
            bitmapfilter.mix(panel, weights)


def grid_to_bitmap():
    """Copy the four panels into the full size bitmap, to save as a photo."""
    for i, panel in enumerate(grid_panels):
        bitmaptools.blit(bitmap, panel, (i % 2) * GRID_WIDTH, (i // 2) * GRID_HEIGHT)


effects = [
    ("none", lambda b: None),
    ("greyscale", lambda b: bitmapfilter.mix(b, greyscale_weights)),
    ("negative", lambda b: bitmapfilter.mix(b, negative_weights)),
    ("sepia", lambda b: bitmapfilter.mix(b, sepia_weights)),
    ("red cast", lambda b: bitmapfilter.mix(b, red_weights)),
    ("green cast", lambda b: bitmapfilter.mix(b, green_weights)),
    ("blue cast", lambda b: bitmapfilter.mix(b, blue_weights)),
    ("solarize", bitmapfilter.solarize),
    ("ironbow", lambda b: bitmapfilter.false_color(b, ironbow_palette)),
    ("blur", lambda b: bitmapfilter.morph(b, blur_weights)),
    ("sharpen", lambda b: bitmapfilter.morph(b, sharpen_weights)),
    ("emboss", lambda b: bitmapfilter.morph(b, emboss_weights, add=0.5)),
    ("bright", lambda b: bitmapfilter.mix(b, bright_weights)),
    ("low contrast", lambda b: bitmapfilter.mix(b, low_contrast_weights)),
    ("swap r/b", lambda b: bitmapfilter.mix(b, swap_rb_weights)),
    ("sketch", sketch),
]
FIRST_GRID = len(effects)
for _i in range(len(GRID_SETS)):
    effects.append(("color grid %d" % (_i + 1), color_grid(_i)))
effects.append(("swap grid", swap_grid))
effect_index = 0
# Up arrow sets this to show the plain picture without losing effect_index
bypass = False


def active_effect():
    """The index into ``effects`` of what is on screen."""
    return 0 if bypass else effect_index


# --- Saving photos -----------------------------------------------------------


def photo_directory():
    try:
        storage.getmount("/sd")
        return "/sd"
    except OSError:
        return "/saves"


def next_photo_number(directory):
    number = 0
    for name in os.listdir(directory):
        if name.startswith("img") and name[3:7].isdigit():
            number = max(number, int(name[3:7]))
    return number + 1


def save_bmp(path, source):
    """Write an RGB565_SWAPPED bitmap as a 24 bit .bmp file."""
    _width, _height = source.width, source.height
    row_size = (_width * 3 + 3) & ~3
    # Build the file in memory and write it at once: many small writes to the
    # flash drive are several times slower.
    data = bytearray(54 + row_size * _height)
    data[0:2] = b"BM"
    struct.pack_into("<IHHI", data, 2, len(data), 0, 0, 54)
    struct.pack_into(
        "<IiiHHIIiiII", data, 14, 40, _width, _height, 1, 24, 0, 0, 0, 0, 0, 0
    )
    out = np.frombuffer(data, dtype=np.uint8)
    pixels = np.frombuffer(source, dtype=np.uint8)
    for y in range(_height):
        row = pixels[y * _width * 2 : (y + 1) * _width * 2]
        high = row[0::2]  # RRRRRGGG
        low = row[1::2]  # GGGBBBBB
        red = high // 8
        green_low = low // 32
        start = 54 + (_height - 1 - y) * row_size  # .bmp rows run bottom to top
        stop = start + _width * 3
        out[start:stop:3] = (low - green_low * 32) * 8
        out[start + 1 : stop : 3] = (high - red * 8) * 32 + green_low * 4
        out[start + 2 : stop : 3] = red * 8
    with open(path, "wb") as f:
        f.write(data)


def take_photo(_camera, _mode, _frame):
    """Save ``frame`` (the JPEG on screen) and, with an effect selected, the
    filtered picture that was made from it."""
    _active = active_effect()
    effect_name = effects[_active][0]
    try:
        directory = photo_directory()
        base = "%s/img%04d" % (directory, next_photo_number(directory))
        display_message("snap", GREEN)
        _camera.save_jpeg(base + ".jpg", _frame)
        print("Saved", base + ".jpg")
        if effect_name != "none":
            display_message("saving " + effect_name, GREEN)
            path = "%s_%s.bmp" % (base, effect_name.replace(" ", "_").replace("/", ""))
            if _active >= FIRST_GRID:
                grid_to_bitmap()
            # Writing the .bmp takes a few seconds, far longer than the camera's
            # stream can be buffered for, so pause it meanwhile.
            _camera.stop()
            try:
                t0 = time.monotonic()
                save_bmp(path, bitmap)
                print("Saved %s in %.1fs" % (path, time.monotonic() - t0))
            finally:
                _camera.start(_mode)
        display_message("saved " + base, GREEN)
    except OSError as exception:
        # Read-only or full drive. /saves only holds about 2 MB.
        print("Save failed:", exception)
        display_message("Save failed: %s" % exception, RED)
    gc.collect()


def remount_saves():
    """Remount /saves. The computer only reads the CPSAVES drive when it mounts
    it, so photos saved since then stay hidden until the drive comes back."""
    display_message("Remounting CPSAVES", GREEN)
    try:
        storage.remount("/saves", readonly=False)
        print("Remounted CPSAVES")
        display_message("Remounted CPSAVES", GREEN)
    except (OSError, RuntimeError) as exception:
        print("Remount failed:", exception)
        display_message("Remount failed: %s" % exception, RED)


# --- Keyboard and buttons ----------------------------------------------------


def read_keys():
    """Return the keys typed since the last call. A USB keyboard plugged into
    the Fruit Jam types into sys.stdin, the same as the serial console does.
    Arrow keys arrive as three character escape sequences."""
    available = supervisor.runtime.serial_bytes_available
    if not available:
        return []
    data = sys.stdin.read(available)
    keys = []
    i = 0
    while i < len(data):
        if data[i] == "\x1b" and data[i + 1 : i + 2] == "[" and i + 2 < len(data):
            keys.append(data[i : i + 3])
            i += 3
        else:
            keys.append(data[i])
            i += 1
    return keys


# The board's own buttons stand in for three of the keys
try:
    buttons = keypad.Keys(
        (board.BUTTON1, board.BUTTON2, board.BUTTON3),
        value_when_pressed=False,
        pull=True,
    )
except ValueError:
    # Something else holds the button pins: imported over the top of another
    # program (its objects survive Ctrl-C). Run with the keyboard only.
    buttons = None
    print("Board buttons are in use by another program; keyboard only.")
BUTTON_KEYS = (KEY_LEFT, KEY_RIGHT, KEYS_SHUTTER[0])


def read_buttons():
    """Return the keys the board's buttons stand for, for each button pressed
    since the last call."""
    keys = []
    while buttons is not None:
        event = buttons.events.get()
        if event is None:
            break
        if event.pressed:
            keys.append(BUTTON_KEYS[event.key_number])
    return keys


# --- Main --------------------------------------------------------------------

camera = None
while camera is None:
    try:
        # Finds the camera among the attached devices; the keyboard is one too
        camera = adafruit_usb_host_camera.UVCCamera()
    except ValueError:
        print("Plug a USB camera into a USB host port")
        display_message("Plug in a USB camera", RED)
        time.sleep(1)

mode = camera.find_mode(WIDTH, HEIGHT)
decoder = jpegio.JpegDecoder()
print("Filtered camera ready:", mode)
print("Arrow keys choose the effect, space takes a photo, R remounts CPSAVES.")
print("Board buttons: 1/2 choose the effect, 3 takes a photo.")
camera.start(mode)
display_message("arrows: effect  space: photo  R: remount", seconds=4)

try:
    while True:
        try:
            frame = camera.capture()
        except RuntimeError:
            continue  # no complete frame in time; keep trying
        width, height = decoder.open(camera.add_huffman_tables(frame))
        # The color grids show the picture four times at half size
        active = active_effect()
        grid = active >= FIRST_GRID
        destination = grid_source if grid else bitmap
        # Shrink larger pictures to fit: each scale step halves the size.
        scale = 0
        while (width >> scale) > destination.width or (
            height >> scale
        ) > destination.height:
            scale += 1
        try:
            decoder.decode(destination, scale=scale)
        except (RuntimeError, ValueError):
            continue  # damaged frame
        effects[active][1](destination)
        picture_layers = grid_layers if grid else [sprite]
        refresh()

        for key in read_keys() + read_buttons():
            if key == KEY_RIGHT:
                effect_index = (effect_index + 1) % len(effects)
                bypass = False
            elif key == KEY_LEFT:
                effect_index = (effect_index - 1) % len(effects)
                bypass = False
            elif key == KEY_UP:
                bypass = True
            elif key == KEY_DOWN:
                bypass = False
            elif key in KEYS_NUMBER:
                effect_index = min(2 * KEYS_NUMBER.index(key) + 1, len(effects) - 1)
                bypass = False
            elif key in KEYS_SHUTTER:
                take_photo(camera, mode, frame)
                break
            elif key in {"r", "R"}:
                remount_saves()
        if active_effect() != active:
            print("Filter:", effects[active_effect()][0])
            display_message(effects[active_effect()][0])
finally:
    camera.stop()
