# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
# SPDX-FileCopyrightText: 2020 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# "Pixel dust" sand physics from Adafruit_PixelDust (Phil Burgess, BSD),
# ported to a turbo viper kernel. Integer only: positions are 8.8 fixed
# point (pixel * 256), velocities are in the same units per frame, terminal
# velocity is 256 (one pixel) so grains never tunnel through each other.
#
# `g` is an array('i') of 5 ints per grain: x, y, vx, vy, colour. `fb` is any
# writable byte buffer of height rows, width bytes apart, one byte per cell:
# 0 free, else the colour of the grain sitting there. A displayio.Bitmap with
# value_count=256 and a width that is a multiple of 4 works directly and is
# both the collision map and the frame. `rng` is a one-element array('I')
# holding the random state, advanced in place.
#
# Where the C truncates toward zero on a division this does too, so a grain
# bouncing left behaves like one bouncing right.
import micropython

# pylint: disable=too-many-locals, undefined-variable, too-many-nested-blocks, too-many-branches, too-many-statements
# pylint: disable=import-outside-toplevel


@micropython.viper
def iterate(
    g: ptr32,
    fb: ptr8,
    n: int,
    width: int,
    height: int,
    ax: int,
    ay: int,
    az: int,
    elasticity: int,
    rng: ptr32,
) -> int:
    xmax = width * 256 - 1
    ymax = height * 256 - 1

    # Scale raw accelerometer input (milli-m/s^2) down to grain units. The C
    # has a `scale` parameter that the demo leaves at 1, so it is folded in.
    if ax >= 0:
        ax = ax // 256
    else:
        ax = -((-ax) // 256)
    if ay >= 0:
        ay = ay // 256
    else:
        ay = -((-ay) // 256)
    if az < 0:
        az = -az
    az = az // 2048
    # A bit of random jitter per grain so tall stacks topple instead of
    # sliding as a block. Stronger the further from level the panel is.
    if az >= 4:
        az = 1
    else:
        az = 5 - az
    ax -= az
    ay -= az
    az2 = az * 2 + 1

    r = rng[0]
    moved = 0
    for i in range(n):
        b = i * 5
        x = g[b]
        y = g[b + 1]
        vx = g[b + 2]
        vy = g[b + 3]

        # Apply the 2D acceleration vector plus jitter.
        r = (r * 214013 + 2531011) & 0x3FFFFFFF
        vx += ax + ((r >> 16) % az2)
        r = (r * 214013 + 2531011) & 0x3FFFFFFF
        vy += ay + ((r >> 16) % az2)
        # Clip velocity as a 2D vector at 256 so diagonal motion is no
        # faster than axial. Integer Newton sqrt stands in for sqrtf().
        v2 = vx * vx + vy * vy
        if v2 > 65536:
            v = 512
            for _ in range(8):
                v = (v + v2 // v) >> 1
            t = vx * 256
            if t >= 0:
                vx = t // v
            else:
                vx = -((-t) // v)
            t = vy * 256
            if t >= 0:
                vy = t // v
            else:
                vy = -((-t) // v)

        # Tentative new position, bouncing off the walls.
        nx = x + vx
        ny = y + vy
        if nx < 0:
            nx = 0
            if vx >= 0:
                vx = -((vx * elasticity) // 256)
            else:
                vx = ((-vx) * elasticity) // 256
        elif nx > xmax:
            nx = xmax
            if vx >= 0:
                vx = -((vx * elasticity) // 256)
            else:
                vx = ((-vx) * elasticity) // 256
        if ny < 0:
            ny = 0
            if vy >= 0:
                vy = -((vy * elasticity) // 256)
            else:
                vy = ((-vy) * elasticity) // 256
        elif ny > ymax:
            ny = ymax
            if vy >= 0:
                vy = -((vy * elasticity) // 256)
            else:
                vy = ((-vy) * elasticity) // 256

        # Cell indices before and after. Comparing indices rather than x and
        # y separately makes the blocked-direction test cheap.
        ox = x >> 8
        oy = y >> 8
        cx = nx >> 8
        cy = ny >> 8
        oldidx = oy * width + ox
        newidx = cy * width + cx

        if oldidx != newidx and fb[newidx] != 0:
            delta = newidx - oldidx
            if delta < 0:
                delta = -delta
            if delta == 1:
                # Blocked left or right: cancel X, bounce X, Y is fine.
                nx = x
                if vx >= 0:
                    vx = -((vx * elasticity) // 256)
                else:
                    vx = ((-vx) * elasticity) // 256
            elif delta == width:
                # Blocked up or down: cancel Y, bounce Y, X is fine.
                ny = y
                if vy >= 0:
                    vy = -((vy * elasticity) // 256)
                else:
                    vy = ((-vy) * elasticity) // 256
            else:
                # Diagonal: try skidding along the faster axis first, then
                # the other, else stop dead.
                avx = vx
                if avx < 0:
                    avx = -avx
                avy = vy
                if avy < 0:
                    avy = -avy
                if avx >= avy:
                    if fb[oy * width + cx] == 0:
                        ny = y
                        if vy >= 0:
                            vy = -((vy * elasticity) // 256)
                        else:
                            vy = ((-vy) * elasticity) // 256
                    elif fb[cy * width + ox] == 0:
                        nx = x
                        if vx >= 0:
                            vx = -((vx * elasticity) // 256)
                        else:
                            vx = ((-vx) * elasticity) // 256
                    else:
                        nx = x
                        ny = y
                        if vx >= 0:
                            vx = -((vx * elasticity) // 256)
                        else:
                            vx = ((-vx) * elasticity) // 256
                        if vy >= 0:
                            vy = -((vy * elasticity) // 256)
                        else:
                            vy = ((-vy) * elasticity) // 256
                else:
                    if fb[cy * width + ox] == 0:
                        nx = x
                        if vx >= 0:
                            vx = -((vx * elasticity) // 256)
                        else:
                            vx = ((-vx) * elasticity) // 256
                    elif fb[oy * width + cx] == 0:
                        ny = y
                        if vy >= 0:
                            vy = -((vy * elasticity) // 256)
                        else:
                            vy = ((-vy) * elasticity) // 256
                    else:
                        nx = x
                        ny = y
                        if vx >= 0:
                            vx = -((vx * elasticity) // 256)
                        else:
                            vx = ((-vx) * elasticity) // 256
                        if vy >= 0:
                            vy = -((vy * elasticity) // 256)
                        else:
                            vy = ((-vy) * elasticity) // 256
            newidx = (ny >> 8) * width + (nx >> 8)

        c = g[b + 4]
        fb[oldidx] = 0
        fb[newidx] = c
        if newidx != oldidx:
            moved += 1
        g[b] = nx
        g[b + 1] = ny
        g[b + 2] = vx
        g[b + 3] = vy

    rng[0] = r
    return moved


def place(g, fb, i, x, y, width, colour):
    """Put grain i at pixel (x, y) with the given colour index (1..255).
    Returns False, leaving everything unchanged, if the cell is taken."""
    idx = y * width + x
    if fb[idx]:
        return False
    fb[idx] = colour
    b = i * 5
    g[b] = x * 256
    g[b + 1] = y * 256
    g[b + 2] = 0
    g[b + 3] = 0
    g[b + 4] = colour
    return True


def _turbo_bench():
    # 64x64 world, 512 grains in the demo's eight 8x8 colour blocks along the
    # bottom, 60 frames of gravity that swings between the four edges.
    # Returns a hash of every grain field; every tier must reproduce it.
    from array import array

    W, H, N = 64, 64, 512
    fb = bytearray(W * H)
    g = array("i", [0] * (5 * N))
    rng = array("I", [12345])
    i = 0
    for c in range(8):
        for y in range(H - 8, H):
            for x in range(c * 8, c * 8 + 8):
                place(g, fb, i, x, y, W, c + 1)
                i += 1
    dirs = ((0, 9800, 300), (9800, 0, 300), (0, -9800, 300), (-9800, 0, 300))
    for k in range(60):
        ax, ay, az = dirs[(k // 15) % 4]
        iterate(g, fb, N, W, H, ax, ay, az, 128, rng)
    h = 0
    for v in g:
        h = (h * 31 + v) & 0x3FFFFFFF
    return h
