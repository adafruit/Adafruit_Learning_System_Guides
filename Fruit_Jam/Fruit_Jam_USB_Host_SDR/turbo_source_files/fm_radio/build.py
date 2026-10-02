# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Build the native module from a pinned CircuitPython checkout and Arm GNU tools."""
from pathlib import Path
import argparse, os, subprocess, sys

p = argparse.ArgumentParser()
p.add_argument('--circuitpython', required=True, type=Path)
p.add_argument('--gcc', default=os.environ.get('ARM_GCC', 'arm-none-eabi-gcc'))
p.add_argument('--output', default='_fm_turbo95.mpy')
a = p.parse_args();
cp = a.circuitpython.resolve();
here = Path(__file__).resolve().parent
(here / 'build').mkdir(exist_ok=True)

def run(args):
    subprocess.run(args, cwd=here, check=True)


run([sys.executable, str(cp / 'tools/mpy_ld.py'), '--arch', 'armv7emsp', '--preprocess', '-o',
     'build/_fm_turbo.config.h', '_fm_turbo.c'])
flags = ['-mthumb', '-mcpu=cortex-m4', '-mfpu=fpv4-sp-d16', '-mfloat-abi=hard', '-std=c99', '-O3', '-Wall', '-Werror',
         '-DNDEBUG', '-DNO_QSTR', '-DMICROPY_ENABLE_DYNRUNTIME', '-DMP_CONFIGFILE=<build/_fm_turbo.config.h>', '-I.',
         '-I' + str(cp), '-fpic', '-fno-common', '-fno-tree-loop-distribute-patterns', '-U_FORTIFY_SOURCE',
         '-DMICROPY_FLOAT_IMPL=MICROPY_FLOAT_IMPL_FLOAT']
run([a.gcc, *flags, '-c', '_fm_turbo.c', '-o', 'build/wrapper.o'])
run([sys.executable, str(cp / 'tools/mpy_ld.py'), '--arch', 'armv7emsp', '--qstrs', 'build/_fm_turbo.config.h', '-o',
     a.output, 'build/wrapper.o'])
