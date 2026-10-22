#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Write turbo_source/cornell_asm.py: the Cornell box path tracer as one asm_thumb function.

    python3 tools/gen_cornell_asm.py

trace_row(block_address) traces one sample for each pixel of a row, adds it
to the accumulation buffer and writes the tone-mapped rgb565 pixel. It is the
same computation as tools/cornell_ref.py, operation for operation, so the
pixels are bit-identical; keep the two in step.

Registers: s0-s2 ray origin, s3-s5 direction, s6-s8 throughput, s9-s11
radiance, s12 nearest hit distance, s13-s15 hit point, s16-s18 normal, s19-s21
albedo, s22-s29 working, s28 mostly constants (the box tests borrow more:
see their register maps); the rand subroutine leaves its
float in s31 and uses s30. r7 is the block, r6 the random state, r5 the kind
of surface hit. s16-s31 belong to the caller and are saved in the block.

Float compares branch on conditions that treat NaN like numpy does (a
comparison with NaN is false). Conditional branches use the 32-bit _w forms
(the kernel is longer than 16-bit branches reach) and long jumps use bl.
"""

from spdx import HEADER
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import cornell_scene as scene  # noqa: E402

LEFT, RIGHT, FLOOR, CEILING, BACK, FRONT, DIFFUSE, MIRROR, BOX = range(9)


class Asm:
    def __init__(self):
        self.lines = []
        self.labels = 0

    def __call__(self, line):
        self.lines.append("    " + line)

    def comment(self, text):
        self.lines.append("    # " + text)

    def label(self, name):
        self("label(%s)" % name)

    def new(self, stem):
        self.labels += 1
        return "%s_%d" % (stem, self.labels)

    @staticmethod
    def at(name):
        return "[r7, %d]" % (4 * scene.slot(name))

    def ld(self, reg, name):
        self("vldr(%s, %s)" % (reg, self.at(name)))

    def st(self, reg, name):
        self("vstr(%s, %s)" % (reg, self.at(name)))

    def ldi(self, reg, name):
        self("ldr(%s, %s)" % (reg, self.at(name)))

    def sti(self, reg, name):
        self("str(%s, %s)" % (reg, self.at(name)))

    def skip_unless(self, a, relation, b, label):
        """Branch to label unless a <relation> b (false for NaN, as in numpy)."""
        cond = {">": "ble", "<": "bpl", ">=": "blt", "<=": "bhi"}[relation]
        self("vcmp(%s, %s)" % (a, b))
        self("vmrs(APSR_nzcv, FPSCR)")
        self("%s_w(%s)" % (cond, label))

    def copy(self, dst, src):
        """s-register copy, bits unchanged (there is no vmov between them)."""
        self("vmov(r0, %s)" % src)
        self("vmov(%s, r0)" % dst)

    def jump(self, label):
        self("bl(%s)" % label)

    def dot(self, dst, a, b, tmp):
        """dst = (a0 * b0 + a1 * b1) + a2 * b2"""
        self("vmul(%s, %s, %s)" % (dst, a[0], b[0]))
        self("vmul(%s, %s, %s)" % (tmp, a[1], b[1]))
        self("vadd(%s, %s, %s)" % (dst, dst, tmp))
        self("vmul(%s, %s, %s)" % (tmp, a[2], b[2]))
        self("vadd(%s, %s, %s)" % (dst, dst, tmp))

    def scale3(self, v, k):
        for r in v:
            self("vmul(%s, %s, %s)" % (r, r, k))

    def rand(self):
        self("bl(rand)")

    def box(self, o, d, b, regs, k, missed):
        """Entry distance of the ray (o, d) into box b, in the box's frame:
        regs["tnear"], with the entry face (axis * 2 + positive) in r2; or a
        branch to missed. Uses r0, r1, r3 and the registers in regs."""
        L, LD, t1, t2, tnear, tfar, tmp = (
            regs["l"], regs["ld"], regs["t1"], regs["t2"], regs["tnear"], regs["tfar"], regs["tmp"]
        )
        f = lambda name: "B%d_%s" % (b, name)  # noqa: E731
        for axis, reg, src in zip(("CX", "CY", "CZ"), L, o):
            self.ld(k, f(axis))
            self("vsub(%s, %s, %s)" % (reg, src, k))
        for dst, src in ((L, L), (LD, d)):
            # x' = x * c + z * s; z' = z * c - x * s
            self.ld(k, f("C"))
            self("vmul(%s, %s, %s)" % (tmp[0], src[0], k))
            self("vmul(%s, %s, %s)" % (tmp[1], src[2], k))
            self.ld(k, f("S"))
            self("vmul(%s, %s, %s)" % (tmp[2], src[2], k))
            self("vmul(%s, %s, %s)" % (tmp[3], src[0], k))
            self("vadd(%s, %s, %s)" % (dst[0], tmp[0], tmp[2]))
            self("vsub(%s, %s, %s)" % (dst[2], tmp[1], tmp[3]))
        self.copy(LD[1], d[1])
        for axis, (l, ld, h) in enumerate(zip(L, LD, "XYZ")):
            noswap, joined = self.new("noswap"), self.new("slab")
            self.ld(k, f("NH" + h))
            self("vsub(%s, %s, %s)" % (t1, k, l))
            self("vdiv(%s, %s, %s)" % (t1, t1, ld))
            self.ld(k, f("H" + h))
            self("vsub(%s, %s, %s)" % (t2, k, l))
            self("vdiv(%s, %s, %s)" % (t2, t2, ld))
            self.skip_unless(t1, ">", t2, noswap)
            self("vmov(r0, %s)" % t1)
            self("vmov(r3, %s)" % t2)
            self("vmov(%s, r3)" % t1)
            self("vmov(%s, r0)" % t2)
            self("mov(r1, %d)" % (2 * axis + 1))
            self("b(%s)" % joined)
            self.label(noswap)
            self("mov(r1, %d)" % (2 * axis))
            self.label(joined)
            if axis == 0:
                self.copy(tnear, t1)
                self.copy(tfar, t2)
                self("mov(r2, r1)")
            else:
                up, down = self.new("not_later"), self.new("not_sooner")
                self.skip_unless(t1, ">", tnear, up)
                self.copy(tnear, t1)
                self("mov(r2, r1)")
                self.label(up)
                self.skip_unless(t2, "<", tfar, down)
                self.copy(tfar, t2)
                self.label(down)
        self.skip_unless(tnear, "<=", tfar, missed)
        self.ld(k, "EPSILON")
        self.skip_unless(tnear, ">", k, missed)

    def sphere(self, o, d, prefix, tmp, k, missed):
        """Nearest-hit distance of the ray (o, d) with a sphere into tmp[4],
        or a branch to missed. tmp: six working registers; k: a register for
        constants."""
        oc, bb, cc, scratch = tmp[0:3], tmp[3], tmp[4], tmp[5]
        for axis, reg, src in zip("XYZ", oc, o):
            self.ld(k, prefix + axis)
            self("vsub(%s, %s, %s)" % (reg, src, k))
        self.dot(bb, oc, d, scratch)
        self.dot(cc, oc, oc, scratch)
        self.ld(k, prefix + "R2")
        self("vsub(%s, %s, %s)" % (cc, cc, k))
        self("vmul(%s, %s, %s)" % (oc[0], bb, bb))
        self("vsub(%s, %s, %s)" % (oc[0], oc[0], cc))
        self.ld(k, "ZERO")
        self.skip_unless(oc[0], ">", k, missed)
        self("vsqrt(%s, %s)" % (oc[0], oc[0]))
        self("vneg(%s, %s)" % (bb, bb))
        self("vsub(%s, %s, %s)" % (cc, bb, oc[0]))


def generate():
    a = Asm()
    O, D, T, L = ("s0", "s1", "s2"), ("s3", "s4", "s5"), ("s6", "s7", "s8"), ("s9", "s10", "s11")
    H, N, ALB = ("s13", "s14", "s15"), ("s16", "s17", "s18"), ("s19", "s20", "s21")
    a("ldr(r7, [r3, 0])")
    a("push({r7})")
    a("asr(r7, r7, 1)")
    for i in range(16):
        a("vstr(s%d, [r7, %d])" % (16 + i, 4 * (scene.SAVE_BASE + i)))
    a.comment("this pass's tone-mapping scale: exposure / samples")
    a.ldi("r0", "SAMPLES")
    a("vmov(s31, r0)")
    a("vcvt_f32_s32(s31, s31)")
    a.ld("s30", "EXPOSURE")
    a("vdiv(s30, s30, s31)")
    a.st("s30", "SCALE")
    a("mov(r0, 0)")
    a.sti("r0", "COLUMN")

    a.label("pixel")
    a.comment("random seed: (index * SEED_MUL) ^ (pass * PASS_MUL) ^ SEED_XOR | 1")
    a.ldi("r0", "COLUMN")
    a.ldi("r1", "INDEX")
    a("add(r1, r1, r0)")
    a.ldi("r2", "SEED_MUL")
    a("mul(r1, r2)")
    a.ldi("r2", "PASS")
    a.ldi("r3", "PASS_MUL")
    a("mul(r2, r3)")
    a("eor(r1, r2)")
    a.ldi("r2", "SEED_XOR")
    a("eor(r1, r2)")
    a("mov(r2, 1)")
    a("orr(r1, r2)")
    a("mov(r6, r1)")

    a.comment("camera ray through a jittered point of the box's open front")
    a.rand()
    a.ldi("r0", "COLUMN")
    a("vmov(s29, r0)")
    a("vcvt_f32_s32(s29, s29)")
    a("vadd(s29, s29, s31)")
    a.ld("s28", "INV_SIZE")
    a("vmul(s0, s29, s28)")
    a.rand()
    a.ldi("r0", "ROW")
    a("vmov(s29, r0)")
    a("vcvt_f32_s32(s29, s29)")
    a("vadd(s29, s29, s31)")
    a.ld("s28", "INV_SIZE")
    a("vmul(s29, s29, s28)")
    a.ld("s28", "ONE")
    a("vsub(s1, s28, s29)")
    a.ld("s2", "ZERO")
    for o, d, cam in zip(O, D, ("CAM_X", "CAM_Y", "CAM_Z")):
        a.ld("s28", cam)
        a("vsub(%s, %s, s28)" % (d, o))
    a.dot("s29", D, D, "s28")
    a("vsqrt(s29, s29)")
    a.ld("s28", "ONE")
    a("vdiv(s29, s28, s29)")
    a.scale3(D, "s29")
    for r in T:
        a.ld(r, "ONE")
    for r in L:
        a.ld(r, "ZERO")
    a("mov(r0, 1)")
    a.sti("r0", "SPECULAR")
    a("mov(r0, %d)" % scene.DEPTH)
    a.sti("r0", "BOUNCE")

    a.label("bounce")
    a.comment("the wall the ray leaves the box through")
    a.ld("s12", "FAR")
    a("mov(r5, %d)" % FRONT)
    for o, d, low, high in zip(O, D, (LEFT, FLOOR, FRONT), (RIGHT, CEILING, BACK)):
        neg, join, skip = a.new("behind"), a.new("bound"), a.new("not_nearer")
        a.ld("s28", "ZERO")
        a("vcmp(%s, s28)" % d)
        a("vmrs(APSR_nzcv, FPSCR)")
        a("blt(%s)" % neg)
        a.ld("s29", "ONE")
        a("mov(r1, %d)" % high)
        a("b(%s)" % join)
        a.label(neg)
        a.ld("s29", "ZERO")
        a("mov(r1, %d)" % low)
        a.label(join)
        a("vsub(s29, s29, %s)" % o)
        a("vdiv(s29, s29, %s)" % d)
        a.ld("s28", "EPSILON")
        a.skip_unless("s29", ">", "s28", skip)
        a.skip_unless("s29", "<", "s12", skip)
        a.copy("s12", "s29")
        a("mov(r5, r1)")
        a.label(skip)
    a.ldi("r0", "MODE")
    a("cmp(r0, 0)")
    a("bne_w(nearest_boxes)")
    for kind, prefix in ((DIFFUSE, "D_"), (MIRROR, "M_")):
        skip = a.new("missed")
        a.comment("sphere " + prefix[0])
        a.sphere(O, D, prefix, ("s22", "s23", "s24", "s25", "s26", "s27"), "s28", skip)
        a.ld("s28", "EPSILON")
        a.skip_unless("s26", ">", "s28", skip)
        a.skip_unless("s26", "<", "s12", skip)
        a.copy("s12", "s26")
        a("mov(r5, %d)" % kind)
        a.label(skip)
    a.jump("nearest_done")
    a.label("nearest_boxes")
    nearest = dict(
        l=("s13", "s14", "s15"), ld=("s16", "s17", "s18"), t1="s22", t2="s23", tnear="s19", tfar="s20",
        tmp=("s24", "s25", "s26", "s27"),
    )
    for b in range(2):
        skip = a.new("missed")
        a.comment("box %d" % b)
        a.box(O, D, b, nearest, "s28", skip)
        a.skip_unless("s19", "<", "s12", skip)
        a.copy("s12", "s19")
        a("mov(r5, %d)" % BOX)
        a("mov(r3, %d)" % (8 * b))
        a("add(r3, r3, r2)")
        a.sti("r3", "HIT_FACE")
        a.label(skip)
    a.label("nearest_done")
    a("cmp(r5, %d)" % FRONT)
    a("beq_w(pixel_done)")
    for h, o, d in zip(H, O, D):
        a("vmul(%s, %s, s12)" % (h, d))
        a("vadd(%s, %s, %s)" % (h, o, h))

    a.comment("the light: emission counts only straight from the camera or a mirror")
    a("cmp(r5, %d)" % CEILING)
    a("bne_w(not_light)")
    for h in (H[0], H[2]):
        a.ld("s28", "LIGHT_MIN")
        a.skip_unless(h, ">=", "s28", "not_light")
        a.ld("s28", "LIGHT_MAX")
        a.skip_unless(h, "<=", "s28", "not_light")
    a.ldi("r0", "SPECULAR")
    a("cmp(r0, 0)")
    a("beq_w(pixel_done)")
    for t, l, le in zip(T, L, ("LE_R", "LE_G", "LE_B")):
        a.ld("s28", le)
        a("vmul(s28, %s, s28)" % t)
        a("vadd(%s, %s, s28)" % (l, l))
    a.jump("pixel_done")

    a.label("not_light")
    a("cmp(r5, %d)" % MIRROR)
    a("bne_w(diffuse)")
    a.comment("mirror: reflect")
    a.ld("s27", "M_INV_R")
    for n, h, axis in zip(N, H, "XYZ"):
        a.ld("s28", "M_" + axis)
        a("vsub(%s, %s, s28)" % (n, h))
        a("vmul(%s, %s, s27)" % (n, n))
    a.dot("s29", D, N, "s28")
    a.ld("s28", "TWO")
    a("vmul(s29, s29, s28)")
    for d, n in zip(D, N):
        a("vmul(s28, %s, s29)" % n)
        a("vsub(%s, %s, s28)" % (d, d))
    a.ld("s28", "M_ALB")
    a.scale3(T, "s28")
    for o, h in zip(O, H):
        a.copy(o, h)
    a.jump("next_bounce")

    a.label("diffuse")
    a("cmp(r5, %d)" % BOX)
    a("bne_w(not_box)")
    a.comment("box: the entry face's normal, rotated back to the world")
    a.ldi("r0", "HIT_FACE")
    for b in range(2):
        c, sn = "B%d_C" % b, "B%d_S" % b
        normals = {
            0: ((c, True), ("ZERO", False), (sn, True)),
            1: ((c, False), ("ZERO", False), (sn, False)),
            2: (("ZERO", False), ("ONE", True), ("ZERO", False)),
            3: (("ZERO", False), ("ONE", False), ("ZERO", False)),
            4: ((sn, False), ("ZERO", False), (c, True)),
            5: ((sn, True), ("ZERO", False), (c, False)),
        }
        for face, parts in normals.items():
            nxt = a.new("not_face")
            a("cmp(r0, %d)" % (8 * b + face))
            a("bne_w(%s)" % nxt)
            for n, (name, negate) in zip(N, parts):
                a.ld(n, name)
                if negate:
                    a("vneg(%s, %s)" % (n, n))
            a.jump("box_albedo")
            a.label(nxt)
    a.label("box_albedo")
    for r, ch in zip(ALB, "RGB"):
        a.ld(r, "WHITE_" + ch)
    a.jump("shade")
    a.label("not_box")
    a("cmp(r5, %d)" % DIFFUSE)
    a("bne_w(walls)")
    a.ld("s27", "D_INV_R")
    for n, h, axis in zip(N, H, "XYZ"):
        a.ld("s28", "D_" + axis)
        a("vsub(%s, %s, s28)" % (n, h))
        a("vmul(%s, %s, s27)" % (n, n))
    for r, ch in zip(ALB, "RGB"):
        a.ld(r, "D_ALB_" + ch)
    a.jump("shade")
    a.label("walls")
    for n in N:
        a.ld(n, "ZERO")
    for r, ch in zip(ALB, "RGB"):
        a.ld(r, "WHITE_" + ch)
    for wall, n, negate, color in (
        (LEFT, N[0], False, "RED_"),
        (RIGHT, N[0], True, "GREEN_"),
        (FLOOR, N[1], False, None),
        (CEILING, N[1], True, None),
        (BACK, N[2], True, None),
    ):
        nxt = a.new("not_wall")
        a("cmp(r5, %d)" % wall)
        a("bne_w(%s)" % nxt)
        a.ld(n, "ONE")
        if negate:
            a("vneg(%s, %s)" % (n, n))
        if color:
            for r, ch in zip(ALB, "RGB"):
                a.ld(r, color + ch)
        a.jump("shade")
        a.label(nxt)

    a.label("shade")
    for t, alb in zip(T, ALB):
        a("vmul(%s, %s, %s)" % (t, t, alb))
    for o, h in zip(O, H):
        a.copy(o, h)
    a("mov(r0, 0)")
    a.sti("r0", "SPECULAR")
    a.comment("next event estimation: a random point on the light")
    a.rand()
    a.ld("s28", "LIGHT_SIZE")
    a("vmul(s29, s31, s28)")
    a.ld("s28", "LIGHT_MIN")
    a("vadd(s22, s28, s29)")
    a.rand()
    a.ld("s28", "LIGHT_SIZE")
    a("vmul(s29, s31, s28)")
    a.ld("s28", "LIGHT_MIN")
    a("vadd(s24, s28, s29)")
    W = ("s22", "s23", "s24")
    a("vsub(s22, s22, s0)")
    a.ld("s28", "ONE")
    a("vsub(s23, s28, s1)")
    a("vsub(s24, s24, s2)")
    a.dot("s25", W, W, "s28")
    a("vsqrt(s26, s25)")
    a.ld("s28", "ONE")
    a("vdiv(s27, s28, s26)")
    a.scale3(W, "s27")
    a.dot("s29", N, W, "s28")
    a.ld("s28", "ZERO")
    a.skip_unless("s29", ">", "s28", "unlit")
    a.skip_unless("s23", ">", "s28", "unlit")
    a.comment("g = ((cos_s * cos_l) * LIGHT_K) / dist2")
    a("vmul(s29, s29, s23)")
    a.ld("s28", "LIGHT_K")
    a("vmul(s29, s29, s28)")
    a("vdiv(s29, s29, s25)")
    a.ldi("r0", "MODE")
    a("cmp(r0, 0)")
    a("bne_w(shadow_boxes)")
    for prefix in ("D_", "M_"):
        clear = a.new("clear")
        a.sphere(O, W, prefix, ("s19", "s20", "s21", "s30", "s31", "s12"), "s28", clear)
        a.ld("s28", "EPSILON")
        a.skip_unless("s31", ">", "s28", clear)
        a.skip_unless("s31", "<", "s26", clear)
        a.jump("unlit")
        a.label(clear)
    a.jump("shadow_done")
    a.label("shadow_boxes")
    shadow = dict(
        l=("s12", "s13", "s14"), ld=("s15", "s19", "s20"), t1="s30", t2="s31", tnear="s21", tfar="s27",
        tmp=("s3", "s4", "s5", "s25"),
    )
    for b in range(2):
        clear = a.new("clear")
        a.box(O, W, b, shadow, "s28", clear)
        a.skip_unless("s21", "<", "s26", clear)
        a.jump("unlit")
        a.label(clear)
    a.label("shadow_done")
    for t, l, le in zip(T, L, ("LE_R", "LE_G", "LE_B")):
        a.ld("s28", le)
        a("vmul(s28, %s, s28)" % t)
        a("vmul(s28, s28, s29)")
        a("vadd(%s, %s, s28)" % (l, l))
    a.label("unlit")

    a.comment("the last interaction needs no bounce")
    a.ldi("r4", "BOUNCE")
    a("cmp(r4, 1)")
    a("beq_w(pixel_done)")
    a.comment("cosine-weighted bounce: normal + a random point in the unit ball")
    V = ("s22", "s23", "s24")
    a.label("reject")
    for v in V:
        a.rand()
        a.ld("s28", "TWO")
        a("vmul(%s, s31, s28)" % v)
        a.ld("s28", "ONE")
        a("vsub(%s, %s, s28)" % (v, v))
    a.dot("s25", V, V, "s26")
    a.ld("s28", "EPSILON")
    a.skip_unless("s25", ">", "s28", "reject")
    a.ld("s28", "ONE")
    a.skip_unless("s25", "<=", "s28", "reject")
    a("vsqrt(s25, s25)")
    a.ld("s28", "ONE")
    a("vdiv(s25, s28, s25)")
    for v, n in zip(V, N):
        a("vmul(%s, %s, s25)" % (v, v))
        a("vadd(%s, %s, %s)" % (v, n, v))
    a.dot("s25", V, V, "s26")
    a.ld("s28", "EPSILON")
    a.skip_unless("s25", ">", "s28", "use_normal")
    a("vsqrt(s25, s25)")
    a.ld("s28", "ONE")
    a("vdiv(s25, s28, s25)")
    for d, v in zip(D, V):
        a("vmul(%s, %s, s25)" % (d, v))
    a.jump("next_bounce")
    a.label("use_normal")
    for d, n in zip(D, N):
        a.copy(d, n)

    a.label("next_bounce")
    a.ldi("r4", "BOUNCE")
    a("sub(r4, r4, 1)")
    a.sti("r4", "BOUNCE")
    a("bgt_w(bounce)")

    a.label("pixel_done")
    a.comment("accumulate, tone-map, pack rgb565")
    a.ldi("r0", "ACCUM")
    for i, (l, acc) in enumerate(zip(L, ("s22", "s23", "s24"))):
        a("vldr(%s, [r0, %d])" % (acc, 4 * i))
        a("vadd(%s, %s, %s)" % (acc, acc, l))
        a("vstr(%s, [r0, %d])" % (acc, 4 * i))
    a("add(r0, 12)")
    a.sti("r0", "ACCUM")
    a.ld("s27", "SCALE")
    for acc, k, reg in zip(("s22", "s23", "s24"), ("K5", "K6", "K5"), ("r1", "r2", "r3")):
        under = a.new("under")
        a("vmul(%s, %s, s27)" % (acc, acc))
        a.ld("s26", "ONE")
        a.skip_unless(acc, ">", "s26", under)
        a.ld(acc, "ONE")
        a.label(under)
        a("vsqrt(%s, %s)" % (acc, acc))
        a.ld("s26", k)
        a("vmul(%s, %s, s26)" % (acc, acc))
        a("vcvt_s32_f32(%s, %s)" % (acc, acc))
        a("vmov(%s, %s)" % (reg, acc))
    a("lsl(r1, r1, 11)")
    a("lsl(r2, r2, 5)")
    a("orr(r1, r2)")
    a("orr(r1, r3)")
    a.ldi("r0", "OUT")
    a("strh(r1, [r0, 0])")
    a("add(r0, 2)")
    a.sti("r0", "OUT")
    a.ldi("r0", "COLUMN")
    a("add(r0, 1)")
    a.sti("r0", "COLUMN")
    a.ldi("r1", "COUNT")
    a("cmp(r0, r1)")
    a("blt_w(pixel)")

    for i in range(16):
        a("vldr(s%d, [r7, %d])" % (16 + i, 4 * (scene.SAVE_BASE + i)))
    a("pop({r0})")
    a.jump("done")

    a.comment("rand: xorshift32 of r6; s31 = (bits >> 9 | 1.0's bits) - 1.0. Uses r0, r1, s30.")
    a.label("rand")
    a("lsl(r0, r6, 13)")
    a("eor(r6, r0)")
    a("lsr(r0, r6, 17)")
    a("eor(r6, r0)")
    a("lsl(r0, r6, 5)")
    a("eor(r6, r0)")
    a("lsr(r0, r6, 9)")
    a.ldi("r1", "ONE_BITS")
    a("orr(r0, r1)")
    a("vmov(s31, r0)")
    a.ld("s30", "ONE")
    a("vsub(s31, s31, s30)")
    a("bx(lr)")
    a.label("done")
    return a.lines


HEAD = '''"""Generated by tools/gen_cornell_asm.py: edit that.

trace_row(block_address): one path-traced sample for each pixel of a row of
the Cornell box, bit-identical to tools/cornell_ref.py. Relabelled as viper by
tools/asm_to_viper.py, so the argument object is at [r3].
"""

import micropython


@micropython.asm_thumb
def trace_row(r0, r1, r2, r3):
'''


def main():
    out = ROOT / "turbo_source" / "cornell_asm.py"
    out.write_text(HEADER + HEAD + "\n".join(generate()) + "\n")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
