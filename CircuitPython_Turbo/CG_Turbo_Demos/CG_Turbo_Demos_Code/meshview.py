# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""3D model demo setup: the model, the per-frame transform, sorting and drawing.

Transformed vertices are screen x, y in 1/16 pixels, an integer depth and
the normal's x, y as small integers; see turbo_source/mesh.py.
"""

import math

import mesh

WIDTH = 240  # the back buffer: the model spins in the middle of the screen
HEIGHT = 200
CENTER_X16 = WIDTH * 8  # screen center, 1/16 pixels
CENTER_Y16 = HEIGHT * 8
# Each model file carries its own focal length (pixels per unit at distance
# 1): as large as keeps it inside the back buffer through a whole turn, so
# every projected value stays positive (tools/make_meshes.py).
DISTANCE = 3.0  # from the camera to the model's center (the model fits radius 1)
DEPTH_SCALE = 4096.0  # integer depth = view z * DEPTH_SCALE
NORMAL_SCALE = 63.0  # integer normal = view normal * NORMAL_SCALE + NORMAL_OFFSET:
# 1..127, so table indices (>> 1) stay within 0..63 and need no clamping
NORMAL_OFFSET = 64
TILT = -0.35  # radians: the model leans toward the camera, so we see a little from above
MODES = ("quads", "triangles", "lambert", "phong", "blinn", "texture")  # the first is the start
KERNEL_MODES = (3, 0, 1, 2, 2, 4)  # mesh.draw's mode for each
TABLES = (None, None, 0, 1, 2, 3)  # which of a model's lighting tables (mesh_luts.bin) each uses
SHADED_TABLES = 4  # lighting tables per model in mesh_luts.bin
WIRES = (0xFFFF, 0x07E8, 0, 0, 0, 0)  # wireframe colors: quads white, triangles green
LABELS = ("quad", "tri", "Lambert", "Phong", "Blinn", "texture")  # what the demo shows for each
TEXTURED = 5  # MODES' texture mode: only for models with texture coordinates
UNTEXTURED = 3  # what a model without them shows instead (Phong)
BACKGROUND = 0x0000  # black, like the screen around the window


def rotation(angle, tilt=TILT):
    """Row-major 3x3: spin about y by angle, then lean about x by tilt."""
    cy, sy = math.cos(angle), math.sin(angle)
    cx, sx = math.cos(tilt), math.sin(tilt)
    return (cy, 0.0, sy, sx * sy, cx, -sx * cy, -cx * sy, sx, cx * cy)


def load(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        data = bytearray(f.tell())
        f.seek(0)
        f.readinto(data)
    return data


class Model:
    """A make_meshes.py model in PSRAM, with its triangle records for mesh.*."""

    def __init__(self, path):
        import mem  # pylint: disable=import-outside-toplevel

        self.data = load(path)
        counts = memoryview(self.data).cast("H")
        self.verts, self.tris, self.focal = counts[0], counts[1], counts[2]
        self.has_uvs = counts[3] == 1  # per corner, after the edge masks
        self.texture = None  # MeshView loads it
        base = mem.address(self.data)
        self.positions = base + 8
        self.normals = self.positions + 12 * self.verts
        self.face_normals = self.normals + 12 * self.verts
        # the file's vertex indices are the records (TRI u16 each), then edge
        # masks, then any texture coordinates
        self.tri = memoryview(self.data)[8 + 24 * self.verts + 12 * self.tris :]


class MeshView:
    """The demo's state: models, mode, rotation, and the SRAM buffers."""

    def __init__(  # pylint: disable=too-many-locals
        self, model_paths, luts_path, scratch, texture_paths=()
    ):
        """scratch: SRAM (see scratch_bytes()) for the hot buffers.
        texture_paths: per model, its texture (512 x 512 rgb565) or None."""
        import mem  # pylint: disable=import-outside-toplevel

        self.models = [Model(p) for p in model_paths]
        for model, path in zip(self.models, texture_paths):
            if path is not None and model.has_uvs:
                model.texture = memoryview(load(path)).cast("H")
        sizes = _sizes([(m.verts, m.tris) for m in self.models])
        if len(scratch) < sum(sizes):
            raise ValueError("MeshView needs %d bytes of scratch" % sum(sizes))
        view = memoryview(scratch)
        at = 0
        parts = []
        for size in sizes:
            parts.append(view[at : at + size])
            at += size
        self.geo = parts[0].cast("H")
        self.args = parts[1].cast("i")
        self.table = parts[2].cast("H")
        self.block = parts[3].cast("i")
        self.block_floats = parts[3].cast("f")
        for part in parts:
            if mem.address(part) < mem.SRAM:
                print(
                    "warning: MeshView buffers are in PSRAM (0x%08x): drawing will be slow"
                    % mem.address(part)
                )
        self.block_address = mem.address(self.block)
        self.luts = load(luts_path)
        args = self.args
        args[mesh.A_WIDTH] = WIDTH
        args[mesh.A_HEIGHT] = HEIGHT
        args[mesh.A_COUNTS_AT] = mesh.HEADER
        args[mesh.A_DEPTH_MIN] = int(3 * (DISTANCE - 1) * DEPTH_SCALE)
        args[mesh.A_DEPTH_SHIFT] = 7
        args[mesh.A_BACKGROUND] = BACKGROUND
        f = self.block_floats
        f[mesh.X_DISTANCE] = DISTANCE
        f[mesh.X_CENTER_X16] = CENTER_X16
        f[mesh.X_CENTER_Y16] = CENTER_Y16
        f[mesh.X_DEPTH_SCALE] = DEPTH_SCALE
        f[mesh.X_NORMAL_SCALE] = NORMAL_SCALE
        f[mesh.X_ONE] = 1.0
        self.geo_address = mem.address(self.geo)
        self.block[mesh.X_GEO] = self.geo_address
        self.model = None
        self.mode = None
        self.wanted = None  # the mode asked for: texture mode survives a visit to the bunny
        self.fast = True  # the asm sort and draw; False: the viper reference
        self.show_model(0)
        self.show_mode(0)

    def show_model(self, index):
        self.model = index
        m = self.models[index]
        block = self.block
        block[mesh.X_POSITIONS] = m.positions
        block[mesh.X_NORMALS] = m.normals
        block[mesh.X_VERTS] = m.verts
        block[mesh.X_FACE_NORMALS] = m.face_normals
        block[mesh.X_TRIS] = m.tris
        self.block_floats[mesh.X_FOCAL16] = m.focal * 16
        self.args[mesh.A_TRIS] = m.tris
        self.args[mesh.A_ORDER_AT] = m.verts * mesh.VERT
        self.args[mesh.A_FACES_AT] = m.verts * mesh.VERT + m.tris
        block[mesh.X_FACES] = self.geo_address + 2 * (m.verts * mesh.VERT + m.tris)
        if self.mode is not None:
            # this model's lighting tables; texture mode again for the teapot
            self.show_mode(self.wanted)

    def can_show(self, index):
        return index != TEXTURED or self.models[self.model].texture is not None

    def next_mode(self):
        """The next of MODES this model can show."""
        index = (self.mode + 1) % len(MODES)
        while not self.can_show(index):
            index = (index + 1) % len(MODES)
        self.show_mode(index)

    def show_mode(self, index):
        """MODES[index] (or UNTEXTURED, if this model has no texture): loads
        its lighting table."""
        self.wanted = index
        if not self.can_show(index):
            index = UNTEXTURED
        self.mode = index
        self.args[mesh.A_MODE] = KERNEL_MODES[index]
        self.args[mesh.A_WIRE] = WIRES[index]
        self.block[mesh.X_FACES_ON] = 1 if KERNEL_MODES[index] == 1 else 0
        which = TABLES[index]
        if which is not None:
            which += self.model * SHADED_TABLES
            start = which * 2 * mesh.TABLE * mesh.TABLE
            end = start + 2 * mesh.TABLE * mesh.TABLE
            memoryview(self.table).cast("B")[:] = memoryview(self.luts)[start:end]

    def set_rotation(self, matrix):
        f = self.block_floats
        for i in range(9):
            f[mesh.X_M + i] = matrix[i]

    def render(self, back):
        import mesh_asm  # pylint: disable=import-outside-toplevel

        mesh_asm.transform_asm(self.block_address)
        model = self.models[self.model]
        # unread unless textured
        texture = model.texture if model.texture is not None else self.table
        if self.fast:
            mesh.render_fast(back, self.table, model.tri, self.geo, self.args, texture)
        else:
            mesh.sort(model.tri, self.geo, self.args)
            mesh.draw(back, self.table, model.tri, self.geo, self.args, texture)


def _sizes(model_counts):
    """Bytes of geo, args, table and the transform block, each rounded up to
    4 so the next starts word-aligned (an odd geo once put the table 2 bytes
    into the block)."""
    geo_words = max(v * mesh.VERT + 2 * t for v, t in model_counts)
    sizes = (
        2 * geo_words,
        4 * (mesh.HEADER + mesh.BUCKETS + 1),
        2 * mesh.TABLE * mesh.TABLE,
        4 * mesh.X_WORDS,
    )
    return [(size + 3) & ~3 for size in sizes]


def scratch_bytes(model_counts):
    """SRAM MeshView needs, for models' (vertices, triangles)."""
    return sum(_sizes(model_counts))
