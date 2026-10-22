# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""3D model kernels: sorting and drawing transformed triangles.

The viper reference: indexed access only, so the same source also runs on a
desktop under tools/host/micropython.py. Faster versions must produce
identical pixels.

geo (u16, hot: SRAM): per vertex VERT values (screen x, y in 1/16 pixels,
depth, normal x, y offset to 0..128; the projection keeps them all
positive), then the drawing order from args[A_ORDER_AT], then per triangle
its face normal packed as x << 8 | y (offset likewise) from args[A_FACES_AT]
(the transform writes them, for flat shading). tri (u16, PSRAM is fine): per
triangle TRI vertex indices, then per triangle an edge mask for the quad
wireframe (bit e for edge e: a-b, b-c, c-a), from TRI * args[A_TRIS], then
(textured models) per triangle UV values: each corner's texture s, t in
1/1024 of the texture's side (s, t << 22 wraps at 2^32: a whole side, where
the texture repeats). Front faces have a positive signed area on the screen (y
down); back faces are skipped.

Texturing (mode 4) interpolates s, t and the normal like Phong does, as
Q = (qc << 22) + (e0 * (qa - qc) + e1 * (qb - qc)) * inv, in wrapping 32-bit
arithmetic (args[A_WRAP] wraps a value here, as the asm's registers do; ints
don't wrap on a desktop). They go in pairs packed in one word, high << 16 +
low (s, t >> 16: 1/65536 of a side; normal x, y >> 13), and so do their steps
across and down: packed values start at the box's top left corner and step
down its rows and along each row, so the asm keeps two registers for four
values. The texel is scaled by its lighting entry's m / 32 and the highlight
added, on rgb565 spread to 0x07E0F81F (each channel with room to multiply).
"""

import micropython
from micropython import const

from mesh_draw import draw_asm, sort_asm

A_WIDTH = const(0)
A_HEIGHT = const(1)
A_TRIS = const(2)
A_FACES_AT = const(3)  # geo offset of the packed face normals
A_ORDER_AT = const(4)  # geo offset of the drawing order
A_COUNTS_AT = const(5)  # args offset of BUCKETS + 1 counts
A_DEPTH_MIN = const(6)  # smallest depth sum of a triangle's 3 vertices
A_DEPTH_SHIFT = const(7)  # (depth sum - min) >> shift = bucket
A_MODE = const(8)  # 0 wireframe, 1 flat (Lambert), 2 interpolated normals (Phong, Blinn),
# 3 quad wireframe (only the edges in each triangle's mask), 4 textured (Phong)
A_BACKGROUND = const(9)
A_WIRE = const(10)  # wireframe color
A_VISIBLE = const(11)  # out: front-facing triangles, in drawing order
A_WRAP = const(12)  # scratch: storing an int here wraps it to 32 bits
D_BLOCK = const(32)  # 32 words from here: what sort_asm() and draw_asm() use
HEADER = const(64)

# The asm block, args[D_BLOCK:], word offsets: render_fast() fills the first
# ones; the rest is the asm's working space for one triangle.
D_BACK = const(0)  # addresses
D_TABLE = const(1)
D_TRI = const(2)
D_GEO = const(3)
D_ORDER = const(4)
D_COUNTS = const(5)
D_VISIBLE = const(6)
D_TRIS = const(7)
D_MODE = const(8)
D_WIDTH = const(9)
D_HEIGHT = const(10)
D_WIRE = const(11)
D_TEXTURE = const(11)  # mode 4: the texture's address (wireframes don't texture)
D_DEPTH_MIN = const(12)
D_DEPTH_SHIFT = const(13)
D_BACKGROUND = const(14)
D_K = const(15)  # working
D_AX = const(16)
D_AY = const(17)
D_BX = const(18)
D_BY = const(19)
D_CX = const(20)
D_CY = const(21)
D_X0 = const(22)
D_X1 = const(23)
D_Y0 = const(24)
D_Y1 = const(25)
D_E0 = const(26)  # at the current row's first pixel
D_E1 = const(27)
D_PX = const(28)
D_PY = const(29)
D_ROW = const(30)  # address of the current row's first pixel
D_COLOR = const(31)

# The transform block (int32 words): what transform_asm() reads.
X_POSITIONS = const(0)  # address of the model's f32 positions
X_NORMALS = const(1)  # ... vertex normals
X_GEO = const(2)  # address of geo (u16 out)
X_VERTS = const(3)
X_FACE_NORMALS = const(4)  # address of the f32 face normals
X_FACES = const(5)  # address of the packed face normals in geo (u16 out)
X_TRIS = const(6)
X_FACES_ON = const(7)  # 1: also transform the face normals (flat shading)
X_M = const(8)  # 9 f32: the rotation, row major
X_DISTANCE = const(17)  # f32 bits from here on
X_CENTER_X16 = const(18)
X_CENTER_Y16 = const(19)
X_FOCAL16 = const(20)
X_DEPTH_SCALE = const(21)
X_NORMAL_SCALE = const(22)
X_ONE = const(23)
X_SAVE = const(24)  # 16 words: s16-s31 belong to the caller
X_WORDS = const(40)
NORMAL_OFFSET = const(64)

VERT = const(5)
V_X = const(0)
V_Y = const(1)
V_Z = const(2)
V_NX = const(3)
V_NY = const(4)
TRI = const(3)
UV = const(6)  # u16 per triangle: s, t of corners a, b, c
BUCKETS = const(256)
TABLE = const(64)  # lighting tables are TABLE x TABLE
TEXTURE_SHIFT = const(9)  # textures are 512 x 512
SPREAD = const(0x07E0F81F)  # rgb565 as (c | c << 16) & SPREAD
WHITE = const(0x0841)  # h * WHITE: rgb565 gray h / 31


@micropython.viper
def sort(tri: ptr16, geo: ptr16, args: ptr32):
    """Front-facing triangles into args' order, farthest first (bucket sort)."""
    tris = args[A_TRIS]
    order = args[A_ORDER_AT]
    counts = args[A_COUNTS_AT]
    depth_min = args[A_DEPTH_MIN]
    depth_shift = args[A_DEPTH_SHIFT]
    i = 0
    while i <= BUCKETS:
        args[counts + i] = 0
        i += 1
    passes = 0
    while passes < 2:
        t = 0
        while t < tris:
            a = VERT * tri[TRI * t]
            b = VERT * tri[TRI * t + 1]
            c = VERT * tri[TRI * t + 2]
            ax = geo[a + V_X]
            ay = geo[a + V_Y]
            area = (geo[b + V_X] - ax) * (geo[c + V_Y] - ay) - (geo[b + V_Y] - ay) * (geo[c + V_X] - ax)
            if area > 0:
                bucket = (geo[a + V_Z] + geo[b + V_Z] + geo[c + V_Z] - depth_min) >> depth_shift
                if bucket < 0:
                    bucket = 0
                if bucket > BUCKETS - 1:
                    bucket = BUCKETS - 1
                bucket = BUCKETS - 1 - bucket  # far first
                if passes == 0:
                    args[counts + bucket + 1] += 1
                else:
                    geo[order + args[counts + bucket]] = t
                    args[counts + bucket] += 1
            t += 1
        if passes == 0:
            i = 0
            while i < BUCKETS:
                args[counts + i + 1] += args[counts + i]
                i += 1
            args[A_VISIBLE] = args[counts + BUCKETS]
        passes += 1


@micropython.viper
def draw(back: ptr16, table: ptr16, tri: ptr16, geo: ptr16, args: ptr32, texture: ptr16):
    """Clear, then draw args[A_VISIBLE] triangles in order."""
    w = args[A_WIDTH]
    h = args[A_HEIGHT]
    mode = args[A_MODE]
    order = args[A_ORDER_AT]
    i = 0
    n = w * h
    background = args[A_BACKGROUND]
    while i < n:
        back[i] = background
        i += 1
    visible = args[A_VISIBLE]
    color = 0
    k = 0
    while k < visible:
        t = geo[order + k]
        a = VERT * tri[TRI * t]
        b = VERT * tri[TRI * t + 1]
        c = VERT * tri[TRI * t + 2]
        ax = geo[a + V_X]
        ay = geo[a + V_Y]
        bx = geo[b + V_X]
        by = geo[b + V_Y]
        cx = geo[c + V_X]
        cy = geo[c + V_Y]
        if mode == 0 or mode == 3:
            # wireframe: the three edges (or the quad's), Bresenham between pixel centers
            edges = 7
            if mode == 3:
                edges = tri[TRI * args[A_TRIS] + t]
            e = 0
            while e < 3:
                if ((edges >> e) & 1) == 0:
                    e += 1
                    continue
                if e == 0:
                    x0 = ax >> 4
                    y0 = ay >> 4
                    x1 = bx >> 4
                    y1 = by >> 4
                elif e == 1:
                    x0 = bx >> 4
                    y0 = by >> 4
                    x1 = cx >> 4
                    y1 = cy >> 4
                else:
                    x0 = cx >> 4
                    y0 = cy >> 4
                    x1 = ax >> 4
                    y1 = ay >> 4
                dx = x1 - x0
                sx = 1
                if dx < 0:
                    dx = -dx
                    sx = -1
                dy = y1 - y0
                sy = 1
                if dy < 0:
                    dy = -dy
                    sy = -1
                err = dx - dy
                color = args[A_WIRE]
                while True:
                    if x0 >= 0 and x0 < w and y0 >= 0 and y0 < h:
                        back[y0 * w + x0] = color
                    if x0 == x1 and y0 == y1:
                        break
                    e2 = err << 1
                    if e2 > -dy:
                        err -= dy
                        x0 += sx
                    if e2 < dx:
                        err += dx
                        y0 += sy
                e += 1
        else:
            # filled: pixels whose centers pass all three edge functions
            x0 = ax
            if bx < x0:
                x0 = bx
            if cx < x0:
                x0 = cx
            x1 = ax
            if bx > x1:
                x1 = bx
            if cx > x1:
                x1 = cx
            y0 = ay
            if by < y0:
                y0 = by
            if cy < y0:
                y0 = cy
            y1 = ay
            if by > y1:
                y1 = by
            if cy > y1:
                y1 = cy
            # the first and last pixel centers (16 k + 8) inside the box
            x0 = (x0 + 7) >> 4
            x1 = (x1 - 8) >> 4
            y0 = (y0 + 7) >> 4
            y1 = (y1 - 8) >> 4
            if x0 < 0:
                x0 = 0
            if y0 < 0:
                y0 = 0
            if x1 > w - 1:
                x1 = w - 1
            if y1 > h - 1:
                y1 = h - 1
            area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)  # the edge functions' sum
            if mode == 1:
                packed = geo[args[A_FACES_AT] + t]
                ix = packed >> 9
                iy = (packed & 0xFF) >> 1
                if ix > TABLE - 1:
                    ix = TABLE - 1
                if iy > TABLE - 1:
                    iy = TABLE - 1
                color = table[iy * TABLE + ix]
            inv = 0
            if area > 0:
                inv = (1 << 22) // area
            if mode == 4:
                # corner differences: s, t, normal x, y
                uv = 4 * args[A_TRIS] + UV * t
                sa = tri[uv] - tri[uv + 4]
                sb = tri[uv + 2] - tri[uv + 4]
                ta = tri[uv + 1] - tri[uv + 5]
                tb = tri[uv + 3] - tri[uv + 5]
                xa = geo[a + V_NX] - geo[c + V_NX]
                xb = geo[b + V_NX] - geo[c + V_NX]
                ya = geo[a + V_NY] - geo[c + V_NY]
                yb = geo[b + V_NY] - geo[c + V_NY]
                # e0, e1 at the box's first pixel, and their steps across and down
                px = (x0 << 4) + 8
                py = (y0 << 4) + 8
                e0 = (cx - bx) * (py - by) - (cy - by) * (px - bx)
                e1 = (ax - cx) * (py - cy) - (ay - cy) * (px - cx)
                d0 = -((cy - by) << 4)
                d1 = -((ay - cy) << 4)
                down0 = (cx - bx) << 4
                down1 = (ax - cx) << 4
                # packed: s, t (>> 16) and normal x, y (>> 13); the first value, x and y steps
                args[A_WRAP] = (tri[uv + 4] << 22) + (e0 * sa + e1 * sb) * inv
                row_uv = (args[A_WRAP] >> 16) << 16
                args[A_WRAP] = (tri[uv + 5] << 22) + (e0 * ta + e1 * tb) * inv
                row_uv += args[A_WRAP] >> 16
                args[A_WRAP] = (d0 * sa + d1 * sb) * inv
                step_uv = (args[A_WRAP] >> 16) << 16
                args[A_WRAP] = (d0 * ta + d1 * tb) * inv
                step_uv += args[A_WRAP] >> 16
                args[A_WRAP] = (down0 * sa + down1 * sb) * inv
                down_uv = (args[A_WRAP] >> 16) << 16
                args[A_WRAP] = (down0 * ta + down1 * tb) * inv
                down_uv += args[A_WRAP] >> 16
                args[A_WRAP] = (geo[c + V_NX] << 22) + (e0 * xa + e1 * xb) * inv
                row_n = (args[A_WRAP] >> 13) << 16
                args[A_WRAP] = (geo[c + V_NY] << 22) + (e0 * ya + e1 * yb) * inv
                row_n += args[A_WRAP] >> 13
                args[A_WRAP] = (d0 * xa + d1 * xb) * inv
                step_n = (args[A_WRAP] >> 13) << 16
                args[A_WRAP] = (d0 * ya + d1 * yb) * inv
                step_n += args[A_WRAP] >> 13
                args[A_WRAP] = (down0 * xa + down1 * xb) * inv
                down_n = (args[A_WRAP] >> 13) << 16
                args[A_WRAP] = (down0 * ya + down1 * yb) * inv
                down_n += args[A_WRAP] >> 13
            y = y0
            while y <= y1:
                py = (y << 4) + 8
                x = x0
                while x <= x1:
                    px = (x << 4) + 8
                    e0 = (cx - bx) * (py - by) - (cy - by) * (px - bx)  # weights a
                    e1 = (ax - cx) * (py - cy) - (ay - cy) * (px - cx)  # weights b
                    e2 = (bx - ax) * (py - ay) - (by - ay) * (px - ax)  # weights c
                    if e0 >= 0 and e1 >= 0 and e2 >= 0:
                        if mode == 2:
                            nx = e0 * geo[a + V_NX] + e1 * geo[b + V_NX] + e2 * geo[c + V_NX]
                            ny = e0 * geo[a + V_NY] + e1 * geo[b + V_NY] + e2 * geo[c + V_NY]
                            ix = (nx * inv) >> 23
                            iy = (ny * inv) >> 23
                            if ix > TABLE - 1:
                                ix = TABLE - 1
                            if iy > TABLE - 1:
                                iy = TABLE - 1
                            color = table[iy * TABLE + ix]
                        elif mode == 4:
                            packed = row_uv + (x - x0) * step_uv
                            texel = texture[(((packed >> 7) & 511) << TEXTURE_SHIFT) + ((packed >> 23) & 511)]
                            packed = row_n + (x - x0) * step_n
                            light = table[((packed >> 10) & 63) * TABLE + ((packed >> 26) & 63)]
                            spread = (texel | (texel << 16)) & SPREAD
                            spread = ((spread * (light & 0xFF)) >> 5) & SPREAD
                            color = ((spread | (spread >> 16)) + (light >> 8) * WHITE) & 0xFFFF
                        back[y * w + x] = color
                    x += 1
                if mode == 4:
                    row_uv += down_uv
                    row_n += down_n
                y += 1
        k += 1


@micropython.viper
def render_fast(back: ptr16, table: ptr16, tri: ptr16, geo: ptr16, args: ptr32, texture: ptr16):
    """sort() then draw(), in asm (mesh_draw): identical results."""
    d = D_BLOCK
    args[d + D_BACK] = int(back)
    args[d + D_TABLE] = int(table)
    args[d + D_TRI] = int(tri)
    args[d + D_GEO] = int(geo)
    args[d + D_ORDER] = int(geo) + 2 * args[A_ORDER_AT]
    args[d + D_COUNTS] = int(args) + 4 * args[A_COUNTS_AT]
    args[d + D_TRIS] = args[A_TRIS]
    args[d + D_MODE] = args[A_MODE]
    args[d + D_WIDTH] = args[A_WIDTH]
    args[d + D_HEIGHT] = args[A_HEIGHT]
    args[d + D_WIRE] = args[A_WIRE]
    if args[A_MODE] == 4:
        args[d + D_TEXTURE] = int(texture)
    args[d + D_DEPTH_MIN] = args[A_DEPTH_MIN]
    args[d + D_DEPTH_SHIFT] = args[A_DEPTH_SHIFT]
    args[d + D_BACKGROUND] = args[A_BACKGROUND]
    block = int(args) + 4 * d
    sort_asm(block)
    args[A_VISIBLE] = args[d + D_VISIBLE]
    draw_asm(block)
