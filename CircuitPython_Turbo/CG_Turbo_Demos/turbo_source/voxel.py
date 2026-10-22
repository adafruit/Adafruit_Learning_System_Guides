# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""VoxelSpace kernels.

render() is the readable viper reference: indexed access only, so the same
source also runs on a desktop under tools/host/micropython.py.
render_fast() runs the whole frame in voxel_asm.frame_asm() and must produce
identical pixels.

Everything a frame needs is in one int32 args array: the header slots below,
then a row table (z, 1/z, fog, mip level per distance step), the column
occlusion buffer, the sky gradient and the palette, at the offsets the header
gives.

The terrain is one u16 per texel: height << 8 | palette index, square, a power
of two on a side, wrapping, followed by its mip levels at half and quarter
size. Positions are 16.16 fixed point in full-size texels.
"""

import micropython
from micropython import const

from voxel_asm import frame_asm

# Slots 0-31: what frame_asm() reads (ldr/str offsets stop at 124 bytes).
# render_fast() fills them from the header below; tools/gen_voxel_asm.py
# writes the asm from these names.
F_PX = const(0)  # the current row: 16.16 map position << 7 (texel in the top
F_PY = const(1)  # 9 bits, so wrapping is free)
F_YBUF = const(2)  # address of the column buffer
F_YEND = const(3)  # address just past it
F_BACK = const(4)  # address of the back buffer
F_SPREAD = const(5)  # 0x07E0F81F
F_FOG_KEEP = const(6)  # the current row: 32 - fog
F_FOG_ADD = const(7)  # the current row: fog color * fog
F_SKY = const(8)  # address of the sky gradient
F_PAL = const(9)  # address of the palette
F_ROWS = const(10)  # address of the row table
F_ROWS_END = const(11)  # address just past it
F_ROW_NEXT = const(12)  # the next row's entry
F_CAM_X = const(13)
F_CAM_Y = const(14)
F_LEFT_X = const(15)
F_LEFT_Y = const(16)
F_STEP_X = const(17)
F_STEP_Y = const(18)
F_CAM_H = const(19)
F_HORIZON = const(20)  # horizon << 12, so top = (C - h * hinvz) >> 12 with
F_FOG_COLOR = const(21)  # hinvz = invz >> height shift and C = cam_h * invz +
# ((frac * invz) >> 8) + (horizon << 12) - base * (invz - hinvz)
F_LEVEL0 = const(22)  # address of each mip level
F_LEVEL1 = const(23)
F_LEVEL2 = const(24)
F_HEIGHT = const(25)  # back buffer rows
F_CAM_H_FRAC = const(26)  # camera height's 8 fractional bits
F_HEIGHT_SHIFT = const(27)  # terrain heights scale by 1 / 2**shift (31: flat),
F_BASE = const(28)  # around this height

# The header: written by voxelspace.py, read by render() and render_fast().
A_WIDTH = const(32)
A_HEIGHT = const(33)
A_MASK = const(34)  # terrain size - 1
A_SHIFT = const(35)  # log2(terrain size)
A_CAM_X = const(36)  # 16.16
A_CAM_Y = const(37)
A_CAM_H = const(38)  # camera height, map units
A_HORIZON = const(39)  # screen row of the horizon
A_LEFT_X = const(40)  # left edge of the view at z = 1, 16.16
A_LEFT_Y = const(41)
A_STEP_X = const(42)  # one screen column at z = 1, 16.16
A_STEP_Y = const(43)
A_FOG = const(44)  # fog color, rgb565 spread to 0x07E0F81F form
A_ROWS = const(45)  # number of distance steps
A_ROWS_AT = const(46)  # row table: z, invz (scale * 4096 / z), fog 0-32, mip level
A_YBUF_AT = const(47)  # one int per column
A_SKY_AT = const(48)  # one rgb565 per screen row
A_PAL_AT = const(49)  # 256 palette colors, spread to 0x07E0F81F form
A_LEVEL_AT = const(50)  # 3 slots: where each mip level starts, in texels
A_CAM_H_FRAC = const(53)  # camera height's 8 fractional bits
A_HEIGHT_SHIFT = const(54)  # terrain heights scale by 1 / 2**shift (31: flat),
A_BASE = const(55)  # around this height (the sea)
HEADER = const(56)
ROW = const(4)  # row table entries per distance step

SPREAD = const(0x07E0F81F)


@micropython.viper
def render(back: ptr16, terrain: ptr16, args: ptr32):
    w = args[A_WIDTH]
    h = args[A_HEIGHT]
    mask = args[A_MASK]
    shift = args[A_SHIFT]
    cam_x = args[A_CAM_X]
    cam_y = args[A_CAM_Y]
    cam_h = args[A_CAM_H]
    cam_h_frac = args[A_CAM_H_FRAC]
    height_shift = args[A_HEIGHT_SHIFT]
    base = args[A_BASE]
    horizon = args[A_HORIZON]
    left_x = args[A_LEFT_X]
    left_y = args[A_LEFT_Y]
    step_x = args[A_STEP_X]
    step_y = args[A_STEP_Y]
    fog_color = args[A_FOG]
    rows = args[A_ROWS]
    rows_at = args[A_ROWS_AT]
    ybuf = args[A_YBUF_AT]
    sky = args[A_SKY_AT]
    pal = args[A_PAL_AT]

    i = 0
    while i < w:
        args[ybuf + i] = h
        i += 1

    # front to back: each column only draws what rises above all nearer rows
    r = 0
    while r < rows:
        k = rows_at + ROW * r
        z = args[k]
        invz = args[k + 1]
        fog = args[k + 2]
        level = args[k + 3]
        start = args[A_LEVEL_AT + level]
        row_shift = shift - level
        px = cam_x + z * left_x
        py = cam_y + z * left_y
        dx = z * step_x
        dy = z * step_y
        # projection: (cam_h + frac / 256 - height') * invz / 4096 + horizon,
        # height' = base + (height - base) / 2**height_shift; every term
        # rounded the way the asm rounds it, once per row
        hinvz = invz >> height_shift
        row_c = cam_h * invz + ((cam_h_frac * invz) >> 8) + (horizon << 12) - base * (invz - hinvz)
        i = 0
        while i < w:
            u = ((px >> 16) & mask) >> level
            v = ((py >> 16) & mask) >> level
            t = terrain[start + (v << row_shift) + u]
            top = (row_c - (t >> 8) * hinvz) >> 12
            if top < 0:
                top = 0
            bottom = args[ybuf + i]
            if top < bottom:
                s = args[pal + (t & 0xFF)]
                s = ((s * (32 - fog) + fog_color * fog) >> 5) & SPREAD
                c = (s & 0xFFFF) | (s >> 16)
                o = top * w + i
                y = top
                while y < bottom:
                    back[o] = c
                    o += w
                    y += 1
                args[ybuf + i] = top
            px += dx
            py += dy
            i += 1
        r += 1

    # sky in whatever each column has left
    i = 0
    while i < w:
        bottom = args[ybuf + i]
        o = i
        y = 0
        while y < bottom:
            back[o] = args[sky + y]
            o += w
            y += 1
        i += 1


@micropython.viper
def render_fast(back: ptr16, terrain: ptr16, args: ptr32):
    """render() as one frame_asm() call: same pixels."""
    w = args[A_WIDTH]
    if w != 320 or args[A_SHIFT] != 9:
        raise ValueError("frame_asm needs a 320-wide buffer and a 512-texel map")
    rows = args[A_ROWS]
    if rows < 1:
        raise ValueError("no distance steps")
    base = int(args)
    texels = int(terrain)
    args[F_YBUF] = base + 4 * args[A_YBUF_AT]
    args[F_YEND] = base + 4 * (args[A_YBUF_AT] + w)
    args[F_BACK] = int(back)
    args[F_SPREAD] = SPREAD
    args[F_SKY] = base + 4 * args[A_SKY_AT]
    args[F_PAL] = base + 4 * args[A_PAL_AT]
    args[F_ROWS] = base + 4 * args[A_ROWS_AT]
    args[F_ROWS_END] = base + 4 * (args[A_ROWS_AT] + ROW * rows)
    args[F_CAM_X] = args[A_CAM_X]
    args[F_CAM_Y] = args[A_CAM_Y]
    args[F_LEFT_X] = args[A_LEFT_X]
    args[F_LEFT_Y] = args[A_LEFT_Y]
    args[F_STEP_X] = args[A_STEP_X]
    args[F_STEP_Y] = args[A_STEP_Y]
    args[F_CAM_H] = args[A_CAM_H]
    args[F_HORIZON] = args[A_HORIZON] << 12
    args[F_FOG_COLOR] = args[A_FOG]
    args[F_LEVEL0] = texels + 2 * args[A_LEVEL_AT]
    args[F_LEVEL1] = texels + 2 * args[A_LEVEL_AT + 1]
    args[F_LEVEL2] = texels + 2 * args[A_LEVEL_AT + 2]
    args[F_HEIGHT] = args[A_HEIGHT]
    args[F_CAM_H_FRAC] = args[A_CAM_H_FRAC]
    args[F_HEIGHT_SHIFT] = args[A_HEIGHT_SHIFT]
    args[F_BASE] = args[A_BASE]
    frame_asm(base)


@micropython.viper
def heights_as_colors(dst: ptr16, src: ptr16, count: int) -> int:
    """Copy count texels with each one's palette index replaced by its height,
    for viewing the bare height map. Returns lowest | highest << 8 height."""
    low = 255
    high = 0
    i = 0
    while i < count:
        h = src[i] >> 8
        dst[i] = (h << 8) | h
        if h < low:
            low = h
        if h > high:
            high = h
        i += 1
    return low | (high << 8)


@micropython.viper
def heights_with_shade(dst: ptr16, src: ptr16, shade: ptr8, count: int):
    """Copy count texels with each one's palette index replaced by its shade
    (lighting alone, from shade.bin), for the shaded height map."""
    i = 0
    while i < count:
        dst[i] = (src[i] & 0xFF00) | shade[i]
        i += 1
