# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Build _hf_sstv.mpy from a CircuitPython checkout and Arm GNU tools.

python3 build.py --circuitpython /path/to/circuitpython [--gcc arm-none-eabi-gcc]
Native ABI armv7emsp, hard float.
"""

from pathlib import Path
import argparse
import os
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument("--circuitpython", required=True, type=Path)
p.add_argument("--gcc", default=os.environ.get("ARM_GCC", "arm-none-eabi-gcc"))
p.add_argument("--output", default="_hf_sstv.mpy")
a = p.parse_args()
cp = a.circuitpython.resolve()
here = Path(__file__).resolve().parent
(here / "build").mkdir(exist_ok=True)


def run(args):
    subprocess.run(args, cwd=here, check=True)


run(
    [
        sys.executable,
        str(cp / "tools/mpy_ld.py"),
        "--arch",
        "armv7emsp",
        "--preprocess",
        "-o",
        "build/_hf_sstv.config.h",
        "_hf_sstv.c",
    ]
)
flags = [
    "-mthumb",
    "-mcpu=cortex-m4",
    "-mfpu=fpv4-sp-d16",
    "-mfloat-abi=hard",
    "-std=c99",
    "-O3",
    "-Wall",
    "-Werror",
    "-DNDEBUG",
    "-DNO_QSTR",
    "-DMICROPY_ENABLE_DYNRUNTIME",
    "-DMP_CONFIGFILE=<build/_hf_sstv.config.h>",
    "-I.",
    "-I" + str(cp),
    "-fpic",
    "-fno-common",
    "-fno-tree-loop-distribute-patterns",
    "-fno-math-errno",
    "-U_FORTIFY_SOURCE",
    "-DMICROPY_FLOAT_IMPL=MICROPY_FLOAT_IMPL_FLOAT",
]
run([a.gcc, *flags, "-c", "_hf_sstv.c", "-o", "build/_hf_sstv.o"])
run(
    [
        sys.executable,
        str(cp / "tools/mpy_ld.py"),
        "--arch",
        "armv7emsp",
        "--qstrs",
        "build/_hf_sstv.config.h",
        "-o",
        a.output,
        "build/_hf_sstv.o",
    ]
)
