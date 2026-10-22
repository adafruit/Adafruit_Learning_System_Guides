# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""VoxelSpace setup: camera, distance table and sky for the voxel kernels.

Plain Python, run once per frame; the per-pixel work is in voxel.render*().
"""

import array
import math

import mem
import voxel


def spread(c):
    return (c | (c << 16)) & voxel.SPREAD


def rgb565(r, g, b):
    return ((int(r) >> 3) << 11) | ((int(g) >> 2) << 5) | (int(b) >> 3)


def load(path):
    """A whole file as a bytearray. Load the terrain after the framebuffer and
    back buffer: it is big enough to land in PSRAM, and they need the SRAM."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        data = bytearray(f.tell())
        f.seek(0)
        f.readinto(data)
    return data


class VoxelSpace:
    MODES = ("color", "height", "shaded")
    # terrain height scales, as shifts: full, 1/2, 1/4, 1/8, flat
    HEIGHT_SHIFTS = (0, 1, 2, 3, 31)
    HEIGHT_NAMES = ("full", "1/2", "1/4", "1/8", "flat")
    SKY_TOP = (40, 80, 170)
    SKY_HORIZON = (190, 210, 230)

    def __init__(  # pylint: disable=too-many-locals,too-many-statements
        self,
        width,
        height,
        terrain_path,
        palette_path,
        size,
        shade_path=None,
        distance=600,
        scale=120,
        growth=0.016,
        fog_start=0.35,
        mips=(100, 200),
        scratch=None,
        buffer_view=None,
    ):
        """terrain_path: make_terrain.py's u16 texels with their mip levels;
        palette_path: 256 rgb565 colors; shade_path: optional per-texel
        lighting, for the shaded height map mode; mips: distances where levels
        1 and 2 start. scratch: SRAM for the per-frame args (Display(scratch=...)),
        which are hot; without it they're allocated here, and may well land in
        PSRAM. buffer_view: how kernels see a terrain buffer (the desktop
        passes a u16 memoryview cast)."""
        self.width = width
        self.height = height
        self.size = size
        self.shift = size.bit_length() - 1
        self.scale = scale
        self.horizon = None

        # distance steps that grow with distance, in 16.16 so that the board's
        # single-precision floats and the desktop's doubles give the same table
        zs = []
        z = 1 << 16
        dz = 1 << 16
        grow = int(growth * 65536)
        while z < distance << 16:
            zs.append(z >> 16)
            z += dz
            dz += grow
        self.rows = len(zs)
        rows_at = voxel.HEADER
        ybuf_at = rows_at + voxel.ROW * self.rows
        sky_at = ybuf_at + width
        pal_at = sky_at + height
        count = pal_at + 256
        if scratch is None:
            args = array.array("i", bytes(4 * count))
        elif len(scratch) < 4 * count:
            raise ValueError(
                "VoxelSpace needs %d bytes of scratch, got %d" % (4 * count, len(scratch))
            )
        else:
            args = memoryview(scratch)[: 4 * count].cast("i")
            for i in range(count):
                args[i] = 0
        if 0 < mem.address(args) < mem.SRAM:
            print(
                "warning: VoxelSpace args are in PSRAM (0x%08x): rendering will be slow"
                % mem.address(args)
            )
        palette = load(palette_path)
        self.terrain = load(terrain_path)  # the packed bytes, for height_at()
        view = buffer_view or (lambda b: b)
        texels = len(self.terrain) // 2
        # the bare height map: the same texels with height as the color index
        heights = bytearray(len(self.terrain))
        maps = [view(self.terrain), view(heights)]
        span = voxel.heights_as_colors(maps[1], maps[0], texels)
        low, high = span & 0xFF, span >> 8
        self.base = low  # the sea: heights scale toward it
        # the shaded height map: the lighting alone as the color index
        if shade_path:
            shade = load(shade_path)
            shaded = bytearray(len(self.terrain))
            maps.append(view(shaded))
            voxel.heights_with_shade(maps[2], maps[0], shade, texels)
            shade = None
        args[voxel.A_WIDTH] = width
        args[voxel.A_HEIGHT] = height
        args[voxel.A_MASK] = size - 1
        args[voxel.A_SHIFT] = self.shift
        fog = rgb565(*self.SKY_HORIZON)
        args[voxel.A_FOG] = spread(fog)
        args[voxel.A_ROWS] = self.rows
        args[voxel.A_ROWS_AT] = rows_at
        args[voxel.A_YBUF_AT] = ybuf_at
        args[voxel.A_SKY_AT] = sky_at
        args[voxel.A_PAL_AT] = pal_at
        colors = memoryview(palette).cast("H")
        gray = [spread(rgb565(g, g, g)) for g in range(256)]
        self._maps = maps
        self._palettes = [
            [spread(colors[i]) for i in range(256)],
            [gray[max(0, min(255, (h - low) * 255 // max(1, high - low)))] for h in range(256)],
            gray,
        ][: len(maps)]
        self.modes = self.MODES[: len(maps)]
        for level in range(3):
            args[voxel.A_LEVEL_AT + level] = sum((size >> n) ** 2 for n in range(level))
        # integer math from here on, so board and desktop tables match exactly
        fog_from = round(distance * fog_start)
        fog_span = int(distance) - fog_from
        for r, z in enumerate(zs):
            k = rows_at + voxel.ROW * r
            args[k] = z
            args[k + 1] = (scale << 12) // z
            near = max(0, z - fog_from)
            args[k + 2] = min(32, near * near * 32 // (fog_span * fog_span))
            args[k + 3] = sum(1 for m in mips if z >= m)
        self._fog = [args[rows_at + voxel.ROW * r + 2] for r in range(self.rows)]
        self.fog = True
        self.args = args
        args[voxel.A_BASE] = self.base
        self.height_scale = 0
        self.mode = None
        self.show(self.MODES[0])
        # the asm kernels are specialised; anything else uses the viper reference
        self.kernel = voxel.render_fast if (width, size) == (320, 512) else voxel.render

    def show(self, mode):
        """Draw the "color" map, the bare "height" map in grays, or the
        "shaded" height map (lighting without the material colors)."""
        if mode == self.mode:
            return
        which = self.modes.index(mode)
        args = self.args
        pal_at = args[voxel.A_PAL_AT]
        palette = self._palettes[which]
        for i in range(256):
            args[pal_at + i] = palette[i]
        self.map = self._maps[which]
        self.mode = mode

    def show_fog(self, on):
        """Fog on, or off: every distance step at full color."""
        args = self.args
        rows_at = args[voxel.A_ROWS_AT]
        for r in range(self.rows):
            args[rows_at + voxel.ROW * r + 2] = self._fog[r] if on else 0
        self.fog = on

    def next_height_scale(self):
        """Full terrain height, then 1/2, 1/4, 1/8, flat, and back."""
        self.height_scale = (self.height_scale + 1) % len(self.HEIGHT_SHIFTS)
        self.args[voxel.A_HEIGHT_SHIFT] = self.HEIGHT_SHIFTS[self.height_scale]
        return self.HEIGHT_NAMES[self.height_scale]

    def next_mode(self):
        self.show(self.modes[(self.modes.index(self.mode) + 1) % len(self.modes)])

    def height_at(self, x, y):
        mask = self.size - 1
        i = ((int(y) & mask) << self.shift) + (int(x) & mask)
        h = self.terrain[i * 2 + 1]
        shift = self.HEIGHT_SHIFTS[self.height_scale]
        return self.base + ((h - self.base) >> shift if shift < 31 else 0)

    def _sky(self, horizon):
        args = self.args
        sky_at = args[voxel.A_SKY_AT]
        top = self.SKY_TOP
        bottom = self.SKY_HORIZON
        span = max(1, horizon)
        for y in range(self.height):
            t = min(span, max(0, y))
            mix = ((a * (span - t) + b * t) // span for a, b in zip(top, bottom))
            args[sky_at + y] = rgb565(*mix)
        self.horizon = horizon

    def view(self, x, y, h, angle, horizon):
        """Camera at map texel (x, y), height h, heading angle (radians)."""
        args = self.args
        limit = self.size << 16
        args[voxel.A_CAM_X] = int(x * 65536) % limit
        args[voxel.A_CAM_Y] = int(y * 65536) % limit
        # 8 fractional bits: whole units would make near terrain jump
        h256 = int(h * 256)
        args[voxel.A_CAM_H] = h256 >> 8
        args[voxel.A_CAM_H_FRAC] = h256 & 0xFF
        args[voxel.A_HORIZON] = int(horizon)
        s = math.sin(angle)
        c = math.cos(angle)
        # a 90 degree view: left edge (-c - s, s - c), right edge (c - s, -s - c)
        args[voxel.A_LEFT_X] = int((-c - s) * 65536)
        args[voxel.A_LEFT_Y] = int((s - c) * 65536)
        args[voxel.A_STEP_X] = int(2 * c * 65536 / self.width)
        args[voxel.A_STEP_Y] = int(-2 * s * 65536 / self.width)
        if horizon != self.horizon:
            self._sky(int(horizon))

    def render(self, back):
        self.kernel(back, self.map, self.args)
