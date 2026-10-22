#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Write turbo_source/mesh_draw.py: the 3D model sort and draw as asm_thumb functions.

    python3 tools/gen_mesh_draw.py

sort_asm(block) and draw_asm(block) do what mesh.sort() and mesh.draw() do,
with identical results. block is the address of args[D_BLOCK:] (see
turbo_source/mesh.py's D_* slots), filled by mesh.render_fast().

Filled triangles step their edge functions across the bounding box; the third
edge function is area - e0 - e1 (an exact identity), which saves a register.
Each row skips to the triangle's one run of pixels, paints it and stops.
Normal indices never pass TABLE - 1 (normals are scaled by 63), so the asm
leaves out the reference's clamps. For interpolated normals the asm steps
n_sum * inv directly (n_sum is linear
in x and y, so the product is too, exactly, in wrapping 32-bit arithmetic),
where the reference multiplies per pixel; the values it shifts down are the
same.

Textured triangles (mode 4) work out each row's run instead of seeking it:
along a row each edge function is e + k d, so it holds (>= 0) from
ceil(-e / d) on (d > 0) or up to floor(e / -d) (d < 0), exactly, and the
run is the pixels all three hold for: the reference's pixels. Then it paints
the run with nothing else to test: two packed registers hold s, t and the
normal (see turbo_source/mesh.py), stepped per pixel, and per row in slots.
"""

from spdx import HEADER
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
consts = {
    name: int(value)
    for name, value in re.findall(r"^(\w+) = const\((\d+)\)", (ROOT / "turbo_source" / "mesh.py").read_text(), re.M)
}
VERT_BYTES = 2 * consts["VERT"]
TRI_BYTES = 2 * consts["TRI"]
TABLE = consts["TABLE"]
BUCKETS = consts["BUCKETS"]
CULLED = 0xFFFF  # sort's mark for a back face (buckets are below 256)

# slots reused once their first values are consumed (see draw's setup)
ALIAS = {
    "E0_ROW_STEP": "D_X0",
    "E1_ROW_STEP": "D_X1",
    "ROWS": "D_Y0",
    "ROW_PIXELS": "D_Y1",
    "EDGE_MASK": "D_X0",  # wireframes only
    "VA": "D_PX",
    "VB": "D_PY",
    "VC": "D_COLOR",
    "INV": "D_AX",
    "PX_TEMP": "D_AY",
    "PY_TEMP": "D_BX",
    "PX_ROW_STEP": "D_CX",
    "PY_ROW_STEP": "D_CY",
    # textured: packed values at the row's left edge, their steps down and
    # across, the e steps across; slots the sort, the clear or the setup are
    # done with (every triangle's clip reads D_WIDTH and D_HEIGHT)
    "T_UV": "D_AY",
    "T_N": "D_BX",
    "T_UV_Y": "D_BY",
    "T_N_Y": "D_CX",
    "T_UV_X": "D_CY",
    "T_N_X": "D_COUNTS",
    "T_E0_X": "D_DEPTH_MIN",
    "T_E1_X": "D_DEPTH_SHIFT",
}
SPREAD = 0x07E0F81F  # turbo_source/mesh.py's
WHITE = 0x0841


class Asm:
    def __init__(self):
        self.lines = []
        self.count = 0

    def __call__(self, *lines):
        self.lines.extend(lines)

    def new(self, stem):
        self.count += 1
        return "%s_%d" % (stem, self.count)

    @staticmethod
    def slot(name):
        name = ALIAS.get(name, name)
        return "[r7, %d]" % (4 * consts[name])

    def ld(self, reg, name):
        self("ldr(%s, %s)" % (reg, self.slot(name)))

    def st(self, reg, name):
        self("str(%s, %s)" % (reg, self.slot(name)))

    def vertex(self, dst, index_reg):
        """dst = geo + index * VERT_BYTES (index_reg is consumed)."""
        self("mov(%s, %s)" % (dst, index_reg), "lsl(%s, %s, 3)" % (dst, dst), "lsl(%s, %s, 1)" % (index_reg, index_reg))
        self("add(%s, %s, %s)" % (dst, dst, index_reg))
        assert VERT_BYTES == 10
        self.ld(index_reg, "D_GEO")
        self("add(%s, %s, %s)" % (dst, dst, index_reg))

    def record(self, dst, t_reg, scratch):
        """dst = tri + t * TRI_BYTES."""
        assert TRI_BYTES == 6
        self("mov(%s, %s)" % (dst, t_reg), "lsl(%s, %s, 2)" % (dst, dst), "mov(%s, %s)" % (scratch, t_reg))
        self("lsl(%s, %s, 1)" % (scratch, scratch), "add(%s, %s, %s)" % (dst, dst, scratch))
        self.ld(scratch, "D_TRI")
        self("add(%s, %s, %s)" % (dst, dst, scratch))

    def entry(self):
        self("ldr(r7, [r3, 0])", "push({r7})", "asr(r7, r7, 1)")
        self("mov(r3, r8)", "mov(r4, r9)", "mov(r5, r10)", "mov(r6, r11)", "push({r3, r4, r5, r6})")

    def leave(self):
        self("pop({r3, r4, r5, r6})", "mov(r8, r3)", "mov(r9, r4)", "mov(r10, r5)", "mov(r11, r6)", "pop({r0})")


def sort_asm():
    """The reference's two passes, but the first keeps each triangle's bucket
    (CULLED for back faces) in the back buffer, which draw clears next, so the
    second reads it instead of working it out again."""
    a = Asm()
    a.entry()
    # clear BUCKETS + 1 counts
    a.ld("r0", "D_COUNTS")
    a("mov(r1, 0)", "movw(r2, %d)" % (BUCKETS + 1))
    a("label(clear)", "str(r1, [r0, 0])", "add(r0, 4)", "sub(r2, r2, 1)", "bgt(clear)")
    a("mov(r0, 0)", "mov(r11, r0)")  # r11: t
    a.ld("r0", "D_TRIS")
    a("cmp(r0, 0)", "ble_w(counted)")
    a("label(triangle)")
    a("mov(r0, r11)")
    a.record("r6", "r0", "r1")
    # vertex addresses: r3 a, r4 b, r5 c
    a("ldrh(r0, [r6, 0])")
    a.vertex("r3", "r0")
    a("ldrh(r0, [r6, 2])")
    a.vertex("r4", "r0")
    a("ldrh(r0, [r6, 4])")
    a.vertex("r5", "r0")
    # area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    a("ldrh(r0, [r4, 0])", "ldrh(r1, [r3, 0])", "sub(r0, r0, r1)")  # bx - ax
    a("ldrh(r1, [r5, 2])", "ldrh(r2, [r3, 2])", "sub(r1, r1, r2)")  # cy - ay
    a("mul(r0, r1)")
    a("ldrh(r1, [r4, 2])", "ldrh(r2, [r3, 2])", "sub(r1, r1, r2)")  # by - ay
    a("ldrh(r2, [r5, 0])", "ldrh(r6, [r3, 0])", "sub(r2, r2, r6)")  # cx - ax
    a("mul(r1, r2)")
    a("sub(r0, r0, r1)")
    a("bgt(front)")
    a("movw(r0, %d)" % CULLED, "b(keep_bucket)")
    a("label(front)")
    # bucket = clamp((za + zb + zc - min) >> shift), far first
    a("ldrh(r0, [r3, 4])", "ldrh(r1, [r4, 4])", "add(r0, r0, r1)", "ldrh(r1, [r5, 4])", "add(r0, r0, r1)")
    a.ld("r1", "D_DEPTH_MIN")
    a("sub(r0, r0, r1)")
    a.ld("r1", "D_DEPTH_SHIFT")
    a("asr(r0, r1)")
    a("bpl(not_low)", "mov(r0, 0)", "label(not_low)")
    a("cmp(r0, %d)" % (BUCKETS - 1), "ble(not_high)", "mov(r0, %d)" % (BUCKETS - 1), "label(not_high)")
    a("mov(r1, %d)" % (BUCKETS - 1), "sub(r0, r1, r0)")
    a("lsl(r1, r0, 2)")
    a.ld("r2", "D_COUNTS")
    a("add(r1, r1, r2)")  # &counts[bucket]
    a("ldr(r2, [r1, 4])", "add(r2, 1)", "str(r2, [r1, 4])")
    a("label(keep_bucket)")
    a.ld("r1", "D_BACK")
    a("mov(r2, r11)", "lsl(r2, r2, 1)", "add(r1, r1, r2)", "strh(r0, [r1, 0])")
    a("mov(r0, r11)", "add(r0, 1)", "mov(r11, r0)")
    a.ld("r1", "D_TRIS")
    a("cmp(r0, r1)", "blt_w(triangle)")
    a("label(counted)")
    # prefix sums
    a.ld("r0", "D_COUNTS")
    a("movw(r2, %d)" % BUCKETS)
    a("label(prefix)", "ldr(r1, [r0, 0])", "ldr(r3, [r0, 4])", "add(r3, r3, r1)", "str(r3, [r0, 4])")
    a("add(r0, 4)", "sub(r2, r2, 1)", "bgt(prefix)")
    a("ldr(r1, [r0, 0])")
    a.st("r1", "D_VISIBLE")
    # place: r0 bucket, r1 scratch, r2 order, r3 counts, r4 buckets kept, r5 t, r6 tris
    a.ld("r6", "D_TRIS")
    a("cmp(r6, 0)", "ble(sorted)")
    a.ld("r2", "D_ORDER"), a.ld("r3", "D_COUNTS"), a.ld("r4", "D_BACK")
    a("mov(r5, 0)")
    a("label(place)")
    a("ldrh(r0, [r4, 0])", "lsr(r1, r0, 8)", "bne(placed)")  # CULLED
    a("lsl(r0, r0, 2)", "add(r0, r0, r3)", "ldr(r1, [r0, 0])", "add(r1, 1)", "str(r1, [r0, 0])", "sub(r1, 1)")
    a("lsl(r1, r1, 1)", "add(r1, r1, r2)", "strh(r5, [r1, 0])")
    a("label(placed)")
    a("add(r4, 2)", "add(r5, 1)", "cmp(r5, r6)", "blt(place)")
    a("label(sorted)")
    a.leave()
    return a.lines


def draw_asm():
    a = Asm()
    a.entry()
    # clear to the background: two pixels per word
    a.ld("r0", "D_BACK")
    a.ld("r1", "D_WIDTH")
    a.ld("r2", "D_HEIGHT")
    a("mul(r2, r1)", "lsr(r2, r2, 1)")
    a.ld("r1", "D_BACKGROUND")
    a("lsl(r3, r1, 16)", "orr(r1, r3)")
    a("label(clear)", "str(r1, [r0, 0])", "add(r0, 4)", "sub(r2, r2, 1)", "bgt(clear)")
    a("mov(r0, 0)")
    a.st("r0", "D_K")
    a.ld("r1", "D_VISIBLE")
    a("cmp(r1, 0)", "ble_w(done)")

    a("label(triangle)")
    # t = order[k]; r6 = its record
    a.ld("r0", "D_ORDER")
    a.ld("r1", "D_K")
    a("lsl(r1, r1, 1)", "add(r0, r0, r1)", "ldrh(r0, [r0, 0])")
    a.record("r6", "r0", "r1")
    # vertex addresses, then coordinates into D_AX..D_CY
    for k, (slot, xs, ys) in enumerate((("VA", "D_AX", "D_AY"), ("VB", "D_BX", "D_BY"), ("VC", "D_CX", "D_CY"))):
        a("ldrh(r0, [r6, %d])" % (2 * k))
        a.vertex("r1", "r0")
        a("ldrh(r0, [r1, 0])")
        a.st("r0", xs)
        a("ldrh(r0, [r1, 2])")
        a.st("r0", ys)
        a.st("r1", slot)
    a.ld("r0", "D_MODE")
    a("cmp(r0, 0)", "beq_w(wireframe)", "cmp(r0, 3)", "beq_w(wireframe)")

    # ---- filled
    # r10 area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    a.ld("r0", "D_BX"), a.ld("r1", "D_AX"), a("sub(r0, r0, r1)")
    a.ld("r1", "D_CY"), a.ld("r2", "D_AY"), a("sub(r1, r1, r2)", "mul(r0, r1)")
    a.ld("r1", "D_BY"), a.ld("r2", "D_AY"), a("sub(r1, r1, r2)")
    a.ld("r2", "D_CX"), a.ld("r3", "D_AX"), a("sub(r2, r2, r3)", "mul(r1, r2)")
    a("sub(r0, r0, r1)", "mov(r10, r0)")
    # bounding box in pixels, clipped
    for lo, hi, a0, b0, c0, limit in (("D_X0", "D_X1", "D_AX", "D_BX", "D_CX", "D_WIDTH"), ("D_Y0", "D_Y1", "D_AY", "D_BY", "D_CY", "D_HEIGHT")):
        a.ld("r0", a0), a("mov(r1, r0)")  # r0 min, r1 max
        for other in (b0, c0):
            m1, m2 = a.new("min"), a.new("max")
            a.ld("r2", other)
            a("cmp(r2, r0)", "bge(%s)" % m1, "mov(r0, r2)", "label(%s)" % m1)
            a("cmp(r2, r1)", "ble(%s)" % m2, "mov(r1, r2)", "label(%s)" % m2)
        # the first and last pixel centers (16 k + 8) inside
        a("add(r0, 7)", "asr(r0, r0, 4)", "sub(r1, 8)", "asr(r1, r1, 4)")
        ok1, ok2 = a.new("lo_ok"), a.new("hi_ok")
        a("cmp(r0, 0)", "bge(%s)" % ok1, "mov(r0, 0)", "label(%s)" % ok1)
        a.ld("r2", limit)
        a("sub(r2, r2, 1)", "cmp(r1, r2)", "ble(%s)" % ok2, "mov(r1, r2)", "label(%s)" % ok2)
        a.st("r0", lo)
        a.st("r1", hi)
    # rows and row pixels; nothing to do if either is not positive
    a.ld("r0", "D_X0"), a.ld("r1", "D_X1"), a("sub(r1, r1, r0)", "add(r1, 1)", "ble_w(next_triangle)")
    a.ld("r2", "D_Y0"), a.ld("r3", "D_Y1"), a("sub(r3, r3, r2)", "add(r3, 1)", "ble_w(next_triangle)")
    # first row's first pixel: back + (y0 * width + x0) * 2
    a.ld("r4", "D_WIDTH")
    a("mul(r4, r2)", "add(r4, r4, r0)", "lsl(r4, r4, 1)")
    a.ld("r5", "D_BACK")
    a("add(r4, r4, r5)")
    a.st("r4", "D_ROW")
    # pixel center of the box's corner: r0 px0, r2 py0 (1/16 pixels)
    a("lsl(r0, r0, 4)", "add(r0, 8)", "lsl(r2, r2, 4)", "add(r2, 8)")
    # D_X0/D_X1/D_Y0/D_Y1 become row steps and counters from here
    a.st("r1", "ROW_PIXELS")
    a.st("r3", "ROWS")
    # e0 = (cx - bx) * (py - by) - (cy - by) * (px - bx); steps x: -(cy - by) * 16, y: (cx - bx) * 16
    # e1 = (ax - cx) * (py - cy) - (ay - cy) * (px - cx); steps x: -(ay - cy) * 16, y: (ax - cx) * 16
    for e, (p, q), xstep_reg, ystep in (("D_E0", ("B", "C"), "r8", "E0_ROW_STEP"), ("D_E1", ("C", "A"), "r9", "E1_ROW_STEP")):
        a.ld("r3", "D_%sX" % q), a.ld("r4", "D_%sX" % p), a("sub(r3, r3, r4)")  # qx - px
        a("lsl(r5, r3, 4)")
        a.st("r5", ystep)
        a.ld("r5", "D_%sY" % p), a("sub(r5, r2, r5)", "mul(r3, r5)")  # (qx - px) * (py0 - py)
        a.ld("r5", "D_%sY" % q), a.ld("r6", "D_%sY" % p), a("sub(r5, r5, r6)")  # qy - py
        a("lsl(r6, r5, 4)", "neg(r6, r6)", "mov(%s, r6)" % xstep_reg)
        a.ld("r6", "D_%sX" % p), a("sub(r6, r0, r6)", "mul(r5, r6)")  # (qy - py) * (px0 - px)
        a("sub(r3, r3, r5)")
        a.st("r3", e)
    a.ld("r0", "D_MODE")
    a("cmp(r0, 4)", "beq_w(textured)")
    a("cmp(r0, 2)", "bne_w(flat)")
    # interpolated normals: inv = (1 << 22) // area; for each of x and y,
    #   P0 = (e0 * (na - nc) + e1 * (nb - nc) + area * nc) * inv
    #   steps: (dE0 * (na - nc) + dE1 * (nb - nc)) * inv
    a("movwt(r0, %d)" % (1 << 22), "mov(r1, r10)", "sdiv(r0, r0, r1)")
    a.st("r0", "INV")
    for offset, start_temp, x_step_reg, y_step in ((6, "PX_TEMP", "r11", "PX_ROW_STEP"), (8, "PY_TEMP", "r12", "PY_ROW_STEP")):
        a.ld("r3", "VC"), a("ldrh(r3, [r3, %d])" % offset)  # nc
        a.ld("r4", "VA"), a("ldrh(r4, [r4, %d])" % offset), a("sub(r4, r4, r3)")  # na - nc
        a.ld("r5", "VB"), a("ldrh(r5, [r5, %d])" % offset), a("sub(r5, r5, r3)")  # nb - nc
        # start: e0 * r4 + e1 * r5 + area * r3
        a("mov(r0, r10)", "mul(r3, r0)")
        a.ld("r0", "D_E0"), a("mul(r0, r4)", "add(r3, r3, r0)")
        a.ld("r0", "D_E1"), a("mul(r0, r5)", "add(r3, r3, r0)")
        a.ld("r0", "INV"), a("mul(r3, r0)")
        a.st("r3", start_temp)
        # x step: r8 * r4 + r9 * r5
        a("mov(r3, r8)", "mul(r3, r4)", "mov(r0, r9)", "mul(r0, r5)", "add(r3, r3, r0)")
        a.ld("r0", "INV"), a("mul(r3, r0)", "mov(%s, r3)" % x_step_reg)
        # y step
        a.ld("r3", "E0_ROW_STEP"), a("mul(r3, r4)")
        a.ld("r0", "E1_ROW_STEP"), a("mul(r0, r5)", "add(r3, r3, r0)")
        a.ld("r0", "INV"), a("mul(r3, r0)")
        a.st("r3", y_step)
    a.ld("r0", "PX_TEMP"), a.st("r0", "D_PX")
    a.ld("r0", "PY_TEMP"), a.st("r0", "D_PY")

    # rows, interpolated normals. r0 e0, r1 e1, r2 pixel, r3 PX, r4 PY, r5 table,
    # r6 r7 scratch; r8 r9 e steps, r10 area, r11 r12 P steps, lr row end
    a("label(rows_smooth)")
    a.ld("r0", "D_E0"), a.ld("r1", "D_E1"), a.ld("r2", "D_ROW")
    a.ld("r3", "D_PX"), a.ld("r4", "D_PY"), a.ld("r5", "D_TABLE")
    a.ld("r6", "ROW_PIXELS"), a("lsl(r6, r6, 1)", "add(r6, r6, r2)", "mov(lr, r6)")
    a("push({r7})")
    # a triangle covers one run of each row: skip to it, paint it, stop after
    # it. Normal indices never pass TABLE - 1 (NORMAL_SCALE 63), so no clamps.
    inside = ("mov(r6, r10)", "sub(r6, r6, r0)", "sub(r6, r6, r1)", "orr(r6, r0)", "orr(r6, r1)")
    step = ("mov(r6, r8)", "add(r0, r0, r6)", "mov(r6, r9)", "add(r1, r1, r6)",
            "mov(r6, r11)", "add(r3, r3, r6)", "mov(r6, r12)", "add(r4, r4, r6)",
            "add(r2, 2)", "mov(r6, lr)", "cmp(r2, r6)")
    a("label(seek_smooth)")
    a(*inside)
    a("bpl(paint_smooth)")
    a(*step)
    a("blt(seek_smooth)", "b(row_end_smooth)")
    a("label(paint_smooth)")
    a("asr(r6, r3, 23)", "asr(r7, r4, 23)", "lsl(r7, r7, 6)", "add(r7, r7, r6)", "lsl(r7, r7, 1)")
    a("add(r7, r7, r5)", "ldrh(r7, [r7, 0])", "strh(r7, [r2, 0])")
    a(*step)
    a("bge(row_end_smooth)")
    a(*inside)
    a("bpl(paint_smooth)")
    a("label(row_end_smooth)")
    a("pop({r7})")
    for value, step in (("D_E0", "E0_ROW_STEP"), ("D_E1", "E1_ROW_STEP"), ("D_PX", "PX_ROW_STEP"), ("D_PY", "PY_ROW_STEP")):
        a.ld("r0", value), a.ld("r1", step), a("add(r0, r0, r1)")
        a.st("r0", value)
    a.ld("r0", "D_ROW"), a.ld("r1", "D_WIDTH"), a("lsl(r1, r1, 1)", "add(r0, r0, r1)")
    a.st("r0", "D_ROW")
    a.ld("r0", "ROWS"), a("sub(r0, r0, 1)")
    a.st("r0", "ROWS")
    a("bgt_w(rows_smooth)")
    a("b(next_triangle)")

    # flat: the triangle's color from its face normal (D_COLOR held a vertex
    # address until now)
    a("label(flat)")
    a.ld("r0", "D_ORDER")
    a.ld("r1", "D_K")
    a("lsl(r1, r1, 1)", "add(r0, r0, r1)", "ldrh(r0, [r0, 0])")
    # packed face normal at geo faces + t: the faces follow the order (D_TRIS u16s)
    a("lsl(r0, r0, 1)")
    a.ld("r1", "D_ORDER")
    a("add(r0, r0, r1)")
    a.ld("r1", "D_TRIS")
    a("lsl(r1, r1, 1)", "add(r0, r0, r1)", "ldrh(r1, [r0, 0])")
    a("lsr(r0, r1, 9)", "lsl(r1, r1, 24)", "lsr(r1, r1, 25)")  # <= TABLE - 1: no clamps
    a("lsl(r1, r1, 6)", "add(r1, r1, r0)", "lsl(r1, r1, 1)")
    a.ld("r0", "D_TABLE")
    a("add(r1, r1, r0)", "ldrh(r1, [r1, 0])")
    a.st("r1", "D_COLOR")
    # rows, flat: r0 e0, r1 e1, r2 pixel, r3 color, r4 scratch
    a("label(rows_flat)")
    a.ld("r0", "D_E0"), a.ld("r1", "D_E1"), a.ld("r2", "D_ROW"), a.ld("r3", "D_COLOR")
    a.ld("r4", "ROW_PIXELS"), a("lsl(r4, r4, 1)", "add(r4, r4, r2)", "mov(lr, r4)")
    inside = ("mov(r4, r10)", "sub(r4, r4, r0)", "sub(r4, r4, r1)", "orr(r4, r0)", "orr(r4, r1)")
    step = ("mov(r4, r8)", "add(r0, r0, r4)", "mov(r4, r9)", "add(r1, r1, r4)",
            "add(r2, 2)", "mov(r4, lr)", "cmp(r2, r4)")
    a("label(seek_flat)")
    a(*inside)
    a("bpl(paint_flat)")
    a(*step)
    a("blt(seek_flat)", "b(row_end_flat)")
    a("label(paint_flat)")
    a("strh(r3, [r2, 0])")
    a(*step)
    a("bge(row_end_flat)")
    a(*inside)
    a("bpl(paint_flat)")
    a("label(row_end_flat)")
    for value, step in (("D_E0", "E0_ROW_STEP"), ("D_E1", "E1_ROW_STEP")):
        a.ld("r0", value), a.ld("r1", step), a("add(r0, r0, r1)")
        a.st("r0", value)
    a.ld("r0", "D_ROW"), a.ld("r1", "D_WIDTH"), a("lsl(r1, r1, 1)", "add(r0, r0, r1)")
    a.st("r0", "D_ROW")
    a.ld("r0", "ROWS"), a("sub(r0, r0, 1)")
    a.st("r0", "ROWS")
    a("bgt_w(rows_flat)")
    a("b(next_triangle)")

    textured(a)

    # ---- wireframe: Bresenham between pixel centers, as mesh.draw does.
    # r0 x0, r1 y0, r2 err, r3 r4 scratch, r5 sx, r6 sy; r8 x1, r9 y1, r10 dx, r11 dy
    a("label(wireframe)")
    # which edges: all three, or (quad wireframe) the triangle's mask
    a("mov(r1, 7)")
    a.ld("r0", "D_MODE")
    a("cmp(r0, 3)", "bne(all_edges)")
    a.ld("r0", "D_ORDER")
    a.ld("r1", "D_K")
    a("lsl(r1, r1, 1)", "add(r0, r0, r1)", "ldrh(r0, [r0, 0])")
    # masks follow the records: tri + TRI_BYTES * tris + 2 * t
    a("lsl(r0, r0, 1)")
    a.ld("r1", "D_TRI")
    a("add(r0, r0, r1)")
    a.ld("r1", "D_TRIS")
    a("lsl(r2, r1, 2)", "lsl(r1, r1, 1)", "add(r1, r1, r2)", "add(r0, r0, r1)")
    a("ldrh(r1, [r0, 0])")
    a("label(all_edges)")
    a.st("r1", "EDGE_MASK")
    for edge, (p, q) in enumerate((("A", "B"), ("B", "C"), ("C", "A"))):
        line, step_x, no_x, no_y, plotted, sx_pos, sy_pos = (a.new(n) for n in ("line", "step_x", "no_x", "no_y", "plotted", "sx_pos", "sy_pos"))
        skip_edge = a.new("skip_edge")
        a.ld("r0", "EDGE_MASK")
        a("mov(r1, %d)" % (1 << edge), "and_(r1, r0)", "beq_w(%s)" % skip_edge)
        a.ld("r0", "D_%sX" % p), a("asr(r0, r0, 4)")
        a.ld("r1", "D_%sY" % p), a("asr(r1, r1, 4)")
        a.ld("r3", "D_%sX" % q), a("asr(r3, r3, 4)", "mov(r8, r3)")
        a.ld("r4", "D_%sY" % q), a("asr(r4, r4, 4)", "mov(r9, r4)")
        a("mov(r5, 1)", "sub(r3, r3, r0)", "bge(%s)" % sx_pos, "neg(r3, r3)", "neg(r5, r5)", "label(%s)" % sx_pos, "mov(r10, r3)")
        a("mov(r6, 1)", "sub(r4, r4, r1)", "bge(%s)" % sy_pos, "neg(r4, r4)", "neg(r6, r6)", "label(%s)" % sy_pos, "mov(r11, r4)")
        a("sub(r2, r3, r4)")
        a("label(%s)" % line)
        # plot if inside the buffer
        a("cmp(r0, 0)", "blt(%s)" % plotted, "cmp(r1, 0)", "blt(%s)" % plotted)
        a.ld("r3", "D_WIDTH"), a("cmp(r0, r3)", "bge(%s)" % plotted)
        a.ld("r4", "D_HEIGHT"), a("cmp(r1, r4)", "bge(%s)" % plotted)
        a("mul(r3, r1)", "add(r3, r3, r0)", "lsl(r3, r3, 1)")
        a.ld("r4", "D_BACK"), a("add(r3, r3, r4)")
        a.ld("r4", "D_WIRE"), a("strh(r4, [r3, 0])")
        a("label(%s)" % plotted)
        done_edge = a.new("edge_done")
        a("mov(r3, r8)", "cmp(r0, r3)", "bne(%s)" % step_x, "mov(r3, r9)", "cmp(r1, r3)", "beq_w(%s)" % done_edge)
        a("label(%s)" % step_x)
        # e2 = err << 1; if e2 > -dy: err -= dy, x += sx; if e2 < dx: err += dx, y += sy
        a("lsl(r3, r2, 1)", "mov(r4, r11)", "neg(r4, r4)", "cmp(r3, r4)", "ble(%s)" % no_x)
        a("mov(r4, r11)", "sub(r2, r2, r4)", "add(r0, r0, r5)")
        a("label(%s)" % no_x)
        a("mov(r4, r10)", "cmp(r3, r4)", "bge(%s)" % no_y)
        a("add(r2, r2, r4)", "add(r1, r1, r6)")
        a("label(%s)" % no_y)
        a("b(%s)" % line)
        a("label(%s)" % done_edge)
        a("label(%s)" % skip_edge)

    a("label(next_triangle)")
    a.ld("r0", "D_K"), a("add(r0, 1)")
    a.st("r0", "D_K")
    a.ld("r1", "D_VISIBLE")
    a("cmp(r0, r1)", "blt_w(triangle)")
    a("label(done)")
    a.leave()
    return a.lines


def linear(a, load, shift, first, slots):
    """One interpolated value, Q = (qc << 22) + (e0 (qa - qc) + e1 (qb - qc)) inv:
    load() puts qa, qb, qc in r4, r5, r3. Q at the box's first pixel and its
    steps down and across, each >> shift, go into slots (T_UV, T_UV_Y,
    T_UV_X, or T_N's): the high halves if first, else added as the low.
    Uses r0, r1, r3-r5."""
    load()
    a("sub(r4, r4, r3)", "sub(r5, r5, r3)", "lsl(r3, r3, 22)")
    for (e0, e1), slot in zip((("D_E0", "D_E1"), ("E0_ROW_STEP", "E1_ROW_STEP"), (None, None)), slots):
        if e0 is None:
            a("mov(r0, r8)", "mul(r0, r4)", "mov(r1, r9)", "mul(r1, r5)", "add(r0, r0, r1)")
        else:
            a.ld("r0", e0), a("mul(r0, r4)")
            a.ld("r1", e1), a("mul(r1, r5)", "add(r0, r0, r1)")
        a.ld("r1", "INV"), a("mul(r0, r1)")
        if slot == slots[0]:
            a("add(r0, r0, r3)")
        a("asr(r0, r0, %d)" % shift)
        if first:
            a("lsl(r0, r0, 16)")
        else:
            a.ld("r1", slot), a("add(r0, r0, r1)")
        a.st("r0", slot)


def textured(a):
    """Mode 4: texel times its light's m / 32, plus its highlight."""
    a("label(textured)")
    a("movwt(r0, %d)" % (1 << 22), "mov(r1, r10)", "sdiv(r0, r0, r1)")
    a.st("r0", "INV")
    # r6: the triangle's UV values, tri + 8 * tris + 12 * t
    a.ld("r0", "D_ORDER")
    a.ld("r1", "D_K")
    a("lsl(r1, r1, 1)", "add(r0, r0, r1)", "ldrh(r0, [r0, 0])")
    a("lsl(r1, r0, 3)", "lsl(r0, r0, 2)", "add(r1, r1, r0)")
    a.ld("r0", "D_TRIS"), a("lsl(r0, r0, 3)", "add(r1, r1, r0)")
    a.ld("r0", "D_TRI"), a("add(r6, r1, r0)")
    uv_slots, n_slots = ("T_UV", "T_UV_Y", "T_UV_X"), ("T_N", "T_N_Y", "T_N_X")
    for k in range(2):  # s, t
        linear(a, lambda k=k: a("ldrh(r4, [r6, %d])" % (2 * k), "ldrh(r5, [r6, %d])" % (4 + 2 * k), "ldrh(r3, [r6, %d])" % (8 + 2 * k)),
               16, k == 0, uv_slots)
    for k, offset in enumerate((6, 8)):  # normal x, y
        def load(offset=offset):
            a.ld("r3", "VC"), a("ldrh(r3, [r3, %d])" % offset)
            a.ld("r4", "VA"), a("ldrh(r4, [r4, %d])" % offset)
            a.ld("r5", "VB"), a("ldrh(r5, [r5, %d])" % offset)
        linear(a, load, 13, k == 0, n_slots)
    a("mov(r0, r8)")
    a.st("r0", "T_E0_X")
    a("mov(r0, r9)")
    a.st("r0", "T_E1_X")
    # for the whole triangle: r8 r9 the packed x steps, r11 the texture, r12 the table
    a.ld("r0", "T_UV_X"), a("mov(r8, r0)")
    a.ld("r0", "T_N_X"), a("mov(r9, r0)")
    a.ld("r0", "D_TEXTURE"), a("mov(r11, r0)")
    a.ld("r0", "D_TABLE"), a("mov(r12, r0)")

    # the row's run: r2 first, r3 last pixel (from the box's left edge);
    # r0 e0, r1 e1, r5 r6 their steps, r10 area; r4 r7 scratch
    a("label(rows_tex)")
    a.ld("r0", "D_E0"), a.ld("r1", "D_E1"), a.ld("r5", "T_E0_X"), a.ld("r6", "T_E1_X")
    a("mov(r2, 0)")
    a.ld("r3", "ROW_PIXELS"), a("sub(r3, r3, 1)", "push({r7})")

    def edge(e, d, scratch):
        positive, negative, done = a.new("rising"), a.new("falling"), a.new("edge_done")
        a("cmp(%s, 0)" % d, "bgt(%s)" % positive, "blt(%s)" % negative)
        a("cmp(%s, 0)" % e, "blt_w(no_run_tex)", "b(%s)" % done)  # level
        a("label(%s)" % positive)
        a("cmp(%s, 0)" % e, "bge(%s)" % done)
        a("sub(%s, %s, %s)" % (scratch, d, e), "sub(%s, %s, 1)" % (scratch, scratch))  # ceil(-e / d)
        a("sdiv(%s, %s, %s)" % (scratch, scratch, d))
        a("cmp(%s, r2)" % scratch, "ble(%s)" % done, "mov(r2, %s)" % scratch, "b(%s)" % done)
        a("label(%s)" % negative)
        a("cmp(%s, 0)" % e, "blt_w(no_run_tex)")
        a("neg(%s, %s)" % (scratch, d), "sdiv(%s, %s, %s)" % (scratch, e, scratch))  # floor(e / -d)
        a("cmp(%s, r3)" % scratch, "bge(%s)" % done, "mov(r3, %s)" % scratch)
        a("label(%s)" % done)

    edge("r0", "r5", "r4")
    edge("r1", "r6", "r4")
    a("mov(r4, r10)", "sub(r4, r4, r0)", "sub(r4, r4, r1)", "add(r7, r5, r6)", "neg(r7, r7)")  # e2, its step
    edge("r4", "r7", "r0")
    a("pop({r7})")
    a("cmp(r2, r3)", "bgt_w(row_end_tex)")
    # r2 the run's first pixel, lr its end; packed values there
    a.ld("r4", "D_ROW")
    a("lsl(r3, r3, 1)", "add(r3, 2)", "add(r3, r3, r4)", "mov(lr, r3)")
    a("mov(r3, r2)", "lsl(r2, r2, 1)", "add(r2, r2, r4)")
    a.ld("r0", "T_UV"), a("mov(r5, r8)", "mul(r5, r3)", "add(r0, r0, r5)")
    a.ld("r1", "T_N"), a("mov(r6, r9)", "mul(r6, r3)", "add(r1, r1, r6)")
    # painting: r0 packed s, t; r1 packed normal; r2 pixel; r3 SPREAD; r4
    # WHITE; r5-r7 scratch; r8 r9 their x steps, r11 the texture, r12 the
    # table, lr the run's end
    a("movwt(r3, %d)" % SPREAD, "movw(r4, %d)" % WHITE, "push({r7})")
    a("label(paint_tex)")
    # texel at t * 512 + s
    a("lsr(r5, r0, 23)", "lsl(r6, r0, 16)", "lsr(r6, r6, 23)", "lsl(r6, r6, 9)", "add(r5, r5, r6)")
    a("lsl(r5, r5, 1)", "mov(r6, r11)", "add(r5, r5, r6)", "ldrh(r5, [r5, 0])")
    # light at iy * 64 + ix
    a("lsr(r6, r1, 26)", "lsl(r7, r1, 16)", "lsr(r7, r7, 26)", "lsl(r7, r7, 6)", "add(r6, r6, r7)")
    a("lsl(r6, r6, 1)", "mov(r7, r12)", "add(r6, r6, r7)", "ldrh(r6, [r6, 0])")
    # spread, scale by m / 32, fold, add h * WHITE
    a("lsl(r7, r5, 16)", "orr(r5, r7)", "and_(r5, r3)")
    a("lsl(r7, r6, 24)", "lsr(r7, r7, 24)", "mul(r5, r7)", "lsr(r5, r5, 5)", "and_(r5, r3)")
    a("lsr(r7, r5, 16)", "orr(r5, r7)")
    a("lsr(r6, r6, 8)", "mul(r6, r4)", "add(r5, r5, r6)", "strh(r5, [r2, 0])")
    a("mov(r5, r8)", "add(r0, r0, r5)", "mov(r5, r9)", "add(r1, r1, r5)")
    a("add(r2, 2)", "mov(r5, lr)", "cmp(r2, r5)", "blt(paint_tex)")
    a("pop({r7})", "b(row_end_tex)")
    a("label(no_run_tex)")
    a("pop({r7})")
    a("label(row_end_tex)")
    for value, step in (("D_E0", "E0_ROW_STEP"), ("D_E1", "E1_ROW_STEP"), ("T_UV", "T_UV_Y"), ("T_N", "T_N_Y")):
        a.ld("r0", value), a.ld("r1", step), a("add(r0, r0, r1)")
        a.st("r0", value)
    a.ld("r0", "D_ROW"), a.ld("r1", "D_WIDTH"), a("lsl(r1, r1, 1)", "add(r0, r0, r1)")
    a.st("r0", "D_ROW")
    a.ld("r0", "ROWS"), a("sub(r0, r0, 1)")
    a.st("r0", "ROWS")
    a("bgt_w(rows_tex)")
    a("b(next_triangle)")


HEAD = '''"""Generated by tools/gen_mesh_draw.py: edit that.

sort_asm(block) and draw_asm(block): mesh.sort() and mesh.draw() in asm,
with identical results. block is the address of args[D_BLOCK:], filled by
mesh.render_fast(). Relabelled as viper by tools/asm_to_viper.py, so the
argument object is at [r3].
"""

import micropython
'''


def main():
    out = ROOT / "turbo_source" / "mesh_draw.py"
    parts = [HEAD]
    for name, body in (("sort_asm", sort_asm()), ("draw_asm", draw_asm())):
        parts.append("\n\n@micropython.asm_thumb\ndef %s(r0, r1, r2, r3):\n" % name)
        parts.append("".join("    %s\n" % line for line in body))
    out.write_text(HEADER + "".join(parts))
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
