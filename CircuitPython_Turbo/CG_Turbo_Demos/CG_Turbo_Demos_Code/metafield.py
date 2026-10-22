# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""2D metaballs setup: ball positions and the args block for metaballs.render*()."""

import array

import mem
import metaballs as kernels


def load(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        data = bytearray(f.tell())
        f.seek(0)
        f.readinto(data)
    return data


class Metaballs:
    THRESHOLD = 2600  # field units: one ball alone reaches 4096 at its center
    GLOW_SHIFT = 4
    SLOPE_SHIFT = 12

    def __init__(  # pylint: disable=too-many-locals
        self, width, height, tables_path, max_balls=12, scratch=None, buffer_view=None
    ):
        """tables_path: tools/make_metaballs_tables.py's output, one set of
        tables per hue. scratch: SRAM for the args and the current hue's
        tables, which the kernel reads all the time."""
        self.width = width
        self.height = height
        self.max_balls = max_balls
        balls_at = kernels.HEADER
        row_at = balls_at + kernels.BALL * max_balls
        count = row_at + 3 * width
        table_bytes = 2 * (kernels.GLOW + kernels.SHADES * kernels.SHADES + kernels.SCALES)
        if scratch is not None and len(scratch) >= 4 * count + table_bytes:
            args = memoryview(scratch)[: 4 * count].cast("i")
            tables = memoryview(scratch)[4 * count : 4 * count + table_bytes]
            for i in range(count):
                args[i] = 0
        else:
            args = array.array("i", bytes(4 * count))
            tables = bytearray(table_bytes)
        self.hue_sets = load(tables_path)  # every hue's tables (PSRAM is fine)
        self.hues = len(self.hue_sets) // table_bytes
        self.table_bytes = table_bytes
        self._tables = tables
        self.hue = 0
        self.glow = True
        tables[:] = memoryview(self.hue_sets)[:table_bytes]
        view = buffer_view or (lambda b: b)
        self.tables = view(tables)
        for name in ("args", "tables"):
            where = mem.address(args if name == "args" else tables)
            if 0 < where < mem.SRAM:
                print(
                    "warning: metaballs %s are in PSRAM (0x%08x): rendering will be slow"
                    % (name, where)
                )
        args[kernels.A_WIDTH] = width
        args[kernels.A_HEIGHT] = height
        args[kernels.A_THRESHOLD] = self.THRESHOLD
        args[kernels.A_GLOW_SHIFT] = self.GLOW_SHIFT
        args[kernels.A_SLOPE_SHIFT] = self.SLOPE_SHIFT
        args[kernels.A_BALLS_AT] = balls_at
        args[kernels.A_ROW_AT] = row_at
        self.args = args
        self.kernel = kernels.render_fast

    def next_hue(self):
        """Switch to the next hue's tables."""
        self.hue = (self.hue + 1) % self.hues
        self._load_tables()
        return self.hue

    def show_glow(self, on):
        """The glow and its contour bands around the blobs, or a plain background."""
        self.glow = on
        self._load_tables()

    def _load_tables(self):
        start = self.hue * self.table_bytes
        self._tables[:] = memoryview(self.hue_sets)[start : start + self.table_bytes]
        if not self.glow:
            # every glow color becomes the first one, the empty field's
            colors = memoryview(self._tables).cast("H")
            for i in range(1, kernels.GLOW):
                colors[i] = colors[0]

    def set_balls(self, balls):
        """balls: (x, y, radius) in pixels, at most max_balls."""
        args = self.args
        at = args[kernels.A_BALLS_AT]
        for i, (x, y, r) in enumerate(balls):
            k = at + kernels.BALL * i
            r16 = int(r * 16)
            args[k + kernels.B_X] = int(x * 16)
            args[k + kernels.B_Y] = int(y * 16)
            args[k + kernels.B_R] = r16
            args[k + kernels.B_R2] = r16 * r16
            args[k + kernels.B_INV] = (1 << 28) // (r16 * r16)
        args[kernels.A_BALLS] = len(balls)

    def render(self, back):
        self.kernel(back, self.tables, self.args)
