# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""Runs MicroPython/CircuitPython's tools/mpy_ld.py with a fix applied in memory.

usage: mpy_ld_fixed.py PATH/TO/mpy_ld.py [mpy_ld arguments...]

Bug (found 2026-11-16 in CircuitPython main, MicroPython v1.29 merge): for
R_RISCV_PCREL_LO12_S / R_RISCV_LO12_S (S-type store with a folded low-12 address,
e.g. "sw a5, %pcrel_lo(.L0)(a4)") mpy_ld keeps `existing & 0xFE000F80` -- the
old immediate bits -- and drops the registers, funct3 and opcode, so every such
store becomes a garbage instruction. The mask must be 0x01FFF07F. The fix below
is a no-op once mpy_ld has it.
"""

import sys

BUGGY = "((existing & 0xFE000F80) | ((lower & 0xFE0) << 20) | ((lower & 0x1F) << 7))"
FIXED = "((existing & 0x01FFF07F) | ((lower & 0xFE0) << 20) | ((lower & 0x1F) << 7))"

path = sys.argv[1]
with open(path) as f:
    src = f.read()
if BUGGY in src:
    src = src.replace(BUGGY, FIXED)
elif FIXED not in src:
    sys.exit(
        "mpy_ld_fixed.py: the S-type relocation code in %s has changed; check it" % path
    )
sys.argv = [path] + sys.argv[2:]
sys.path.insert(0, path.rsplit("/", 1)[0])
exec(  # pylint: disable=exec-used
    compile(src, path, "exec"), {"__name__": "__main__", "__file__": path}
)
