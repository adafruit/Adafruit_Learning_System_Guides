# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Sushi conveyor belt drawn straight into a DotClockFramebuffer, the inner
loops as @micropython.viper.

At startup, load_tiles() builds one opaque tile per plate. The belt is a
loop of slots, one tile each.

Four caller-owned buffers:

  framebuffer  the DotClockFramebuffer itself, RGB565, via its buffer protocol
  tiles        bytearray of every tile, back to back, RGB565, portrait
  slots        array('i'), per slot: index in tiles of its tile's first pixel
  params       array('i'), settings in, one int per PARAM_* slot below

new() builds slots and params
"""

import array
import struct

import micropython
from micropython import const

PARAM_FIRST_PIXEL = const(0)  # framebuffer index of screen pixel (0, 0)
PARAM_ROW_STRIDE = const(1)  # framebuffer pixels from one row to the next
PARAM_BELT_X = const(2)  # belt's left edge on screen, pixels
PARAM_SCREEN_HEIGHT = const(3)  # rows to draw
PARAM_TILE_WIDTH = const(4)  # tile size in the framebuffer's orientation, pixels
PARAM_TILE_HEIGHT = const(5)  # the belt pitch: one tile per slat
PARAM_SLOT_COUNT = const(6)  # slots in the belt loop
PARAM_SCROLL = const(7)  # 0 .. slot count * tile height - 1; more moves the belt down
PARAM_COUNT = const(8)
# pylint: disable=undefined-variable, too-many-locals, too-many-positional-arguments, unused-argument

# load bitmap
class IndexedBMP:
    """An uncompressed 8-bit indexed BMP file: its size and its palette as
    RGB565"""

    def __init__(self, path, transparent_index=None):
        self.path = path
        with open(path, "rb") as bmp:
            header = bmp.read(54)
            if len(header) < 54 or header[:2] != b"BM":
                raise ValueError(path + ": not a BMP file")
            (
                self._data_offset,
                info_size,
                self.width,
                height,
                _planes,
                bits,
                compression,
                _image_size,
                _x_density,
                _y_density,
                color_count,
                _important,
            ) = struct.unpack_from("<IIiiHHIIiiII", header, 10)
            if bits != 8 or compression != 0 or info_size < 40:
                raise ValueError(
                    path + ": needs to be an 8-bit indexed BMP without compression"
                )
            # A positive height stores the rows bottom to top.
            self._bottom_up = height > 0
            self.height = abs(height)
            color_count = color_count or 256
            bmp.seek(14 + info_size)
            entries = bmp.read(4 * color_count)  # blue, green, red, unused
        self.palette = array.array("H", [0] * 256)
        for index in range(color_count):
            blue, green, red = entries[4 * index], entries[4 * index + 1], entries[4 * index + 2]
            self.palette[index] = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        self.transparent = -1
        if transparent_index is not None:
            used = set(
                self.palette[index] for index in range(color_count) if index != transparent_index
            )
            self.transparent = 0x0821  # nearly black, and nearly never used
            while self.transparent in used:
                self.transparent += 1
            self.palette[transparent_index] = self.transparent

    def draw_rotated(self, dest, start, stride, dest_pixels):
        """Write the image into dest (RGB565, dest_pixels long) turned 90
        degrees clockwise: row y of the image becomes column height - 1 - y,
        and moving right along the image moves down dest, stride pixels a
        step. start is the dest index of the turned image's top left."""
        if start < 0 or start + (self.width - 1) * stride + self.height > dest_pixels:
            raise ValueError(self.path + ": doesn't fit where it's being drawn")
        row_bytes = (self.width + 3) & ~3  # BMP rows are padded to 4 bytes
        row = bytearray(row_bytes)
        args = array.array("i", [self.width, 0, stride])
        with open(self.path, "rb") as bmp:
            bmp.seek(self._data_offset)
            for file_row in range(self.height):
                bmp.readinto(row)
                y = self.height - 1 - file_row if self._bottom_up else file_row
                args[1] = start + self.height - 1 - y
                expand_row(dest, row, self.palette, args)


def overlay_rect(dest, dest_start, dest_stride, src, src_start,
                 src_stride, width, height, transparent=-1):
    """Copy a width x height rectangle of RGB565 from src to dest, skipping
    pixels equal to transparent"""
    overlay(
        dest,
        src,
        array.array(
            "i", [dest_start, dest_stride, src_start, src_stride, width, height, transparent]
        ),
    )


def load_tiles(
    framebuffer,
    first_pixel,
    row_stride,
    screen_width,
    belt_top,
    belt_path,
    plate_paths,
    transparent_index,
    pitch=None,
    plate_offset=(0, 0),
):
    """Build one tile per plate, return (tiles, tile_width, tile_height,
    belt_x)

    Call after the background is in the framebuffer"""
    belt = IndexedBMP(belt_path, transparent_index)
    slat_length, tile_width = belt.width, belt.height
    belt_x = screen_width - belt_top - tile_width
    if not 0 <= belt_x <= screen_width - tile_width:
        raise ValueError("belt_top puts the belt off the background")
    pitch = pitch or slat_length
    tile_pixels = tile_width * pitch
    slat = bytearray(2 * tile_width * slat_length)
    belt.draw_rotated(slat, 0, tile_width, tile_width * slat_length)

    plate_center = slat_length // 2 + plate_offset[0]
    window = plate_center - pitch // 2
    period = bytearray(2 * tile_pixels)
    # first the background under the belt, repeated
    overlay_rect(period, 0, tile_width, framebuffer,
                 first_pixel + belt_x, 0, tile_width, pitch)
    # then every slat
    copy = (window - slat_length + 1) // pitch
    while copy * pitch < window + pitch:
        copy_start = copy * pitch  # belt position of this slat's first row
        top = max(window, copy_start)
        bottom = min(window + pitch, copy_start + slat_length)
        if top < bottom:
            overlay_rect(
                period,
                (top - window) * tile_width,
                tile_width,
                slat,
                (top - copy_start) * tile_width,
                tile_width,
                tile_width,
                bottom - top,
                belt.transparent,
            )
        copy += 1
    del slat

    tiles = bytearray(2 * tile_pixels * len(plate_paths))
    for number, path in enumerate(plate_paths):
        tiles[2 * tile_pixels * number : 2 * tile_pixels * (number + 1)] = period
        plate = IndexedBMP(path, transparent_index)
        # Landscape position of the plate's top left on the slat...
        left = plate_center - plate.width // 2
        top = (tile_width - plate.height) // 2 + plate_offset[1]
        # ...and where that puts the turned plate in the tile.
        row = left - window
        column = tile_width - top - plate.height
        if not (0 <= row and row + plate.width <= pitch and 0 <= column
                and column + plate.height <= tile_width):
            raise ValueError(
                path + ": plate doesn't fit on one belt pitch; check its size, "
                "the pitch and plate_offset"
            )
        turned = bytearray(2 * plate.width * plate.height)
        plate.draw_rotated(turned, 0, plate.height, plate.width * plate.height)
        overlay_rect(
            tiles,
            number * tile_pixels + row * tile_width + column,
            tile_width,
            turned,
            0,
            plate.height,
            plate.height,
            plate.width,
            plate.transparent,
        )
    return tiles, tile_width, pitch, belt_x


@micropython.viper
def expand_row(dest: ptr16, row: ptr8, palette: ptr16, args: ptr32):
    """dest[args[1] + i * args[2]] = palette[row[i]] for i below args[0]."""
    count = args[0]
    dest_index = args[1]
    step = args[2]
    i = 0
    while i < count:
        dest[dest_index] = palette[row[i]]
        dest_index += step
        i += 1


@micropython.viper
def overlay(dest: ptr16, src: ptr16, args: ptr32):
    """Copy a rectangle, skipping the transparent color: args are dest
    start, dest stride, src start, src stride, width, height, transparent."""
    dest_row = args[0]
    dest_stride = args[1]
    src_row = args[2]
    src_stride = args[3]
    width = args[4]
    height = args[5]
    transparent = args[6]
    y = 0
    while y < height:
        i = 0
        while i < width:
            pixel = src[src_row + i]
            if pixel != transparent:
                dest[dest_row + i] = pixel
            i += 1
        dest_row += dest_stride
        src_row += src_stride
        y += 1

# belt
def new(
    screen_width,
    screen_height,
    first_pixel,
    row_stride,
    framebuffer_pixels,
    tile_count,
    tile_width,
    tile_height,
    belt_x,
):
    """Return (slots, params, seen) for a belt at belt_x on a screen of the
    given size. first_pixel and row_stride are the framebuffer's
    first_pixel_offset and row_stride, in pixels

    Slots start pointing at tile 0, call recycle(..., everything=True) to
    fill them with random plates."""
    if tile_count < 3:
        raise ValueError("need at least 3 plates so neighbours can differ")
    if not 0 <= belt_x <= screen_width - tile_width:
        raise ValueError("belt_x puts the belt off the screen")
    if row_stride < screen_width:
        raise ValueError("row_stride is narrower than the screen")
    last_pixel = first_pixel + (screen_height - 1) * row_stride + belt_x + tile_width
    if last_pixel > framebuffer_pixels:
        raise ValueError("framebuffer is too small for this screen size")
    # Enough slots to cover the screen, plus one that is always fully hidden.
    slot_count = (screen_height + tile_height - 1) // tile_height + 1
    slots = array.array("i", [0] * slot_count)
    params = array.array("i", [0] * PARAM_COUNT)
    params[PARAM_FIRST_PIXEL] = first_pixel
    params[PARAM_ROW_STRIDE] = row_stride
    params[PARAM_BELT_X] = belt_x
    params[PARAM_SCREEN_HEIGHT] = screen_height
    params[PARAM_TILE_WIDTH] = tile_width
    params[PARAM_TILE_HEIGHT] = tile_height
    params[PARAM_SLOT_COUNT] = slot_count
    seen = [False] * slot_count
    return slots, params, seen


def loop_length(params):
    """The belt loop's length in pixels"""
    return params[PARAM_SLOT_COUNT] * params[PARAM_TILE_HEIGHT]


def recycle(slots, params, seen, tile_count, randrange, everything=False):
    """Give a new plate to each slot that has been on screen and is now
    fully off it, never the same plate touching. everything=True
    refills every slot, for the first frame. Returns how many slots changed"""
    slot_count = params[PARAM_SLOT_COUNT]
    tile_height = params[PARAM_TILE_HEIGHT]
    screen_height = params[PARAM_SCREEN_HEIGHT]
    tile_pixels = params[PARAM_TILE_WIDTH] * tile_height
    length = slot_count * tile_height
    top = -params[PARAM_SCROLL] % length  # belt position at screen row 0
    changed = 0
    for slot in range(slot_count):
        # where the slot starts
        start = (slot * tile_height - top) % length
        if start < screen_height or start > length - tile_height:
            seen[slot] = True
            if not everything:
                continue
        elif not (seen[slot] or everything):
            continue
        seen[slot] = False
        before = slots[slot - 1] // tile_pixels
        after = slots[(slot + 1) % slot_count] // tile_pixels
        if everything:  # filling in order
            if slot == 0:
                before = -1
            if slot < slot_count - 1:
                after = -1
        tile = randrange(tile_count)
        while tile in (before, after):
            tile = randrange(tile_count)
        slots[slot] = tile * tile_pixels
        changed += 1
    return changed


@micropython.viper
def draw_belt(framebuffer: ptr16, tiles: ptr16, slots: ptr32, params: ptr32):
    """Copy the belt strip, scrolled by PARAM_SCROLL, into the framebuffer."""
    first_pixel = params[PARAM_FIRST_PIXEL]
    row_stride = params[PARAM_ROW_STRIDE]
    belt_x = params[PARAM_BELT_X]
    screen_height = params[PARAM_SCREEN_HEIGHT]
    tile_width = params[PARAM_TILE_WIDTH]
    tile_height = params[PARAM_TILE_HEIGHT]
    slot_count = params[PARAM_SLOT_COUNT]
    scroll = params[PARAM_SCROLL]
    quad_width = tile_width - (tile_width & 3)

    position = slot_count * tile_height - scroll
    if position >= slot_count * tile_height:
        position -= slot_count * tile_height
    slot = position // tile_height
    tile_row = position - slot * tile_height
    source = slots[slot] + tile_row * tile_width

    row_start = first_pixel + belt_x
    y = 0
    while y < screen_height:
        dest = row_start
        quad_end = dest + quad_width
        while dest < quad_end:
            framebuffer[dest] = tiles[source]
            framebuffer[dest + 1] = tiles[source + 1]
            framebuffer[dest + 2] = tiles[source + 2]
            framebuffer[dest + 3] = tiles[source + 3]
            dest += 4
            source += 4
        row_end = row_start + tile_width
        while dest < row_end:
            framebuffer[dest] = tiles[source]
            dest += 1
            source += 1
        row_start += row_stride
        tile_row += 1
        if tile_row == tile_height:  # on to the next slot's tile
            tile_row = 0
            slot += 1
            if slot == slot_count:
                slot = 0
            source = slots[slot]
        y += 1
