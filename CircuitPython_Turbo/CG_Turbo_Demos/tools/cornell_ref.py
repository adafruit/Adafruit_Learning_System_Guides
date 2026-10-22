#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Cornell box path tracer: the numpy float32 reference.

    python3 tools/cornell_ref.py --passes 64 --out build/cornell.png

This is the specification the board's asm kernel follows: every float32
operation in the same order, the same comparisons and the same random number
draws, so the board's pixels and these are bit-identical. It is vectorized
across pixels (each pixel is independent), so it is also quick enough to
render converged images on the desktop.
"""

import argparse
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import cornell_scene as scene  # noqa: E402

F = np.float32
U = np.uint32
np.seterr(all="ignore")

C = {name: F(value) for name, value in scene.float_values().items()}


def use_white_walls(white):
    """Paint the side walls white (or back to red and green), as the board's button does."""
    C.update({name: F(value) for name, value in scene.float_values(white).items()})
ONE, TWO, ZERO, EPS, FAR = C["ONE"], C["TWO"], C["ZERO"], C["EPSILON"], C["FAR"]

LEFT, RIGHT, FLOOR, CEILING, BACK, FRONT, DIFFUSE, MIRROR, BOX = range(9)
MODE = {"boxes": False}


def use_boxes(boxes):
    """The classic two boxes instead of the spheres, as the board's button 3 does."""
    MODE["boxes"] = boxes


def rand(x, mask):
    """xorshift32 on the lanes in mask; returns (state, float in [0, 1))."""
    y = x ^ (x << U(13))
    y = y ^ (y >> U(17))
    y = y ^ (y << U(5))
    x = np.where(mask, y, x)
    f = ((x >> U(9)) | U(0x3F800000)).view(F) - ONE
    return x, f


def dot(ax, ay, az, bx, by, bz):
    return (ax * bx + ay * by) + az * bz


def sphere_t(ox, oy, oz, dx, dy, dz, cx, cy, cz, r2):
    """Nearest hit distance along the ray, or NaN where it misses."""
    ocx, ocy, ocz = ox - cx, oy - cy, oz - cz
    b = dot(ocx, ocy, ocz, dx, dy, dz)
    cc = dot(ocx, ocy, ocz, ocx, ocy, ocz) - r2
    disc = b * b - cc
    t = -b - np.sqrt(disc)
    return np.where(disc > ZERO, t, F(np.nan))


def box_t(ox, oy, oz, dx, dy, dz, b):
    """Entry distance of the ray into box b (NaN where it misses) and the face
    it enters through: axis * 2 + (1 for the + face), in the box's frame."""
    k = lambda f: C["B%d_%s" % (b, f)]  # noqa: E731
    c, s = k("C"), k("S")
    qx, qy, qz = ox - k("CX"), oy - k("CY"), oz - k("CZ")
    lx, lz = qx * c + qz * s, qz * c - qx * s
    ldx, ldz = dx * c + dz * s, dz * c - dx * s
    tnear = tfar = face = None
    for axis, (l, ld, h) in enumerate(((lx, ldx, "X"), (qy, dy, "Y"), (lz, ldz, "Z"))):
        t1 = (k("NH" + h) - l) / ld
        t2 = (k("H" + h) - l) / ld
        swap = t1 > t2
        lo, hi = np.where(swap, t2, t1), np.where(swap, t1, t2)
        f = np.where(swap, 2 * axis + 1, 2 * axis)
        if axis == 0:
            tnear, tfar, face = lo, hi, f
        else:
            up = lo > tnear
            tnear, face = np.where(up, lo, tnear), np.where(up, f, face)
            tfar = np.where(hi < tfar, hi, tfar)
    ok = (tnear <= tfar) & (tnear > EPS)
    return np.where(ok, tnear, F(np.nan)), face


def box_normal(b, face):
    """World normal of box b's face (axis * 2 + positive), as the asm builds it."""
    c, s = C["B%d_C" % b], C["B%d_S" % b]
    one, zero = ONE, ZERO
    return {
        0: (-c, zero, -s),
        1: (c, zero, s),
        2: (zero, -one, zero),
        3: (zero, one, zero),
        4: (s, zero, -c),
        5: (-s, zero, c),
    }[face]


def occluders():
    if MODE["boxes"]:
        return [("box", b) for b in range(2)]
    return [("sphere", "D_"), ("sphere", "M_")]


def occluder_t(kind, which, ox, oy, oz, dx, dy, dz):
    if kind == "box":
        return box_t(ox, oy, oz, dx, dy, dz, which)
    t = sphere_t(ox, oy, oz, dx, dy, dz, C[which + "X"], C[which + "Y"], C[which + "Z"], C[which + "R2"])
    return t, None


def trace_rows(rows, pass_number, accum):
    """One sample for every pixel of the given rows; accum (rows, SIZE, 3)
    float32 is updated in place. Returns the rows' rgb565 pixels."""
    n = scene.SIZE
    row = np.repeat(np.asarray(rows, dtype=np.int32), n)
    col = np.tile(np.arange(n, dtype=np.int32), len(rows))
    index = (row * n + col).astype(U)
    x = (index * U(scene.SEED_MUL)) ^ U((pass_number * scene.PASS_MUL) & 0xFFFFFFFF) ^ U(scene.SEED_XOR)
    x = x | U(1)
    every = np.ones(len(index), dtype=bool)

    x, u1 = rand(x, every)
    x, u2 = rand(x, every)
    px = (col.astype(F) + u1) * C["INV_SIZE"]
    py = ONE - (row.astype(F) + u2) * C["INV_SIZE"]
    pz = np.full(len(index), ZERO, dtype=F)
    dx, dy, dz = px - C["CAM_X"], py - C["CAM_Y"], pz - C["CAM_Z"]
    inv = ONE / np.sqrt(dot(dx, dy, dz, dx, dy, dz))
    dx, dy, dz = dx * inv, dy * inv, dz * inv
    ox, oy, oz = px, py, pz
    tr = np.full(len(index), ONE, dtype=F)
    tg, tb = tr.copy(), tr.copy()
    lr = np.zeros(len(index), dtype=F)
    lg, lb = lr.copy(), lr.copy()
    specular = every.copy()
    alive = every.copy()

    for _ in range(scene.DEPTH):
        # the wall the ray leaves the box through: per axis, the bound ahead
        tmin = np.full(len(index), FAR, dtype=F)
        hit = np.full(len(index), FRONT, dtype=np.int32)
        for d, o, low, high in ((dx, ox, LEFT, RIGHT), (dy, oy, FLOOR, CEILING), (dz, oz, FRONT, BACK)):
            ahead = d >= ZERO
            t = (np.where(ahead, ONE, ZERO) - o) / d
            better = (t > EPS) & (t < tmin)
            tmin = np.where(better, t, tmin)
            hit = np.where(better, np.where(ahead, high, low), hit)
        code = np.zeros(len(index), dtype=np.int32)  # box * 8 + face, for box hits
        for kind, which in occluders():
            t, face = occluder_t(kind, which, ox, oy, oz, dx, dy, dz)
            better = (t > EPS) & (t < tmin)
            tmin = np.where(better, t, tmin)
            if kind == "box":
                hit = np.where(better, BOX, hit)
                code = np.where(better, which * 8 + face, code)
            else:
                hit = np.where(better, DIFFUSE if which == "D_" else MIRROR, hit)
        alive &= hit != FRONT

        hx, hy, hz = ox + dx * tmin, oy + dy * tmin, oz + dz * tmin
        light = (
            (hit == CEILING)
            & (hx >= C["LIGHT_MIN"])
            & (hx <= C["LIGHT_MAX"])
            & (hz >= C["LIGHT_MIN"])
            & (hz <= C["LIGHT_MAX"])
        )
        seen = alive & light & specular
        lr = np.where(seen, lr + tr * C["LE_R"], lr)
        lg = np.where(seen, lg + tg * C["LE_G"], lg)
        lb = np.where(seen, lb + tb * C["LE_B"], lb)
        alive &= ~light

        # mirror: reflect and carry on
        mirror = alive & (hit == MIRROR)
        nx = (hx - C["M_X"]) * C["M_INV_R"]
        ny = (hy - C["M_Y"]) * C["M_INV_R"]
        nz = (hz - C["M_Z"]) * C["M_INV_R"]
        k = dot(dx, dy, dz, nx, ny, nz) * TWO
        mdx, mdy, mdz = dx - nx * k, dy - ny * k, dz - nz * k
        tr = np.where(mirror, tr * C["M_ALB"], tr)
        tg = np.where(mirror, tg * C["M_ALB"], tg)
        tb = np.where(mirror, tb * C["M_ALB"], tb)

        # diffuse surfaces: normal and albedo
        diffuse = alive & ~mirror
        sx = (hx - C["D_X"]) * C["D_INV_R"]
        sy = (hy - C["D_Y"]) * C["D_INV_R"]
        sz = (hz - C["D_Z"]) * C["D_INV_R"]
        zero = np.zeros_like(sx)
        nx = np.select([hit == LEFT, hit == RIGHT, hit == DIFFUSE], [zero + ONE, zero - ONE, sx], zero)
        ny = np.select([hit == FLOOR, hit == CEILING, hit == DIFFUSE], [zero + ONE, zero - ONE, sy], zero)
        nz = np.select([hit == BACK, hit == DIFFUSE], [zero - ONE, sz], zero)
        if MODE["boxes"]:
            for b in range(2):
                for face in range(6):
                    on = (hit == BOX) & (code == b * 8 + face)
                    fx, fy, fz = box_normal(b, face)
                    nx, ny, nz = np.where(on, fx, nx), np.where(on, fy, ny), np.where(on, fz, nz)
        albedo = []
        for ch in "RGB":
            albedo.append(
                np.select(
                    [hit == LEFT, hit == RIGHT, hit == DIFFUSE],
                    [zero + C["RED_" + ch], zero + C["GREEN_" + ch], zero + C["D_ALB_" + ch]],
                    zero + C["WHITE_" + ch],
                )
            )
        tr = np.where(diffuse, tr * albedo[0], tr)
        tg = np.where(diffuse, tg * albedo[1], tg)
        tb = np.where(diffuse, tb * albedo[2], tb)

        # next event estimation: one point on the light, shadowed by the spheres
        x, u1 = rand(x, diffuse)
        x, u2 = rand(x, diffuse)
        qx = C["LIGHT_MIN"] + u1 * C["LIGHT_SIZE"]
        qz = C["LIGHT_MIN"] + u2 * C["LIGHT_SIZE"]
        wx, wy, wz = qx - hx, ONE - hy, qz - hz
        dist2 = dot(wx, wy, wz, wx, wy, wz)
        dist = np.sqrt(dist2)
        inv = ONE / dist
        wx, wy, wz = wx * inv, wy * inv, wz * inv
        cos_s = dot(nx, ny, nz, wx, wy, wz)
        cos_l = wy
        lit = diffuse & (cos_s > ZERO) & (cos_l > ZERO)
        for kind, which in occluders():
            t, _ = occluder_t(kind, which, hx, hy, hz, wx, wy, wz)
            lit &= ~((t > EPS) & (t < dist))
        g = ((cos_s * cos_l) * C["LIGHT_K"]) / dist2
        lr = np.where(lit, lr + (tr * C["LE_R"]) * g, lr)
        lg = np.where(lit, lg + (tg * C["LE_G"]) * g, lg)
        lb = np.where(lit, lb + (tb * C["LE_B"]) * g, lb)

        # cosine-weighted bounce: the normal plus a random point in the unit ball
        need = diffuse.copy()
        vx = np.zeros_like(sx)
        vy, vz, l2 = vx.copy(), vx.copy(), vx.copy()
        while need.any():
            x, a = rand(x, need)
            x, b = rand(x, need)
            x, c = rand(x, need)
            ax, ay, az = a * TWO - ONE, b * TWO - ONE, c * TWO - ONE
            al2 = dot(ax, ay, az, ax, ay, az)
            vx, vy, vz, l2 = (np.where(need, v, w) for v, w in ((ax, vx), (ay, vy), (az, vz), (al2, l2)))
            need &= ~((l2 > EPS) & (l2 <= ONE))
        inv = ONE / np.sqrt(l2)
        bx, by, bz = nx + vx * inv, ny + vy * inv, nz + vz * inv
        m2 = dot(bx, by, bz, bx, by, bz)
        inv = ONE / np.sqrt(m2)
        ok = m2 > EPS
        bdx = np.where(ok, bx * inv, nx)
        bdy = np.where(ok, by * inv, ny)
        bdz = np.where(ok, bz * inv, nz)

        dx = np.where(mirror, mdx, np.where(diffuse, bdx, dx))
        dy = np.where(mirror, mdy, np.where(diffuse, bdy, dy))
        dz = np.where(mirror, mdz, np.where(diffuse, bdz, dz))
        moved = mirror | diffuse
        ox, oy, oz = np.where(moved, hx, ox), np.where(moved, hy, oy), np.where(moved, hz, oz)
        # emission counts only along camera -> mirror* -> light: a diffuse
        # bounce clears it for good (the light is sampled directly there), which
        # also drops the slow-converging caustics through the mirror
        specular = specular & ~diffuse
        alive &= moved

    acc = accum[np.asarray(rows)].reshape(-1, 3)
    acc[:, 0] += lr
    acc[:, 1] += lg
    acc[:, 2] += lb
    accum[np.asarray(rows)] = acc.reshape(len(rows), n, 3)
    scale = C["EXPOSURE"] / F(pass_number + 1)
    v = np.minimum(acc * scale, ONE)
    g = np.sqrt(v)
    r5 = (g[:, 0] * C["K5"]).astype(np.int32)
    g6 = (g[:, 1] * C["K6"]).astype(np.int32)
    b5 = (g[:, 2] * C["K5"]).astype(np.int32)
    return ((r5 << 11) | (g6 << 5) | b5).astype(np.uint16).reshape(len(rows), n)


def to_rgb(pixels):
    p = pixels.astype(np.uint32)
    return np.stack([(p >> 11) << 3, ((p >> 5) & 63) << 2, (p & 31) << 3], axis=-1).astype(np.uint8)


def main():
    from PIL import Image  # pylint: disable=import-outside-toplevel

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--passes", type=int, default=16)
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "build" / "cornell.png")
    parser.add_argument("--white-walls", action="store_true")
    parser.add_argument("--boxes", action="store_true", help="the classic two boxes instead of the spheres")
    options = parser.parse_args()
    use_white_walls(options.white_walls)
    use_boxes(options.boxes)
    accum = np.zeros((scene.SIZE, scene.SIZE, 3), dtype=F)
    rows = list(range(scene.SIZE))
    start = time.monotonic()
    for p in range(options.passes):
        pixels = trace_rows(rows, p, accum)
    print("%d passes in %.1f s" % (options.passes, time.monotonic() - start))
    options.out.parent.mkdir(exist_ok=True)
    Image.fromarray(to_rgb(pixels)).resize((480, 480), Image.NEAREST).save(options.out)
    print("wrote", options.out)


if __name__ == "__main__":
    main()
