#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Make the 3D models: CG_Turbo_Demos_Code/teapot.bin and CG_Turbo_Demos_Code/bunny.bin.

    python3 tools/make_meshes.py

Downloads the sources into build/downloads (once):
  the Utah teapot: Martin Newell's 32 Bezier patches, from three.js's
      TeapotGeometry.js (MIT), tessellated here
  the Stanford bunny: bun_zipper_res3.ply from the Stanford 3D Scanning
      Repository (https://graphics.stanford.edu/data/3Dscanrep/)

Each model is centered, scaled to fit the unit sphere, y up, triangles wound
counterclockwise seen from outside. File format (little-endian):
  u16 vertices, u16 triangles, u16 focal length (pixels per unit at distance
  1: as large as keeps the model inside the demo's window through a whole
  turn), u16 0
  vertices x 3 f32 positions, vertices x 3 f32 normals (smooth),
  triangles x 3 f32 face normals, triangles x 3 u16 vertex indices,
  triangles x u16 edge masks for the quad wireframe (bit 0 a-b, 1 b-c,
      2 c-a; 0 for the diagonal of a quad), apart from the indices so the
      other modes read only 6 bytes a triangle
  if the header's last u16 is 1 (the teapot): triangles x 6 u16 texture
      coordinates, s and t of each corner in 1/UV_UNITS of the texture's
      side (half texels of the 512 x 512 texture): per corner, so a patch
      seam can carry two

The teapot's texture layout is injective (every texel on at most one place
on the surface), after the University of Utah's teapot page: the body, rim
and bottom unwrap around the axis into the texture's bottom half (s around,
t down the profile, wrapping at s = 1); the lid, seen from above, is a disk
in the top left quarter; the handle and the spout, tubes, are strips in the
top right (s along, t around).
"""

import argparse
import pathlib
import re
import tarfile
import urllib.request

import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools" / "host"), str(ROOT / "turbo_source"), str(ROOT / "CG_Turbo_Demos_Code")]

import meshview  # noqa: E402  (the demo's view: window, distance, tilt)

MARGIN = 4  # pixels kept clear at the window's edges
DOWNLOADS = ROOT / "build" / "downloads"
TEAPOT_URL = "https://raw.githubusercontent.com/mrdoob/three.js/r160/examples/jsm/geometries/TeapotGeometry.js"
BUNNY_URL = "http://graphics.stanford.edu/pub/3Dscanrep/bunny.tar.gz"
BUNNY_MEMBER = "bunny/reconstruction/bun_zipper_res3.ply"


def fetch(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print("downloading", url)
        urllib.request.urlretrieve(url, path)
    return path


def js_numbers(text, name):
    """The numbers in `const name = [ ... ];` of the three.js source."""
    match = re.search(r"const %s = \[(.*?)\];" % name, text, re.S)
    body = re.sub(r"/\*.*?\*/", "", match.group(1), flags=re.S)
    return [float(n.replace(" ", "")) for n in re.findall(r"-?\s*[\d.]+", body)]


def bernstein(t):
    s = 1 - t
    return np.array([s * s * s, 3 * t * s * s, 3 * t * t * s, t * t * t])


def teapot_patches():
    """Newell's patches: [patch][r][c] -> xyz control points (z up)."""
    text = fetch(TEAPOT_URL, DOWNLOADS / "teapot" / "TeapotGeometry.js").read_text()
    patches = np.array(js_numbers(text, "teapotPatches"), dtype=int).reshape(-1, 4, 4)
    control = np.array(js_numbers(text, "teapotVertices")).reshape(-1, 3)
    return control[patches]


def teapot(segments):
    """(positions, triangles, parts, uvs): uvs per triangle corner (texture
    s, t in 0..1)."""
    patches = teapot_patches()
    layout = Layout(patches)
    positions, triangles, parts, uvs = [], [], [], []
    for index, p in enumerate(patches):  # [r][c] -> xyz
        # the spout and handle meet the body: smaller triangles there sort
        # better back to front
        n_seg = segments * FINE if PART[index] in ("spout", "handle") else segments
        t = np.linspace(0, 1, n_seg + 1)
        base = len(positions)
        here = []
        for u in t:
            for v in t:
                positions.append(np.einsum("r,c,rcx->x", bernstein(u), bernstein(v), p))
                here.append(layout.uv(index, u, v))
        n = n_seg + 1
        for i in range(n_seg):
            for j in range(n_seg):
                a, b = i * n + j, i * n + j + 1
                c, d = (i + 1) * n + j, (i + 1) * n + j + 1
                for corners in ((a, c, b), (b, c, d)):
                    triangles.append([base + k for k in corners])
                    uvs.append([here[k] for k in corners])
                    parts.append(PART[index])
    positions = np.array(positions)[:, [0, 2, 1]] * [1, 1, -1]  # z up -> y up, keeping handedness
    return positions, np.array(triangles), np.array(parts), np.array(uvs)


FINE = 2  # the spout's and handle's subdivision, times the rest's
# three.js's patch order: rim 4, body 8, handle 4, spout 4, lid 8, bottom 4
PART = ["rim"] * 4 + ["body"] * 8 + ["handle"] * 4 + ["spout"] * 4 + ["lid"] * 8 + ["bottom"] * 4
TEXTURE = 512  # texels square (tools/make_teapot_texture.py)
UV_UNITS = 1024  # stored texture coordinates per side: value << 22 wraps at a
# whole side, as the texture does (turbo_source/mesh.py interpolates mod 2^32)
INSET = 0.5 / TEXTURE  # half a texel: the regions' texels never meet
# the profiles, as (patch, its u direction along the chain): rows of four
# patches around the axis (three.js's z up)
STRIP = ((0, 1), (4, 1), (8, 1), (28, -1))  # rim, body upper, lower, bottom to the center
LID = ((20, 1), (24, 1))  # knob from the top center, then the lid out to its edge
# tubes: two patches lengthwise, each a pair side by side around
HANDLE = (12, 14)
SPOUT = (16, 18)


class Layout:
    """The injective texture layout, from the patches' parameters: s, t
    (0..1, t down the image) of patch index at (u, v)."""

    def __init__(self, control):
        self.control = control  # [patch][r][c] -> xyz (z up)
        self.place = {}
        self.splits = {}  # each chain's patch boundaries, 0..1 along it
        for chain in (STRIP, LID, HANDLE, SPOUT):
            pairs = chain if chain in (STRIP, LID) else tuple((p, 1) for p in chain)
            lengths = [self.length(p) for p, _ in pairs]
            at = np.concatenate([[0], np.cumsum(lengths)]) / sum(lengths)
            self.splits[chain] = at
            for k, (first, sign) in enumerate(pairs):
                tube = chain in (HANDLE, SPOUT)
                for q in range(2 if tube else 4):  # the patches around (or side by side)
                    self.place[first + q] = (chain, at[k], at[k + 1], sign, q)

    def point(self, index, u, v):
        return np.einsum("r,c,rcx->x", bernstein(u), bernstein(v), self.control[index])

    def length(self, index, samples=64):
        """Along u, at the middle of v."""
        p = np.array([self.point(index, u, 0.5) for u in np.linspace(0, 1, samples)])
        return np.linalg.norm(np.diff(p, axis=0), axis=1).sum()

    def around(self, index, v):
        """Angle about the axis as a fraction of a turn, continuous across the
        patch (its edge at u = 1 is off the axis)."""
        def turn(v):
            x, y, _ = self.point(index, 1.0, v)
            return np.arctan2(y, x) / (2 * np.pi)

        middle = turn(0.5) % 1
        return 1 - (middle + (turn(v) - middle + 0.5) % 1 - 0.5)  # seen from outside, s runs left to right

    def uv(self, index, u, v):
        chain, lo, hi, sign, q = self.place[index]
        along = lo + (hi - lo) * (u if sign > 0 else 1 - u)
        if chain is STRIP:
            return self.around(index, v), 0.5 + INSET + along * (0.5 - 2 * INSET)
        if chain is LID:
            angle = 2 * np.pi * self.around(index, v)
            radius = along * (0.25 - INSET)
            return 0.25 + radius * np.cos(angle), 0.25 - radius * np.sin(angle)
        around = (q + v) / 2  # the second patch of each pair continues the first
        top = 0.0 if chain is HANDLE else 0.25
        return 0.5 + INSET + along * (0.5 - 2 * INSET), top + INSET + around * (0.25 - 2 * INSET)


def trim_inside_body(positions, triangles, parts):
    """Which triangles to keep: all but the spout's and handle's inside the
    body. The original data runs them into it, and drawing back to front
    can't sort surfaces that cut through each other (dark jagged patches at
    the spout's base).
    The body is a surface of revolution about y: inside means nearer the axis
    than the body's radius at that height."""
    body = positions[np.unique(triangles[parts == "body"])]
    heights = np.unique(np.round(body[:, 1], 6))
    radius = np.array([np.hypot(body[:, 0], body[:, 2])[np.abs(body[:, 1] - h) < 1e-6].max() for h in heights])
    center = positions[triangles].mean(axis=1)
    inside = np.hypot(center[:, 0], center[:, 2]) < np.interp(center[:, 1], heights, radius) - 1e-3
    drop = np.isin(parts, ("spout", "handle")) & inside
    print("  teapot: %d spout and handle triangles inside the body dropped" % drop.sum())
    return ~drop


def bunny():
    archive = fetch(BUNNY_URL, DOWNLOADS / "stanford" / "bunny.tar.gz")
    with tarfile.open(archive) as tar:
        lines = tar.extractfile(BUNNY_MEMBER).read().decode().splitlines()
    end = lines.index("end_header")
    vertices = int(next(l for l in lines if l.startswith("element vertex")).split()[2])
    faces = int(next(l for l in lines if l.startswith("element face")).split()[2])
    positions = np.array([[float(x) for x in l.split()[:3]] for l in lines[end + 1 : end + 1 + vertices]])
    triangles = np.array([[int(x) for x in l.split()[1:4]] for l in lines[end + 1 + vertices : end + 1 + vertices + faces]])
    return positions, triangles


def weld(positions, triangles, tolerance=1e-6, parts=None):
    """Merge vertices at the same place (the teapot's patch seams), drop
    triangles that collapse."""
    keys = np.round(positions / tolerance).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    triangles = inverse.reshape(-1)[triangles]
    positions = positions[first]
    keep = (triangles[:, 0] != triangles[:, 1]) & (triangles[:, 1] != triangles[:, 2]) & (triangles[:, 0] != triangles[:, 2])
    if parts is not None:
        return positions, triangles[keep], parts[keep]
    return positions, triangles[keep]


def orient(positions, triangles):
    """Make neighbors agree on winding (walking across edges shared by exactly
    two triangles), then turn each piece outside out by its signed volume.
    The decimated bunny has many triangles wound the wrong way."""
    from collections import defaultdict, deque

    triangles = triangles.copy()
    by_edge = defaultdict(list)
    for t, (a, b, c) in enumerate(triangles):
        for u, v in ((a, b), (b, c), (c, a)):
            by_edge[(min(u, v), max(u, v))].append(t)
    seen = np.zeros(len(triangles), dtype=bool)
    flips = 0
    for start in range(len(triangles)):
        if seen[start]:
            continue
        seen[start] = True
        piece, queue = [start], deque([start])
        while queue:
            t = queue.popleft()
            a, b, c = triangles[t]
            for u, v in ((a, b), (b, c), (c, a)):
                sharing = by_edge[(min(u, v), max(u, v))]
                if len(sharing) != 2:
                    continue
                other = sharing[0] if sharing[1] == t else sharing[1]
                if seen[other]:
                    continue
                oa, ob, oc = triangles[other]
                if (u, v) in ((oa, ob), (ob, oc), (oc, oa)):  # same direction: wound the other way
                    triangles[other] = (oa, oc, ob)
                    flips += 1
                seen[other] = True
                piece.append(other)
                queue.append(other)
        p = positions[triangles[piece]]
        volume = np.einsum("ij,ij->i", p[:, 0], np.cross(p[:, 1], p[:, 2])).sum()
        if volume < 0:
            triangles[piece] = triangles[piece][:, [0, 2, 1]]
    print("  winding: %d triangles flipped to agree with their neighbors" % flips)
    return positions, triangles


def finish(positions, triangles, uvs=None):
    """(positions, normals, face normals, triangles, uvs), centered and scaled;
    triangles without area dropped (and their uvs, if any)."""
    lo, hi = positions.min(axis=0), positions.max(axis=0)
    positions = positions - (lo + hi) / 2
    positions /= np.linalg.norm(positions, axis=1).max()
    a, b, c = (positions[triangles[:, k]] for k in range(3))
    cross = np.cross(b - a, c - a)
    area = np.linalg.norm(cross, axis=1)
    keep = area > 1e-9
    triangles, cross, area = triangles[keep], cross[keep], area[keep]
    if uvs is not None:
        uvs = uvs[keep]
    face_normals = cross / area[:, None]
    normals = np.zeros_like(positions)
    for k in range(3):
        np.add.at(normals, triangles[:, k], cross)  # area-weighted
    used = np.linalg.norm(normals, axis=1) > 0
    normals[used] /= np.linalg.norm(normals[used], axis=1)[:, None]
    return positions, normals, face_normals, triangles, uvs


def focal(positions):
    """The largest focal length (pixels per unit at distance 1) that keeps
    the model's projection inside the demo's window, with MARGIN, through a
    whole turn of the spin."""
    reach_x = reach_y = 0.0
    for degrees in range(360):
        m = np.array(meshview.rotation(np.radians(degrees))).reshape(3, 3)
        r = positions @ m.T
        z = r[:, 2] + meshview.DISTANCE
        reach_x = max(reach_x, np.abs(r[:, 0] / z).max())
        reach_y = max(reach_y, np.abs(r[:, 1] / z).max())
    half_w = meshview.WIDTH / 2 - MARGIN
    half_h = meshview.HEIGHT / 2 - MARGIN
    return int(min(half_w / reach_x, half_h / reach_y))


def quad_edges(positions, triangles, face_normals):
    """Pair triangles into quads for the quad wireframe: two triangles that
    share an edge pair up when it is the longest edge of both and they are
    nearly flat together, best pairs first; the shared edge, the quad's
    diagonal, is left out of both masks. The teapot was tessellated from quads
    and comes back as them; the scanned bunny becomes mostly quads."""
    from collections import defaultdict  # pylint: disable=import-outside-toplevel

    p = positions[triangles]  # (t, 3, xyz)
    lengths = np.stack([np.linalg.norm(p[:, (e + 1) % 3] - p[:, e], axis=1) for e in range(3)], axis=1)
    longest = lengths.argmax(axis=1)
    users = defaultdict(list)
    for t, tri in enumerate(triangles):
        for e in range(3):
            u, v = tri[e], tri[(e + 1) % 3]
            users[(min(u, v), max(u, v))].append((t, e))
    candidates = []
    for pair in users.values():
        if len(pair) != 2:
            continue
        (t1, e1), (t2, e2) = pair
        flat = float(face_normals[t1] @ face_normals[t2])
        if longest[t1] == e1 and longest[t2] == e2 and flat > 0.9:
            candidates.append((flat, t1, e1, t2, e2))
    masks = np.full(len(triangles), 7, dtype=np.uint16)
    paired = np.zeros(len(triangles), dtype=bool)
    for _, t1, e1, t2, e2 in sorted(candidates, reverse=True):
        if not paired[t1] and not paired[t2]:
            masks[t1] &= 7 ^ (1 << e1)
            masks[t2] &= 7 ^ (1 << e2)
            paired[t1] = paired[t2] = True
    print("  quads: %d of %d triangles paired" % (paired.sum(), len(triangles)))
    return masks


def write(path, positions, normals, face_normals, triangles, uvs):
    f = focal(positions)
    masks = quad_edges(positions, triangles, face_normals)
    header = np.array([len(positions), len(triangles), f, 0 if uvs is None else 1], dtype="<u2").tobytes()
    blocks = [(positions, "<f4"), (normals, "<f4"), (face_normals, "<f4"), (triangles, "<u2"), (masks, "<u2")]
    if uvs is not None:
        blocks.append((np.round(uvs * UV_UNITS), "<u2"))
    data = header + b"".join(a.astype(t).tobytes() for a, t in blocks)
    path.write_bytes(data)
    print(
        "wrote %s: %d vertices, %d triangles, focal %d, %d bytes"
        % (path.relative_to(ROOT), len(positions), len(triangles), f, len(data))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--segments", type=int, default=6, help="teapot patch subdivision")
    options = parser.parse_args()
    positions, triangles, parts, uvs = teapot(options.segments)
    positions, triangles, kept = weld(positions, triangles, parts=np.arange(len(triangles)))
    parts, uvs = parts[kept], uvs[kept]
    keep = trim_inside_body(positions, triangles, parts)
    triangles, uvs = triangles[keep], uvs[keep]
    positions, oriented = orient(positions, triangles)
    flipped = oriented[:, 1] != triangles[:, 1]  # orient swaps corners b and c
    uvs[flipped] = uvs[flipped][:, [0, 2, 1]]
    write(ROOT / "CG_Turbo_Demos_Code" / "teapot.bin", *finish(positions, oriented, uvs))
    positions, triangles = orient(*bunny())
    write(ROOT / "CG_Turbo_Demos_Code" / "bunny.bin", *finish(positions, triangles))


if __name__ == "__main__":
    main()
