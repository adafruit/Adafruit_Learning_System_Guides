# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build _chess_engine.rv32imc.mpy from a CircuitPython checkout.

python3 build.py --circuitpython /path/to/circuitpython

The chess engine is C++ (a port of Stockfish), built as a CircuitPython native
module for rv32imc (ESP32-P4: the Metro ESP32-P4) with the Makefile in this
folder. It needs:

- a CircuitPython checkout at the same .mpy version as the firmware
  (11.0.0-alpha.3 or later 11.x),
- pyelftools for the checkout's tools/mpy_ld.py (pip install pyelftools),
- Espressif's RISC-V GCC (riscv32-esp-elf-*, from ESP-IDF's tool installer) on
  PATH, or its bin folder passed with --toolchain.

The build runs in a temporary copy of this folder, so no build files are left
here. The output is _chess_engine.rv32imc.mpy: copy it next to code.py, and
`import _chess_engine` loads it on a board whose
microcontroller.cpu.architecture is rv32imc.
"""

from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument("--circuitpython", required=True, type=Path)
p.add_argument(
    "--toolchain",
    type=Path,
    help="folder with riscv32-esp-elf-gcc (default: find it on PATH)",
)
p.add_argument("--output", default="_chess_engine.rv32imc.mpy", type=Path)
a = p.parse_args()
here = Path(__file__).resolve().parent

env = dict(os.environ)
if a.toolchain:
    env["PATH"] = str(a.toolchain.resolve()) + os.pathsep + env["PATH"]
if not shutil.which("riscv32-esp-elf-gcc", path=env["PATH"]):
    sys.exit("riscv32-esp-elf-gcc not found: put it on PATH or use --toolchain")

with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp) / "chess_game"
    shutil.copytree(
        here, work, ignore=shutil.ignore_patterns("build-*", "*.mpy", "__pycache__")
    )
    subprocess.run(
        [
            "make",
            "MPY_DIR=" + str(a.circuitpython.resolve()),
            "PYTHON=" + sys.executable,
        ],
        cwd=work,
        env=env,
        check=True,
    )
    shutil.copyfile(work / "_chess_engine.mpy", a.output)
print("wrote", a.output)
