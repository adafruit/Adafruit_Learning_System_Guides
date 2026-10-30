# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Build _ft8.<arch>.mpy from a CircuitPython checkout and GNU tools.

python3 build.py --circuitpython /path/to/circuitpython [--gcc arm-none-eabi-gcc]
Native ABI armv7emsp, hard float (RP2350: the Fruit Jam).

python3 build.py --circuitpython ... --arch rv32imc --gcc riscv32-esp-elf-gcc
Native ABI rv32imc, with the F extension and the ilp32f ABI as the
firmware (ESP32-P4: the Metro ESP32-P4).

The output is _ft8.armv7emsp.mpy or _ft8.rv32imc.mpy: `import _ft8`
loads the one for the board's microcontroller.cpu.architecture.

libgcc is linked in for ft8_lib's 64-bit division (message unpacking).
"""

from pathlib import Path
import argparse
import os
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument("--circuitpython", required=True, type=Path)
p.add_argument("--arch", default="armv7emsp", choices=("armv7emsp", "rv32imc"))
p.add_argument("--gcc", default=os.environ.get("ARM_GCC", "arm-none-eabi-gcc"))
p.add_argument("--output")
a = p.parse_args()
a.output = a.output or f"_ft8.{a.arch}.mpy"
cp = a.circuitpython.resolve()
here = Path(__file__).resolve().parent
(here / "build").mkdir(exist_ok=True)
if a.arch == "armv7emsp":
    cpu = ["-mthumb", "-mcpu=cortex-m4", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard"]
else:
    cpu = ["-march=rv32imafc_zicsr_zifencei", "-mabi=ilp32f", "-mno-relax"]


def run(args, **kw):
    return subprocess.run(args, cwd=here, check=True, **kw)


libgcc = run([a.gcc, *cpu, "-print-libgcc-file-name"],
             capture_output=True, text=True).stdout.strip()
run(
    [
        sys.executable,
        str(cp / "tools/mpy_ld.py"),
        "--arch",
        a.arch,
        "--preprocess",
        "-o",
        "build/_ft8.config.h",
        "_ft8.c",
    ]
)
flags = [
    *cpu,
    "-std=gnu99",
    "-O2",
    "-Wall",
    "-Werror",
    "-Wno-unused-function",
    "-Wno-format",
    "-Wno-unused-variable",          # (ft8_lib: variables only its debug logging reads)
    "-DNDEBUG",
    "-DNO_QSTR",
    "-DMICROPY_ENABLE_DYNRUNTIME",
    "-DMP_CONFIGFILE=<build/_ft8.config.h>",
    "-I.",
    "-I" + str(cp),
    "-fpic",
    "-fno-common",
    "-fno-tree-loop-distribute-patterns",
    "-fno-math-errno",
    "-ffp-contract=off",
    "-U_FORTIFY_SOURCE",
    "-DMICROPY_FLOAT_IMPL=MICROPY_FLOAT_IMPL_FLOAT",
]
run([a.gcc, *flags, "-c", "_ft8.c", "-o", "build/_ft8.o"])
run(
    [
        sys.executable,
        str(cp / "tools/mpy_ld.py"),
        "--arch",
        a.arch,
        "--qstrs",
        "build/_ft8.config.h",
        "-l",
        libgcc,
        "-o",
        a.output,
        "build/_ft8.o",
    ]
)
