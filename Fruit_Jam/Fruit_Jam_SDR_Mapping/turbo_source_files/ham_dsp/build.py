# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Build _ham_dsp.<arch>.mpy from a CircuitPython checkout and GNU tools.

python3 build.py --circuitpython /path/to/circuitpython [--gcc arm-none-eabi-gcc]
Native ABI armv7emsp, hard float (RP2350: the Fruit Jam).

python3 build.py --circuitpython ... --arch rv32imc --gcc riscv32-esp-elf-gcc
Native ABI rv32imc, with the F extension and the ilp32f ABI as the
firmware (ESP32-P4: the Metro ESP32-P4).

The output is _ham_dsp.armv7emsp.mpy or _ham_dsp.rv32imc.mpy: `import _ham_dsp`
loads the one for the board's microcontroller.cpu.architecture.
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
a.output = a.output or f"_ham_dsp.{a.arch}.mpy"
cp = a.circuitpython.resolve()
here = Path(__file__).resolve().parent
(here / "build").mkdir(exist_ok=True)
if a.arch == "armv7emsp":
    cpu = ["-mthumb", "-mcpu=cortex-m4", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard"]
else:
    cpu = ["-march=rv32imafc_zicsr_zifencei", "-mabi=ilp32f", "-mno-relax"]


def run(args):
    subprocess.run(args, cwd=here, check=True)


run(
    [
        sys.executable,
        str(cp / "tools/mpy_ld.py"),
        "--arch",
        a.arch,
        "--preprocess",
        "-o",
        "build/_ham_dsp.config.h",
        "_ham_dsp.c",
    ]
)
flags = [
    *cpu,
    "-std=c99",
    "-O3",
    "-Wall",
    "-Werror",
    "-DNDEBUG",
    "-DNO_QSTR",
    "-DMICROPY_ENABLE_DYNRUNTIME",
    "-DMP_CONFIGFILE=<build/_ham_dsp.config.h>",
    "-I.",
    "-I" + str(cp),
    "-fpic",
    "-fno-common",
    "-fno-tree-loop-distribute-patterns",
    "-fno-math-errno",
    "-U_FORTIFY_SOURCE",
    "-DMICROPY_FLOAT_IMPL=MICROPY_FLOAT_IMPL_FLOAT",
]
run([a.gcc, *flags, "-c", "_ham_dsp.c", "-o", "build/_ham_dsp.o"])
run(
    [
        sys.executable,
        str(cp / "tools/mpy_ld.py"),
        "--arch",
        a.arch,
        "--qstrs",
        "build/_ham_dsp.config.h",
        "-o",
        a.output,
        "build/_ham_dsp.o",
    ]
)
