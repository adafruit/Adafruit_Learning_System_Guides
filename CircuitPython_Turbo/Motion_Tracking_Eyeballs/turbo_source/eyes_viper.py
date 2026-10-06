# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Animated monster eyes for CircuitPython turbo, cut down for the motion
tracking project

A port of Adafruit_Monster_Eyes Arduino library It reads the same
config.eye files and eye folders off CIRCUITPY.
"""

import array
import json
import math
import random
import struct

import micropython
from micropython import const

# pylint: disable=too-many-lines, undefined-variable, too-many-locals, too-many-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-instance-attributes, too-many-arguments, invalid-name

_TICKS_MASK = const(0x1FFFFFFF)  # supervisor.ticks_ms() wraps at 2**29

# The Arduino library caps the sclera texture at 4 KB, since it is mostly
# flat color; the iris is loaded at full size.
_SCLERA_MAX_BYTES = const(4096)

from supervisor import ticks_ms  # pylint: disable=wrong-import-position,wrong-import-order

def _elapsed(now, then):
    """Milliseconds from then to now, across a ticks_ms() wrap."""
    return (now - then) & _TICKS_MASK

# The per-eye block. Offsets and sizes in slots 0-16 and 32 are in BYTES,
# the assembly kernel's unit; the viper kernels halve them for ptr16
# indexing. The assembly reads slot n as [block, 4n], so slots 0-31 must stay
# where they are; slots 25-31 are its scratch; 32 and up only Python and
# lid_spans() read.
_B_DEST = const(0)  # the eye's top-left in dest (asm: then the current row)
_B_STRIDE = const(1)  # from one dest row to the next
_B_SIZE = const(2)  # eye width and height in pixels, even
_B_HALF = const(3)
_B_MAP_X = const(4)  # map position under the window's bottom-left
_B_MAP_Y = const(5)
_B_MAP_RADIUS = const(6)
_B_MAP_DIAMETER = const(7)
_B_POLAR = const(8)  # where each table starts in data
_B_DISPLACE = const(9)
_B_BOUNDS = const(10)
_B_IRIS = const(11)
_B_IRIS_WIDTH = const(12)  # texture sizes in pixels
_B_IRIS_HEIGHT = const(13)
_B_SCLERA = const(14)
_B_SCLERA_WIDTH = const(15)
_B_SCLERA_HEIGHT = const(16)
_B_IRIS_ANGLE = const(17)  # rotation, 0-1023
_B_SCLERA_ANGLE = const(18)
_B_IRIS_MIRROR = const(19)  # 0, or 1023 to mirror the texture
_B_SCLERA_MIRROR = const(20)
_B_PUPIL_SCALE = const(21)  # iris_height * 256 / iris fraction
_B_PUPIL_COLOR = const(22)  # RGB565
_B_BACK_COLOR = const(23)
_B_EYELID_COLOR = const(24)
_B_LIDS = const(32)  # the lid tables in data
_B_UPPER_LID = const(33)  # how open, 0-65536
_B_LOWER_LID = const(34)
_B_LID_MIRROR = const(35)  # nonzero to mirror the eyelid shapes
_B_WORDS = const(36)

# Angular resolution past 512 is wasted: the renderer indexes as
# (angle * width) >> 10 with angle 0-1023, and distance is 0-127.
_TEX_MAX_W = const(512)
_TEX_MAX_H = const(128)

# ===========================================================================
#  KERNELS
# ===========================================================================

@micropython.viper
def lid_spans(data: ptr16, block: ptr32):
    """Each column's visible rows for one eye, into data's bounds table as
    low | high << 8, or 255 | 0 when shut. render_eye_asm() reads these."""
    size = block[_B_SIZE]
    lids = block[_B_LIDS] >> 1
    bounds = block[_B_BOUNDS] >> 1
    upper_factor = block[_B_UPPER_LID]
    lower_factor = block[_B_LOWER_LID]
    lid_mirror = block[_B_LID_MIRROR]
    x = 0
    while x < size:
        column = x
        if lid_mirror:
            column = size - 1 - x
        upper_open = int(data[lids + column])
        upper_closed = int(data[lids + size + column])
        lower_open = int(data[lids + size + size + column])
        lower_closed = int(data[lids + size + size + size + column])
        # closed + (int)(0.5 + factor * (open - closed)), as in the C:
        # truncate toward zero, not floor, or the lower lid (whose span is
        # negative) lands a row off.
        low = lower_factor * (lower_open - lower_closed) + 32768
        if low >= 0:
            low = lower_closed + (low >> 16)
        else:
            low = lower_closed - ((0 - low) >> 16)
        high = upper_factor * (upper_open - upper_closed) + 32768
        if high >= 0:
            high = upper_closed + (high >> 16)
        else:
            high = upper_closed - ((0 - high) >> 16)
        if low > size - 1:
            low = size - 1
        elif low < 0:
            low = 0
        if high > size - 1:
            high = size - 1
        elif high < 0:
            high = 0
        if low >= high:
            low = 255
            high = 0
        data[bounds + x] = low | (high << 8)
        x += 1

@micropython.viper
def fill(dest: ptr16, args: ptr32):
    """Fill a rectangle: args are start, width, height, row stride, color."""
    row_start = args[0]
    width = args[1]
    height = args[2]
    stride = args[3]
    color = args[4]
    y = 0
    while y < height:
        i = row_start
        end = row_start + width
        while i < end:
            dest[i] = color
            i += 1
        row_start += stride
        y += 1

@micropython.viper
def bgr_row(dest: ptr16, row: ptr8, args: ptr32):
    """One row of a 24-bit BMP to RGB565, resampled: dest[args[0] + i] is
    source pixel i * args[2] // args[1], for i below args[1]."""
    start = args[0]
    count = args[1]
    source_width = args[2]
    i = 0
    while i < count:
        s = (i * source_width // count) * 3  # stored blue, green, red
        blue = int(row[s])
        green = int(row[s + 1])
        red = int(row[s + 2])
        dest[start + i] = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        i += 1

@micropython.viper
def eyelid_row(extent: ptr16, row: ptr8, args: ptr32):
    """Widen each column's span of lit pixels by one row of a 1-bit BMP.
    args are image width, eye size, image row, palette index of "lit".
    extent holds size minimum rows, then size maximum rows."""
    width = args[0]
    size = args[1]
    image_row = args[2]
    lit = args[3]
    sx = 0
    while sx < width:
        if ((int(row[sx >> 3]) >> (7 - (sx & 7))) & 1) == lit:
            column = sx * size // width
            if image_row < int(extent[column]):
                extent[column] = image_row
            if image_row > int(extent[size + column]):
                extent[size + column] = image_row
        sx += 1

@micropython.viper
def address(buf: ptr8) -> int:
    """Where a buffer's data lives, as an int, for the asm kernels."""
    return int(buf)

def _address(buf):
    value = address(buf)
    if not 0 < value < 0x40000000:  # must stay a small int
        raise ValueError("buffer address 0x%x can't be passed to the asm kernels" % value)
    return value

@micropython.asm_thumb
def render_eye_asm(r0, r1, r2, r3):
    # Called as render_eye_asm(block, data, dest), all addresses. Slot n of
    # the block is at byte offset 4n, which is what the immediates below use.
    ldr(r0, [r3, 0])
    ldr(r1, [r3, 4])
    ldr(r2, [r3, 8])
    push({r0})  # the object to return
    asr(r0, r0, 1)
    asr(r1, r1, 1)
    asr(r2, r2, 1)
    mov(r7, r0)
    mov(r3, r8)  # r8-r11 belong to the caller
    mov(r4, r9)
    mov(r5, r10)
    mov(r6, r11)
    push({r3, r4, r5, r6})
    ldr(r3, [r7, 0])  # offsets into data and dest become addresses
    add(r3, r3, r2)
    str(r3, [r7, 0])
    ldr(r3, [r7, 32])
    add(r3, r3, r1)
    str(r3, [r7, 108])
    ldr(r3, [r7, 36])
    add(r3, r3, r1)
    str(r3, [r7, 112])
    ldr(r3, [r7, 40])
    add(r3, r3, r1)
    str(r3, [r7, 116])
    ldr(r3, [r7, 44])
    add(r3, r3, r1)
    str(r3, [r7, 120])
    ldr(r3, [r7, 56])
    add(r3, r3, r1)
    str(r3, [r7, 124])
    ldr(r0, [r7, 8])  # sy = size - 1, the top row
    sub(r0, 1)
    str(r0, [r7, 100])

    label(ROW)
    ldr(r0, [r7, 100])
    mov(r9, r0)  # sy
    ldr(r1, [r7, 20])
    add(r1, r1, r0)
    mov(r10, r1)  # yy = map_y + sy
    ldr(r2, [r7, 12])  # half
    sub(r1, r0, r2)
    asr(r3, r1, 31)  # -1 below the centre
    mov(r12, r3)
    eor(r1, r3)  # displacement row: |sy - half| folded
    mul(r1, r2)
    lsl(r1, r1, 1)
    ldr(r3, [r7, 112])
    add(r1, r1, r3)
    str(r1, [r7, 104])  # this row of the displacement table
    ldr(r6, [r7, 0])  # output pointer: row start
    ldr(r0, [r7, 116])
    sub(r0, r0, r6)
    mov(r11, r0)  # bounds address = r11 + output pointer
    ldr(r3, [r7, 16])  # map_x + x, x = 0
    lsl(r0, r2, 1)
    add(r0, r0, r6)
    mov(r8, r0)  # end of the left half
    sub(r0, r2, 1)
    lsl(r0, r0, 1)
    add(r4, r1, r0)  # displacement for x = 0 is the far end of the row

    label(LEFT)
    mov(r0, r11)
    add(r0, r0, r6)
    ldrh(r0, [r0, 0])  # lid span: low | high << 8
    mov(r2, r9)
    lsl(r1, r0, 24)
    lsr(r1, r1, 24)
    cmp(r2, r1)
    blt(L_LID)
    lsr(r0, r0, 8)
    cmp(r2, r0)
    bgt(L_LID)
    ldrh(r0, [r4, 0])  # displacement: dx | dy << 8
    lsl(r1, r0, 24)
    lsr(r1, r1, 24)
    cmp(r1, 255)
    beq(L_LID)  # outside the eyeball
    sub(r1, r3, r1)  # LEFT: mx = map_x + x - dx
    lsr(r0, r0, 8)
    mov(r2, r12)
    eor(r0, r2)
    sub(r0, r0, r2)  # dy, negated below the centre
    mov(r2, r10)
    add(r0, r0, r2)  # my
    ldr(r2, [r7, 28])
    cmp(r1, r2)
    bcs(L_BACK)  # unsigned, so this catches mx < 0 too
    cmp(r0, r2)
    bcs(L_BACK)
    ldr(r2, [r7, 24])
    sub(r1, r1, r2)
    sub(r0, r0, r2)
    asr(r5, r0, 31)  # -1 in the map's lower half
    eor(r0, r5)
    mul(r0, r2)
    asr(r2, r1, 31)  # -1 in the map's left half
    eor(r1, r2)
    add(r0, r0, r1)
    eor(r2, r5)  # -1 in the mirrored quadrants
    lsl(r0, r0, 1)
    ldr(r1, [r7, 108])
    add(r0, r0, r1)
    ldrh(r0, [r0, 0])  # angle | (dist + 128) << 8
    lsl(r1, r0, 24)
    lsr(r1, r1, 24)
    lsr(r2, r2, 22)  # 0 or 1023
    eor(r1, r2)  # 1023 - angle where mirrored
    lsr(r5, r5, 31)
    lsl(r5, r5, 9)
    add(r1, r1, r5)  # + 512 in the lower half
    lsr(r0, r0, 8)
    beq(L_BACK)  # dist -128: back of the eye
    sub(r0, 128)
    bmi(L_IRIS)
    ldr(r2, [r7, 72])  # sclera
    add(r1, r1, r2)
    lsl(r1, r1, 22)
    lsr(r1, r1, 22)
    ldr(r2, [r7, 80])
    eor(r1, r2)
    ldr(r2, [r7, 60])
    mul(r1, r2)
    lsr(r1, r1, 10)
    ldr(r5, [r7, 64])
    mul(r0, r5)
    lsr(r0, r0, 7)
    mul(r0, r2)
    add(r0, r0, r1)
    lsl(r0, r0, 1)
    ldr(r1, [r7, 124])
    add(r0, r0, r1)
    ldrh(r0, [r0, 0])
    b(L_STORE)
    label(L_IRIS)
    neg(r0, r0)
    ldr(r2, [r7, 84])
    mul(r0, r2)
    lsr(r0, r0, 15)
    ldr(r2, [r7, 52])
    cmp(r0, r2)
    bcs(L_PUPIL)
    ldr(r2, [r7, 68])
    add(r1, r1, r2)
    lsl(r1, r1, 22)
    lsr(r1, r1, 22)
    ldr(r2, [r7, 76])
    eor(r1, r2)
    ldr(r2, [r7, 48])
    mul(r1, r2)
    lsr(r1, r1, 10)
    mul(r0, r2)
    add(r0, r0, r1)
    lsl(r0, r0, 1)
    ldr(r1, [r7, 120])
    add(r0, r0, r1)
    ldrh(r0, [r0, 0])
    b(L_STORE)
    label(L_PUPIL)
    ldr(r0, [r7, 88])
    b(L_STORE)
    label(L_BACK)
    ldr(r0, [r7, 92])
    b(L_STORE)
    label(L_LID)
    ldr(r0, [r7, 96])
    label(L_STORE)
    strh(r0, [r6, 0])
    add(r6, 2)
    sub(r4, 2)  # LEFT: displacement runs backwards
    add(r3, 1)
    mov(r0, r8)
    cmp(r6, r0)
    bcc_w(LEFT)

    ldr(r4, [r7, 104])  # right half: displacement runs forwards from 0
    ldr(r0, [r7, 12])
    lsl(r0, r0, 1)
    add(r0, r0, r6)
    mov(r8, r0)

    label(RIGHT)
    mov(r0, r11)
    add(r0, r0, r6)
    ldrh(r0, [r0, 0])
    mov(r2, r9)
    lsl(r1, r0, 24)
    lsr(r1, r1, 24)
    cmp(r2, r1)
    blt(R_LID)
    lsr(r0, r0, 8)
    cmp(r2, r0)
    bgt(R_LID)
    ldrh(r0, [r4, 0])
    lsl(r1, r0, 24)
    lsr(r1, r1, 24)
    cmp(r1, 255)
    beq(R_LID)
    add(r1, r1, r3)  # RIGHT: mx = map_x + x + dx
    lsr(r0, r0, 8)
    mov(r2, r12)
    eor(r0, r2)
    sub(r0, r0, r2)
    mov(r2, r10)
    add(r0, r0, r2)
    ldr(r2, [r7, 28])
    cmp(r1, r2)
    bcs(R_BACK)
    cmp(r0, r2)
    bcs(R_BACK)
    ldr(r2, [r7, 24])
    sub(r1, r1, r2)
    sub(r0, r0, r2)
    asr(r5, r0, 31)
    eor(r0, r5)
    mul(r0, r2)
    asr(r2, r1, 31)
    eor(r1, r2)
    add(r0, r0, r1)
    eor(r2, r5)
    lsl(r0, r0, 1)
    ldr(r1, [r7, 108])
    add(r0, r0, r1)
    ldrh(r0, [r0, 0])
    lsl(r1, r0, 24)
    lsr(r1, r1, 24)
    lsr(r2, r2, 22)
    eor(r1, r2)
    lsr(r5, r5, 31)
    lsl(r5, r5, 9)
    add(r1, r1, r5)
    lsr(r0, r0, 8)
    beq(R_BACK)
    sub(r0, 128)
    bmi(R_IRIS)
    ldr(r2, [r7, 72])
    add(r1, r1, r2)
    lsl(r1, r1, 22)
    lsr(r1, r1, 22)
    ldr(r2, [r7, 80])
    eor(r1, r2)
    ldr(r2, [r7, 60])
    mul(r1, r2)
    lsr(r1, r1, 10)
    ldr(r5, [r7, 64])
    mul(r0, r5)
    lsr(r0, r0, 7)
    mul(r0, r2)
    add(r0, r0, r1)
    lsl(r0, r0, 1)
    ldr(r1, [r7, 124])
    add(r0, r0, r1)
    ldrh(r0, [r0, 0])
    b(R_STORE)
    label(R_IRIS)
    neg(r0, r0)
    ldr(r2, [r7, 84])
    mul(r0, r2)
    lsr(r0, r0, 15)
    ldr(r2, [r7, 52])
    cmp(r0, r2)
    bcs(R_PUPIL)
    ldr(r2, [r7, 68])
    add(r1, r1, r2)
    lsl(r1, r1, 22)
    lsr(r1, r1, 22)
    ldr(r2, [r7, 76])
    eor(r1, r2)
    ldr(r2, [r7, 48])
    mul(r1, r2)
    lsr(r1, r1, 10)
    mul(r0, r2)
    add(r0, r0, r1)
    lsl(r0, r0, 1)
    ldr(r1, [r7, 120])
    add(r0, r0, r1)
    ldrh(r0, [r0, 0])
    b(R_STORE)
    label(R_PUPIL)
    ldr(r0, [r7, 88])
    b(R_STORE)
    label(R_BACK)
    ldr(r0, [r7, 92])
    b(R_STORE)
    label(R_LID)
    ldr(r0, [r7, 96])
    label(R_STORE)
    strh(r0, [r6, 0])
    add(r6, 2)
    add(r4, 2)  # RIGHT: displacement runs forwards
    add(r3, 1)
    mov(r0, r8)
    cmp(r6, r0)
    bcc_w(RIGHT)

    ldr(r0, [r7, 0])  # next row
    ldr(r1, [r7, 4])
    add(r0, r0, r1)
    str(r0, [r7, 0])
    ldr(r0, [r7, 100])
    sub(r0, 1)
    str(r0, [r7, 100])
    bpl_w(ROW)

    pop({r3, r4, r5, r6})
    mov(r8, r3)
    mov(r9, r4)
    mov(r10, r5)
    mov(r11, r6)
    pop({r0})

class _Bmp:
    """Header of an uncompressed 1- or 24-bit BMP."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as file:
            header = file.read(54)
            if len(header) < 54 or header[:2] != b"BM":
                raise ValueError(path + ": not a BMP file")
            (self.data_offset, info_size, self.width, height, _planes, self.bits,
             compression) = struct.unpack_from("<IIiiHHI", header, 10)
            if info_size < 40 or compression != 0 or self.bits not in (1, 24):
                raise ValueError(path + ": needs an uncompressed 1- or 24-bit BMP")
            self.top_down = height < 0  # positive height stores rows bottom up
            self.height = abs(height)
            self.row_bytes = ((self.width * self.bits + 31) // 32) * 4
            self.lit = 1
            if self.bits == 1:  # the lighter palette entry is "lit"
                file.seek(14 + info_size)
                palette = file.read(8)
                self.lit = 1 if sum(palette[4:7]) > sum(palette[0:3]) else 0

    def file_row(self, image_row):
        """Byte offset of an image row, counting from the top."""
        row = image_row if self.top_down else self.height - 1 - image_row
        return self.data_offset + row * self.row_bytes


def _texture_size(bmp, max_bytes):
    """Size to load a texture at: the source capped to what the renderer can
    address, then the longer side shrunk until it fits max_bytes. As in the
    Arduino loader, too large means blurrier, not rejected."""
    width = min(bmp.width, _TEX_MAX_W)
    height = min(bmp.height, _TEX_MAX_H)
    if max_bytes:
        while width * height * 2 > max_bytes and (width > 8 or height > 4):
            if width * bmp.height > height * bmp.width:
                if width > 8:
                    width -= 1
                else:
                    height -= 1
            elif height > 4:
                height -= 1
            else:
                width -= 1
    return width, height

def _open_bmp(path, bits, label):
    """A config.eye BMP, checked for depth; None means use the solid color."""
    if not path:
        print("%s: none -- solid color" % label)
        return None
    try:
        bmp = _Bmp(_resolve(path))
    except (OSError, ValueError) as error:
        print("%s: %s unusable (%s) -- solid color" % (label, path, error))
        return None
    if bmp.bits != bits:
        print("%s: %s is %d-bit, needs %d -- skipped" % (label, path, bmp.bits, bits))
        return None
    if bits == 1 and bmp.height < 2:
        return None
    return bmp

def _load_texture(bmp, data, offset, width, height):
    """Decode a 24-bit BMP into data[offset:], resampled to width x height."""
    row = bytearray(bmp.row_bytes)
    args = array.array("i", [0, width, bmp.width])
    with open(bmp.path, "rb") as file:
        for y in range(height):
            file.seek(bmp.file_row(y * bmp.height // height))
            file.readinto(row)
            args[0] = offset + y * width
            bgr_row(data, row, args)

def _load_eyelid(bmp, data, open_offset, closed_offset, size, *, upper):
    """Per column of a 1-bit eyelid shape, its topmost and bottommost lit
    rows, scaled to the eye and flipped to +Y up. An upper lid's top edge is
    where it rests open and its bottom edge where it closes; a lower lid is
    the other way round."""
    extent = array.array("H", [0xFFFF]) * size + array.array("H", [0]) * size
    row = bytearray(bmp.row_bytes)
    args = array.array("i", [bmp.width, size, 0, bmp.lit])
    with open(bmp.path, "rb") as file:
        for y in range(bmp.height):
            file.seek(bmp.file_row(y))
            file.readinto(row)
            args[2] = y
            eyelid_row(extent, row, args)
    span = bmp.height - 1
    for column in range(size):
        if extent[column] == 0xFFFF:
            continue  # nothing lit: keep the "no eyelid" value
        top = min(max(extent[column] * (size - 1) // span, 0), size - 1)
        bottom = min(max(extent[size + column] * (size - 1) // span, 0), size - 1)
        if upper:
            data[open_offset + column] = size - 1 - top
            data[closed_offset + column] = size - 1 - bottom
        else:
            data[closed_offset + column] = size - 1 - top
            data[open_offset + column] = size - 1 - bottom

# ===========================================================================
#  CONFIG.EYE
# ===========================================================================

def _clean_json(text):
    """Strip // and /* */ comments and trailing commas, outside strings.
    config.eye files carry comments, which json.loads() rejects."""
    out = []
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_string = False
        elif c == '"':
            in_string = True
            out.append(c)
        elif c == "/" and text[i + 1 : i + 2] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif c == "/" and text[i + 1 : i + 2] == "*":
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        elif c in "}]":
            # Drop a comma left dangling before the close.
            j = len(out) - 1
            while j >= 0 and out[j] in " \t\r\n":
                j -= 1
            if j >= 0 and out[j] == ",":
                del out[j]
            out.append(c)
        else:
            out.append(c)
        i += 1
    return "".join(out)

def _channel(item):
    """One color channel, 0-255, from an int, a "0xFF" string or a 0.0-1.0
    float."""
    if isinstance(item, float):
        item = int(item * 255.999)
    elif isinstance(item, str):
        item = int(item, 0)
    return min(max(int(item), 0), 255)


def _dwim(value, default=0):
    """M4_Eyes' "do what I mean" number: 42, "0x2A", [255, 0, 0],
    ["0xFF", 0, 0] or [1.0, 0.0, 0.0]. Three-element lists become RGB565;
    shorter lists use their first element."""
    while isinstance(value, (list, tuple)):
        if len(value) >= 3:
            red = _channel(value[0])
            green = _channel(value[1])
            blue = _channel(value[2])
            return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        value = value[0] if value else None
    if value is None:
        return default
    if isinstance(value, float):
        return int(value + 0.5)
    if isinstance(value, str):
        return int(value, 0)
    if isinstance(value, int):  # bool included: True is 1
        return int(value)
    return default

def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def _angle(value):
    """config.eye angle (0-1023, or a float fraction of a turn) to the
    renderer's start angle, which runs the other way."""
    if isinstance(value, float):
        return 1023 - (int(value * 1024) & 1023)
    return 1023 - (int(value) & 1023)

class Settings:
    """Everything a config.eye can change, at the Arduino library's
    defaults. Colors are RGB565."""

    def __init__(self):
        self.display_size = 0  # 0 fills what the screen gives one eye
        self.eye_radius = 0  # 0 derives these three from display_size
        self.iris_radius = 0
        self.slit_pupil_radius = 0  # 0 round, -1 derived
        self.coverage = 0.6
        self.pupil_color = 0x0000
        self.back_color = 0x5000
        self.eyelid_color = 0x0000
        self.iris_color = 0x001F
        self.sclera_color = 0xFFFF
        self.pupil_min = 0.05
        self.pupil_max = 0.25
        self.tracking = True
        self.squint = 0.5
        self.fixate = 7  # map pixels
        self.iris_file = ""
        self.sclera_file = ""
        self.upper_file = ""
        self.lower_file = ""
        # Keys that may differ between the two eyes; see _Eye.
        self.iris_spin = 0.0
        self.sclera_spin = 0.0
        self.iris_start = 512
        self.sclera_start = 512
        self.iris_mirror = 0
        self.sclera_mirror = 0
        self.eyelid_mirror = True
        # For scaling: did the config set geometry, and for what eye size?
        self.geometry_from_config = False
        self.config_display_size = 0

    def apply(self, block):
        """Apply one JSON object: the root, or a single eye's side block."""
        if not isinstance(block, dict):
            return
        for key, attr in (
            ("displaySize", "display_size"),
            ("eyeRadius", "eye_radius"),
            ("irisRadius", "iris_radius"),
            ("slitPupilRadius", "slit_pupil_radius"),
            ("fixate", "fixate"),
            ("pupilColor", "pupil_color"),
            ("backColor", "back_color"),
            ("irisColor", "iris_color"),
            ("scleraColor", "sclera_color"),
        ):
            if key in block:
                setattr(self, attr, _dwim(block[key], getattr(self, attr)))
        if "eyeRadius" in block or "irisRadius" in block or "slitPupilRadius" in block:
            self.geometry_from_config = True
        if "displaySize" in block:
            self.config_display_size = self.display_size
        for key, attr in (
            ("coverage", "coverage"),
            ("pupilMin", "pupil_min"),
            ("pupilMax", "pupil_max"),
            ("squint", "squint"),
        ):
            if _number(block.get(key)):
                setattr(self, attr, float(block[key]))
        if "eyelidIndex" in block:  # legacy grey index
            self.eyelid_color = (_dwim(block["eyelidIndex"]) & 0xFF) * 0x0101
        if "eyelidColor" in block:
            self.eyelid_color = _dwim(block["eyelidColor"], self.eyelid_color)
        if isinstance(block.get("tracking"), bool):
            self.tracking = block["tracking"]
        for key, attr in (
            ("irisTexture", "iris_file"),
            ("scleraTexture", "sclera_file"),
            ("upperEyelid", "upper_file"),
            ("lowerEyelid", "lower_file"),
        ):
            if isinstance(block.get(key), str):
                setattr(self, attr, block[key])
        apply_per_eye(block, self)

def apply_per_eye(block, target):
    """Apply the keys that may differ between eyes to target, a Settings or
    an _Eye."""
    if not isinstance(block, dict):
        return
    for key, attr in (("irisSpin", "iris_spin"), ("scleraSpin", "sclera_spin")):
        if _number(block.get(key)):
            setattr(target, attr, float(block[key]))
    for key, attr in (("irisAngle", "iris_start"), ("scleraAngle", "sclera_start")):
        if _number(block.get(key)):
            setattr(target, attr, _angle(block[key]))
    for key, attr in (("irisMirror", "iris_mirror"), ("scleraMirror", "sclera_mirror")):
        if key in block:
            setattr(target, attr, 1023 if block[key] else 0)
    if "eyelidMirror" in block:
        target.eyelid_mirror = bool(block["eyelidMirror"])

class _Eye:  # pylint: disable=too-few-public-methods
    """One eye: its per-eye settings, its kernel block, and its animation
    state. The character's right eye mirrors the left: opposite spin, half a
    turn round, unmirrored eyelids."""

    def __init__(self, settings, right_eye):
        self.iris_spin = -settings.iris_spin if right_eye else settings.iris_spin
        self.sclera_spin = -settings.sclera_spin if right_eye else settings.sclera_spin
        self.iris_start = (settings.iris_start + (512 if right_eye else 0)) & 1023
        self.sclera_start = settings.sclera_start
        self.iris_mirror = settings.iris_mirror
        self.sclera_mirror = settings.sclera_mirror
        self.eyelid_mirror = settings.eyelid_mirror != right_eye
        self.block = array.array("i", [0]) * _B_WORDS
        self.block_address = 0
        self.origin_x = self.origin_y = 0
        self.upper = self.lower = 1.0  # smoothed lid tracking
        # Rotation is a phase advanced by elapsed time, in 1/1024 turns,
        # rather than start + spin * uptime: a CircuitPython float has too
        # few bits for the uptime product to stay smooth for long.
        self.iris_phase = self.sclera_phase = 0.0

def _resolve(path):
    """config.eye paths are relative to the drive's root."""
    return path if path.startswith("/") else "/" + path

# ===========================================================================
#  THE EYES
# ===========================================================================

class Eyes:
    """Two animated eyes side by side on one screen, looking wherever
    set_gaze() points them.

    Eye 0 is the character's RIGHT eye, so it sits on the viewer's LEFT, and
    reads the "right" block of config.eye; eye 1 is the left eye.

    Use: begin(), attach(screen), then each frame update(), draw() and
    present(); set_gaze() whenever the gaze should change.
    """

    def __init__(self, screen_width, screen_height, config_path="/config.eye", gap=0):
        """
        :param screen_width: screen width in pixels
        :param screen_height: screen height in pixels
        :param config_path: config.eye on CIRCUITPY. If it's missing or won't
            parse, the built-in defaults are used.
        :param gap: screen pixels to keep blank between the eyes. Each eye
            stays centered in its half of the screen, so half the gap is left
            at the outer edges too. A displaySize in config.eye wins.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.config_path = config_path
        self.gap = gap
        self.settings = Settings()
        self.size = self.top = 0
        self.data = None
        self.eyes = []
        # Set by begin(): geometry and the kernels' addresses
        self.map_radius = 0
        self.gaze_radius = 1.0
        self._lids = 0
        self._data_address = 0
        self._iris_height = 1
        # Set by begin() from the config: lid tracking and pupil range
        self._track_factor = 1.0
        self._iris_min = 0.0
        self._iris_range = 0.0
        # Animation state, reset by begin()
        self.gaze_map_x = self.gaze_map_y = 0.0
        self._iris_prev = [0.0] * 7
        self._iris_next = [0.0] * 7
        self._iris_frame = 0
        self.iris_fraction = 0.5
        self._last_update = 0
        # Set by attach(): the screen and the back buffer
        self._screen = self._back = None
        self._back_address = 0
        self._band = (0, 0)

    # -- startup ------------------------------------------------------------

    def begin(self):
        """Read the config, build the tables, load the textures and lids."""
        settings = self.settings
        doc = self._load_config(self.config_path)
        self.eyes = [_Eye(settings, True), _Eye(settings, False)]
        if doc:
            apply_per_eye(doc.get("right"), self.eyes[0])
            apply_per_eye(doc.get("left"), self.eyes[1])

        max_size = min(self.screen_width // 2, self.screen_height)
        # M4_Eyes configs are drawn for a 240 px eye unless they say otherwise.
        reference = settings.config_display_size or 240
        size = settings.display_size or max_size - self.gap
        size = min(max(size, 32), 240, max_size) & ~1
        settings.display_size = size
        if settings.geometry_from_config and size != reference:
            # Scale the config's geometry to the eye size really used, so a
            # 144 px eye looks like the 240 px one it was written for.
            factor = size / reference
            settings.eye_radius = int(settings.eye_radius * factor + 0.5)
            settings.iris_radius = int(settings.iris_radius * factor + 0.5)
            if settings.slit_pupil_radius > 0:
                settings.slit_pupil_radius = int(settings.slit_pupil_radius * factor + 0.5)
            settings.fixate = int(settings.fixate * factor + 0.5)
            print("config geometry scaled by %.3f for a %d px eye" % (factor, size))
        self._finalize()
        self.size = size
        half = size // 2

        self.map_radius = int(settings.eye_radius * math.pi * settings.coverage + 0.5)
        map_radius = self.map_radius
        if map_radius < 8:
            raise ValueError("eye too small: map radius %d" % map_radius)
        self._gaze_radius_init()

        # Size every table, then allocate data once.
        iris_bmp = _open_bmp(settings.iris_file, 24, "iris")
        sclera_bmp = _open_bmp(settings.sclera_file, 24, "sclera")
        iris_w, iris_h = _texture_size(iris_bmp, None) if iris_bmp else (1, 1)
        sclera_w, sclera_h = (
            _texture_size(sclera_bmp, _SCLERA_MAX_BYTES) if sclera_bmp else (1, 1)
        )
        polar = 0
        displace = polar + map_radius * map_radius
        iris = displace + half * half
        sclera = iris + iris_w * iris_h
        lids = sclera + sclera_w * sclera_h
        bounds = lids + 4 * size
        total = bounds + size
        try:
            self.data = array.array("H", [0]) * total
        except MemoryError as error:
            raise MemoryError("no room for %d bytes of eye tables" % (2 * total)) from error
        data = self.data
        print("eye %d px, map radius %d, tables %d bytes" % (size, map_radius, 2 * total))

        t0 = ticks_ms()
        iris_map_radius = self._screen2map(settings.iris_radius)
        _build_polar(data, polar, map_radius, iris_map_radius, settings.slit_pupil_radius)
        t1 = ticks_ms()
        _build_displace(data, displace, half, settings.eye_radius, map_radius)
        print("polar map %d ms, displacement %d ms" % (_elapsed(t1, t0), _elapsed(ticks_ms(), t1)))

        for bmp, offset, width, height, color, label in (
            (iris_bmp, iris, iris_w, iris_h, settings.iris_color, "iris"),
            (sclera_bmp, sclera, sclera_w, sclera_h, settings.sclera_color, "sclera"),
        ):
            if bmp:
                _load_texture(bmp, data, offset, width, height)
                print("%s: %s -> %dx%d" % (label, bmp.path, width, height))
            else:
                data[offset] = color

        # Lids: "fully out of the way" until a file says otherwise.
        for i in range(size):
            data[lids + i] = data[lids + size + i] = size - 1
        for path, open_offset, closed_offset, upper in (
            (settings.upper_file, lids, lids + size, True),
            (settings.lower_file, lids + 2 * size, lids + 3 * size, False),
        ):
            bmp = _open_bmp(path, 1, "upper eyelid" if upper else "lower eyelid")
            if bmp:
                _load_eyelid(bmp, data, open_offset, closed_offset, size, upper=upper)
        self._lids = lids

        slice_width = self.screen_width // 2
        self.top = (self.screen_height - size) // 2
        for number, eye in enumerate(self.eyes):
            eye.origin_x = number * slice_width + (slice_width - size) // 2
            block = eye.block
            for slot, value in (
                (_B_SIZE, size),
                (_B_HALF, half),
                (_B_MAP_RADIUS, map_radius),
                (_B_MAP_DIAMETER, 2 * map_radius),
                (_B_POLAR, 2 * polar),
                (_B_DISPLACE, 2 * displace),
                (_B_BOUNDS, 2 * bounds),
                (_B_IRIS, 2 * iris),
                (_B_IRIS_WIDTH, iris_w),
                (_B_IRIS_HEIGHT, iris_h),
                (_B_SCLERA, 2 * sclera),
                (_B_SCLERA_WIDTH, sclera_w),
                (_B_SCLERA_HEIGHT, sclera_h),
                (_B_IRIS_MIRROR, eye.iris_mirror),
                (_B_SCLERA_MIRROR, eye.sclera_mirror),
                (_B_PUPIL_COLOR, settings.pupil_color),
                (_B_BACK_COLOR, settings.back_color),
                (_B_EYELID_COLOR, settings.eyelid_color),
                (_B_LIDS, 2 * lids),
                (_B_LID_MIRROR, 1 if eye.eyelid_mirror else 0),
            ):
                block[slot] = value
            eye.block_address = _address(block)
        self._data_address = _address(data)
        self._iris_height = iris_h
        self._reset_animation()

    def _load_config(self, path):
        """Apply config.eye to settings; return the parsed document, or None."""
        try:
            with open(path, "r") as file:
                text = file.read()
        except OSError:
            print("no %s; using built-in defaults" % path)
            return None
        try:
            doc = json.loads(_clean_json(text))
        except ValueError as error:
            print("%s: parse error (%s); using built-in defaults" % (path, error))
            return None
        self.settings.apply(doc)
        print("loaded " + path)
        return doc

    def _finalize(self):
        """Derive what the config left at auto, and keep the geometry
        consistent enough that the iris stays on the eyeball."""
        s = self.settings
        size = s.display_size
        s.eye_radius = s.eye_radius if s.eye_radius > 0 else size // 2 + 5
        # Auto values keep the stock demon proportions at any size.
        if s.iris_radius <= 0:
            s.iris_radius = int(0.4583 * size + 0.5)
        s.iris_radius = min(s.iris_radius, s.eye_radius - 1)
        if s.slit_pupil_radius < 0:
            s.slit_pupil_radius = int(0.4167 * size + 0.5)
        s.slit_pupil_radius = min(s.slit_pupil_radius, s.iris_radius)
        # Coverage must be large enough for the eye to look around: solving
        # for the stock eye's gaze-to-map ratio gives mapRadius ~ 0.98 size.
        need = 0.9818 * size / (s.eye_radius * math.pi)
        if s.coverage < need * 0.98:
            print("coverage %.2f too low for this eye; raising to %.2f" % (s.coverage, need))
            s.coverage = need
        s.coverage = min(max(s.coverage, 0.05), 1.0)
        s.pupil_min = max(s.pupil_min, 0.0)
        s.pupil_max = min(s.pupil_max, 1.0)
        if s.pupil_min > s.pupil_max:
            s.pupil_min, s.pupil_max = s.pupil_max, s.pupil_min
        self._track_factor = min(max(1.0 - s.squint, 0.0), 1.0)
        # A bigger iris fraction means a smaller pupil.
        self._iris_min = 1.0 - s.pupil_max
        self._iris_range = s.pupil_max - s.pupil_min

    def _screen2map(self, value):
        """Screen radius to map radius: the same projection as the tables."""
        r = self.settings.eye_radius
        return math.atan2(value, math.sqrt(r * r - value * value)) / (math.pi / 2) * self.map_radius

    def _map2screen(self, value):
        """Map offset to screen offset. As in the Arduino library this is a
        small-angle stand-in for the inverse of _screen2map(), which is all
        lid tracking needs."""
        return math.sin(value / self.map_radius) * (math.pi / 2) * self.settings.eye_radius

    def _gaze_radius_init(self):
        """How far the gaze may move across the map: set_gaze()'s 1.0."""
        size = self.size
        r = (2 * self.map_radius - size * math.pi / 2) * 0.75
        # Also bound it by how far the iris moves in screen pixels; 0.2433 is
        # calibrated so the stock 240 px demon eye keeps its original radius.
        travel = 0.2433 * size
        s = min(travel / (math.pi / 2 * self.settings.eye_radius), 0.999)
        r_screen = self.map_radius * math.asin(s)
        if r > r_screen * 1.10:
            r = r_screen
        self.gaze_radius = max(r, 1.0)
        print("gaze radius %.1f map px" % self.gaze_radius)

    # -- animation ----------------------------------------------------------

    def _reset_animation(self):
        center = float(self.map_radius)
        self.gaze_map_x = self.gaze_map_y = center  # looking straight ahead
        self._iris_prev = [0.0] * 7
        self._iris_next = [0.0] * 7
        self._iris_frame = 0
        self.iris_fraction = 0.5
        self._last_update = ticks_ms()
        for eye in self.eyes:
            eye.upper = eye.lower = 1.0
            eye.iris_phase = float(eye.iris_start)
            eye.sclera_phase = float(eye.sclera_start)

    def _update_iris(self):
        """Pupil dilation as 7-octave value noise: octave i changes every
        2^(i+1) frames and weighs 1/2^(7-i), so slow swings are large and
        fast ones small. Frame-based, as in the original."""
        total = 0.5
        frame = self._iris_frame
        for i in range(7):
            period = 1 << (i + 1)
            bits = frame & (period - 1)
            if bits:
                weight = bits / period
                n = self._iris_prev[i] * (1.0 - weight) + self._iris_next[i] * weight
            else:
                n = self._iris_next[i]
                self._iris_prev[i] = n
                self._iris_next[i] = random.random() - 0.5
            total += n / (1 << (7 - i))
        self.iris_fraction = self._iris_min + total * self._iris_range
        self._iris_frame = (frame + 1) & 127

    def _update_eye(self, number, dt):
        eye = self.eyes[number]
        settings = self.settings
        block = eye.block
        size = self.size
        half = size // 2
        map_radius = self.map_radius
        # Toe the eyes in toward the middle of the face.
        eye_x = self.gaze_map_x + (settings.fixate if number & 1 else -settings.fixate)
        eye_y = self.gaze_map_y
        # The upper lid follows the top of the iris; the lower lid the
        # opposite way. Smoothed, since gaze changes are faster than lids.
        if settings.tracking:
            data = self.data
            ix = int(self._map2screen(int(map_radius - eye_x))) + half
            iy = int(self._map2screen(int(map_radius - eye_y))) + half
            iy += int(settings.iris_radius * self._track_factor)
            if eye.eyelid_mirror:
                ix = size - 1 - ix
            ix = min(max(ix, 0), size - 1)
            upper_open = data[self._lids + ix]
            upper_closed = data[self._lids + size + ix]
            if iy > upper_open:
                upper = 1.0
            elif iy < upper_closed or upper_open == upper_closed:
                upper = 0.0
            else:
                upper = (iy - upper_closed) / (upper_open - upper_closed)
            lower = 1.0 - upper
        else:
            upper = lower = 1.0
        eye.upper = eye.upper * 0.6 + upper * 0.4
        eye.lower = eye.lower * 0.6 + lower * 0.4

        # RPM to 1/1024 turns per millisecond; negative spins clockwise.
        eye.iris_phase = (eye.iris_phase - eye.iris_spin * dt * (1024 / 60000)) % 1024
        eye.sclera_phase = (eye.sclera_phase - eye.sclera_spin * dt * (1024 / 60000)) % 1024

        block[_B_MAP_X] = int(eye_x - half)
        block[_B_MAP_Y] = int(eye_y - half)
        block[_B_IRIS_ANGLE] = int(eye.iris_phase + 0.5) & 1023
        block[_B_SCLERA_ANGLE] = int(eye.sclera_phase + 0.5) & 1023
        block[_B_PUPIL_SCALE] = int(self._iris_height * 256.0 / max(self.iris_fraction, 0.001))
        block[_B_UPPER_LID] = int(eye.upper * 65536)
        block[_B_LOWER_LID] = int(eye.lower * 65536)

    def update(self):
        """Advance the animation one frame: pupil, lid tracking and texture
        spin. Cheap: plain Python, no pixels."""
        now = ticks_ms()
        dt = _elapsed(now, self._last_update)
        self._last_update = now
        self._update_iris()
        self._update_eye(0, dt)
        self._update_eye(1, dt)

    # -- drawing ------------------------------------------------------------

    def attach(self, screen):
        """Draw to screen, an RGB565 buffer the size of the whole display
        (the picodvi.Framebuffer's memoryview), and fill it with the eyelid
        color. Frames are rendered into a back buffer holding just the band
        of rows the eyes occupy, and present() puts it on screen."""
        width = self.screen_width
        color = self.settings.eyelid_color
        self._screen = screen
        fill(screen, array.array("i", [0, width, self.screen_height, width, color]))
        self._back = array.array("H", [color]) * (self.size * width)
        self._back_address = _address(self._back)
        start = self.top * width
        self._band = (start, start + len(self._back))

    def draw(self):
        """Render both eyes into the back buffer."""
        data = self.data
        stride = 2 * self.screen_width
        for eye in self.eyes:
            block = eye.block
            # Set every frame: the kernel walks _B_DEST down the rows as it
            # draws. The back buffer holds just the band of rows the eyes are
            # in, so each eye starts on its row 0.
            block[_B_DEST] = 2 * eye.origin_x
            block[_B_STRIDE] = stride
            lid_spans(data, block)
            # Three arguments, though the asm def lists four registers: as a
            # viper function (see asm_to_viper.py) it finds them through r3.
            render_eye_asm(  # pylint: disable=no-value-for-parameter
                eye.block_address, self._data_address, self._back_address
            )

    def present(self, wait=None):
        """Put the back buffer on screen, calling wait() first if given
        (picodvi.Framebuffer.wait_for_vblank, for no tearing)."""
        if wait:
            wait()
        start, end = self._band
        self._screen[start:end] = self._back  # a C memmove

    def set_gaze(self, x, y):
        """Look somewhere: x -1 (viewer's left) to 1 (viewer's right), y -1
        (down) to 1 (up). Scaled into the reachable disc, not clipped."""
        d2 = x * x + y * y
        if d2 > 1.0:
            k = 1.0 / math.sqrt(d2)
            x *= k
            y *= k
        # A larger map position slides the window the other way, so the
        # iris appears to move opposite to it.
        self.gaze_map_x = self.map_radius - x * self.gaze_radius
        self.gaze_map_y = self.map_radius - y * self.gaze_radius

# ===========================================================================
#  TABLES (once, at startup)
# ===========================================================================

def _build_polar(data, offset, map_radius, iris_radius, slit_radius):
    """One quadrant of the eyeball's surface: per map pixel, its angle
    (0-255 a quadrant, clockwise from the top) and distance (0..127 sclera,
    from map edge to iris edge; -1..-127 iris, from its edge to the center;
    -128 off the map), packed as angle | (distance + 128) << 8.

    Both are symmetric across the diagonal -- angle(y, x) = 256 - angle(x, y)
    and the distance is the same -- so each atan2 and sqrt fills two pixels.
    """
    mr = map_radius
    mr2 = mr * mr
    ir2 = iris_radius * iris_radius
    sclera_span = mr - iris_radius
    to_units = 512 / math.pi
    quarter = math.pi / 2
    atan2 = math.atan2
    sqrt = math.sqrt
    for y in range(mr):
        dy = y + 0.5
        dy2 = dy * dy
        row = offset + y * mr
        column = offset + y
        for x in range(y, mr):
            dx = x + 0.5
            d2 = dx * dx + dy2
            if d2 > mr2:
                data[row + x] = 0  # angle 0, distance -128
                data[column + x * mr] = 0
                continue
            d = sqrt(d2)
            if d2 > ir2:
                dist = int((mr - d) / sclera_span * 127)
            else:
                dist = int((iris_radius - d) / iris_radius * -127) - 1
            v = (quarter - atan2(dy, dx)) * to_units
            high = (dist + 128) << 8
            data[row + x] = int(v) | high
            data[column + x * mr] = int(256 - v) | high

    if slit_radius > 0:
        _build_slit(data, offset, mr, iris_radius, slit_radius)


def _build_slit(data, offset, mr, iris_radius, slit_radius):
    """Reshape the iris for a slit pupil"""
    centers = []
    radii2 = []
    for i in range(127):
        ratio = i / 128
        y1 = iris_radius - (iris_radius - slit_radius) * ratio
        x2 = iris_radius * (1.0 - ratio)
        xc = (x2 * x2 - y1 * y1) / (2.0 * x2)
        centers.append(xc)
        radii2.append((x2 - xc) * (x2 - xc))
    ir2 = iris_radius * iris_radius
    for y in range(mr):
        dy = y + 0.5
        dy2 = dy * dy
        if dy2 > ir2:
            break
        row = offset + y * mr
        for x in range(mr):
            xp = x + 0.5
            if xp * xp + dy2 > ir2:
                break
            low, high = 0, 126  # step 0 always holds an iris pixel
            while low < high:
                mid = (low + high + 1) >> 1
                ex = xp - centers[mid]
                if ex * ex + dy2 <= radii2[mid]:
                    low = mid
                else:
                    high = mid - 1
            data[row + x] = (data[row + x] & 0xFF) | ((127 - low) << 8)  # -1 - low, + 128

def _build_displace(data, offset, half, eye_radius, map_radius):
    """One quadrant of the bend from flat window to hemisphere: per screen
    pixel, how far further out on the map it samples, x | y << 8.

    A pixel d from the center sits on the hemisphere at angle
    asin(d / eye_radius) from the viewing axis, which the map places at
    that angle / (pi/2) * map_radius. Only the x part is computed; the y
    part of (x, y) is the x part of (y, x)."""
    r2 = eye_radius * eye_radius
    scale = map_radius / (math.pi / 2)
    shifts = bytearray(half * half)
    for y in range(half):
        dy = y + 0.5
        dy2 = dy * dy
        for x in range(half):
            dx = x + 0.5
            d2 = dx * dx + dy2
            if d2 <= r2:
                d = math.sqrt(d2)
                pa = math.atan2(d, math.sqrt(r2 - d2)) * scale
                # Subtract before narrowing to a byte, unlike the original,
                # where dx * pa can pass 255 at high coverage.
                shifts[y * half + x] = min(max(int(dx / d * pa) - x, 0), 254)
            else:
                shifts[y * half + x] = 255
    for y in range(half):
        for x in range(half):
            data[offset + y * half + x] = shifts[y * half + x] | (shifts[x * half + y] << 8)
