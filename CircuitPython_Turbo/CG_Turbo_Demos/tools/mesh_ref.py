#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""3D model demo: the numpy float32 transform reference, and desktop frames.

    python3 tools/mesh_ref.py --mesh teapot --mode phong --angle 0.5 --out build/teapot.png

transform() is the specification the board's asm transform follows: the
same float32 operations in the same order, so the integers it produces are
bit-identical. Sorting and drawing run turbo_source/mesh.py's viper reference, as on
the board.
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools" / "host"), str(ROOT / "turbo_source"), str(ROOT / "CG_Turbo_Demos_Code"), str(ROOT / "tools")]

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import mesh  # noqa: E402
import meshview as view  # noqa: E402

F = np.float32


def load(name):
    data = (ROOT / "CG_Turbo_Demos_Code" / ("%s.bin" % name)).read_bytes()
    nv, nt, focal, has_uvs = (int(n) for n in np.frombuffer(data[:8], dtype="<u2"))
    at = 8
    positions = np.frombuffer(data, dtype="<f4", count=nv * 3, offset=at).reshape(-1, 3)
    at += nv * 12
    normals = np.frombuffer(data, dtype="<f4", count=nv * 3, offset=at).reshape(-1, 3)
    at += nv * 12
    face_normals = np.frombuffer(data, dtype="<f4", count=nt * 3, offset=at).reshape(-1, 3)
    at += nt * 12
    # indices, edge masks, then any texture coordinates
    triangles = np.frombuffer(data, dtype="<u2", count=nt * (4 + mesh.UV * has_uvs), offset=at)
    return positions, normals, face_normals, triangles, focal


def rotate(m, p):
    """(m00 x + m01 y) + m02 z, per row: the asm's order."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    return [(m[3 * r] * x + m[3 * r + 1] * y) + m[3 * r + 2] * z for r in range(3)]


def to_int(v):
    return v.astype(np.int32)  # truncation, like vcvt_s32_f32


def transform(matrix, positions, normals, face_normals, focal):
    """(geo verts, tri face normals) as the board's transform makes them:
    VERT u16 per vertex; face normal x, y per triangle."""
    m = np.array(matrix, dtype=F)
    rx, ry, rz = rotate(m, positions)
    rz = rz + F(view.DISTANCE)
    inv = F(1.0) / rz
    sx = F(view.CENTER_X16) + (rx * F(focal * 16)) * inv
    sy = F(view.CENTER_Y16) - (ry * F(focal * 16)) * inv
    nx, ny, _ = rotate(m, normals)
    fx, fy, _ = rotate(m, face_normals)
    k = F(view.NORMAL_SCALE)
    verts = np.stack(
        [
            to_int(sx),
            to_int(sy),
            to_int(rz * F(view.DEPTH_SCALE)),
            to_int(nx * k) + view.NORMAL_OFFSET,
            to_int(ny * k) + view.NORMAL_OFFSET,
        ],
        axis=-1,
    )
    faces = ((to_int(fx * k) + view.NORMAL_OFFSET) << 8) | (to_int(fy * k) + view.NORMAL_OFFSET)
    assert verts.min() >= 0 and faces.min() >= 0, "the projection must keep everything positive"
    return verts.astype(np.uint16), faces.astype(np.uint16)


def setup(name):
    """The board's buffers for a model: (geo, tri, args, model)."""
    positions, normals, face_normals, triangles, focal = load(name)
    nv, nt = len(positions), len(face_normals)
    geo = np.zeros(nv * mesh.VERT + 2 * nt, dtype=np.uint16)
    tri = triangles.astype(np.uint16).copy()
    args = np.zeros(mesh.HEADER + mesh.BUCKETS + 1, dtype=np.int32)
    args[mesh.A_WIDTH] = view.WIDTH
    args[mesh.A_HEIGHT] = view.HEIGHT
    args[mesh.A_TRIS] = nt
    args[mesh.A_ORDER_AT] = nv * mesh.VERT
    args[mesh.A_FACES_AT] = nv * mesh.VERT + nt
    args[mesh.A_COUNTS_AT] = mesh.HEADER
    args[mesh.A_DEPTH_MIN] = int(3 * (view.DISTANCE - 1) * view.DEPTH_SCALE)
    args[mesh.A_DEPTH_SHIFT] = 7
    args[mesh.A_BACKGROUND] = view.BACKGROUND
    return geo, tri, args, (positions, normals, face_normals, focal)


MODELS = ("teapot", "bunny")  # meshview's model order, and mesh_luts.bin's


class Words:
    """args for the viper reference here: int32 slots that wrap what's stored,
    as the board's do (args[mesh.A_WRAP])."""

    def __init__(self, array):
        self.array = array

    def __getitem__(self, i):
        return int(self.array[i])

    def __setitem__(self, i, value):
        self.array[i] = ((value + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def texture_for(name):
    path = ROOT / "CG_Turbo_Demos_Code" / ("%s_texture.bin" % name)
    return np.frombuffer(path.read_bytes(), dtype="<u2").copy() if path.exists() else np.zeros(1, dtype=np.uint16)


def table_for(name, mode):
    which = view.MODES.index(mode)
    table = np.zeros(mesh.TABLE * mesh.TABLE, dtype=np.uint16)
    if view.TABLES[which] is not None:
        luts = np.frombuffer((ROOT / "CG_Turbo_Demos_Code" / "mesh_luts.bin").read_bytes(), dtype="<u2")
        k = MODELS.index(name) * view.SHADED_TABLES + view.TABLES[which]
        table[:] = luts[k * 4096 : (k + 1) * 4096]
    return table


def frame(name, mode, matrix):
    geo, tri, args, model = setup(name)
    verts, faces = transform(matrix, *model)
    geo[: verts.size] = verts.reshape(-1)
    geo[int(args[mesh.A_FACES_AT]) :] = faces
    args[mesh.A_MODE] = view.KERNEL_MODES[view.MODES.index(mode)]
    args[mesh.A_WIRE] = view.WIRES[view.MODES.index(mode)]
    back = np.zeros(view.WIDTH * view.HEIGHT, dtype=np.uint16)
    g, t, a = memoryview(geo), memoryview(tri), Words(args)
    mesh.sort(t, g, a)
    mesh.draw(memoryview(back), memoryview(table_for(name, mode)), t, g, a, memoryview(texture_for(name)))
    return back, int(args[mesh.A_VISIBLE])


def to_image(back, scale=2):
    p = back.astype(np.uint32).reshape(view.HEIGHT, view.WIDTH)
    rgb = np.stack([(p >> 11) << 3, ((p >> 5) & 63) << 2, (p & 31) << 3], axis=-1).astype(np.uint8)
    return Image.fromarray(rgb).resize((view.WIDTH * scale, view.HEIGHT * scale), Image.NEAREST)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mesh", default="teapot", choices=("teapot", "bunny"))
    parser.add_argument("--mode", default="phong", choices=view.MODES)
    parser.add_argument("--angle", type=float, default=0.6)
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "build" / "mesh.png")
    options = parser.parse_args()
    back, visible = frame(options.mesh, options.mode, view.rotation(options.angle))
    options.out.parent.mkdir(exist_ok=True)
    to_image(back).save(options.out)
    print("%d front-facing triangles; wrote %s" % (visible, options.out))


if __name__ == "__main__":
    main()
