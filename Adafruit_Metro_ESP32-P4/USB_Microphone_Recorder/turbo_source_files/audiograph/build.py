# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Build _audiograph.rv32imc.mpy from a CircuitPython checkout's mpy-cross.

python3 build.py --circuitpython /path/to/circuitpython

Build mpy-cross first (make -C mpy-cross in the checkout). _audiograph.py is
viper code: the firmware doesn't compile @micropython.viper itself, but loads
it precompiled as native rv32imc code (ESP32-P4: the Metro ESP32-P4).

The output is _audiograph.rv32imc.mpy: copy it next to code.py, and
`import _audiograph` loads it on a board whose microcontroller.cpu.architecture
is rv32imc.
"""

from pathlib import Path
import argparse
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--circuitpython", required=True, type=Path)
p.add_argument(
    "--mpy-cross",
    type=Path,
    help="mpy-cross to use (default: the checkout's mpy-cross/build/mpy-cross)",
)
p.add_argument("--output", default="_audiograph.rv32imc.mpy")
a = p.parse_args()
mpy_cross = a.mpy_cross or a.circuitpython.resolve() / "mpy-cross/build/mpy-cross"
here = Path(__file__).resolve().parent

subprocess.run(
    [str(mpy_cross), "-march=rv32imc", "-o", a.output, "_audiograph.py"],
    cwd=here,
    check=True,
)
