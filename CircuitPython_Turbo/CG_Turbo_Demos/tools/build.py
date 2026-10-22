#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Compile turbo_source/*.py to .mpy in CG_Turbo_Demos_Code/, and optionally deploy.

    python3 tools/build.py            # compile only
    python3 tools/build.py --deploy   # compile, then copy CG_Turbo_Demos_Code/ to CIRCUITPY
    python3 tools/build.py --bench    # also compile tools/bench/fbtest.py (deploy copies fb_bench.py)

CG_Turbo_Demos_Code/ is what goes on the board, and what the Learn guide's
Project Bundle zips: the demos (plain .py), their data and the compiled Turbo
modules, which are committed so the bundle needs no build. The first deploy
saves the board's existing code.py to backup/. Source .py files in
turbo_source/ are never copied to the board, so they can't shadow the
compiled modules.

The compiled modules are .mpy v6.3 for armv7emsp: they load on any
CircuitPython with that .mpy version and Turbo loading (RP2xxx, 10.3.1 on).
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MPY_CROSS = ROOT / "tools" / "mpy-cross"
ARCH = "armv7emsp"
SOURCE = ROOT / "turbo_source"
CODE = ROOT / "CG_Turbo_Demos_Code"
BENCH = ROOT / "tools" / "bench"
BACKUP = ROOT / "backup"


def copy_if_changed(source, dest, label):
    """Copy unless dest already has the same bytes (skips slow rewrites and reloads)."""
    data = source.read_bytes()
    if dest.exists() and dest.stat().st_size == len(data) and dest.read_bytes() == data:
        return
    dest.write_bytes(data)
    print("copied", source.name, "->", label)


def compile_one(source, output):
    subprocess.run([str(MPY_CROSS), "-march=" + ARCH, "-s", source.name, "-o", str(output), str(source)], check=True)
    if "@micropython.asm_thumb" in source.read_text():
        # the stock turbo loader has no inline assembler: load asm as viper
        subprocess.run([sys.executable, str(ROOT / "tools" / "asm_to_viper.py"), str(output)], check=True)
    print("compiled", source.relative_to(ROOT), "->", output.relative_to(ROOT), output.stat().st_size, "bytes")
    return output


def compile_all(bench):
    if not MPY_CROSS.exists():
        sys.exit(
            "tools/mpy-cross is missing. Download Adafruit's build that writes .mpy v6.3\n"
            "(e.g. the one matching your board's firmware, boot_out.txt) from\n"
            "https://adafruit-circuit-python.s3.amazonaws.com/index.html?prefix=bin/mpy-cross/\n"
            "and save it as tools/mpy-cross (chmod +x)."
        )
    for source in sorted(SOURCE.glob("*.py")):
        compile_one(source, CODE / (source.stem + ".mpy"))
    if bench:
        (ROOT / "build").mkdir(exist_ok=True)
        return [compile_one(BENCH / "fbtest.py", ROOT / "build" / "fbtest.mpy"), BENCH / "fb_bench.py"]
    return []


def board_files(extra):
    """(path on CIRCUITPY, source): the code folder, then any extras, code.py
    last, so the auto-reload it triggers sees everything else."""
    files = [(path.relative_to(CODE).as_posix(), path) for path in sorted(CODE.rglob("*")) if path.is_file()]
    files = [f for f in files if "__pycache__" not in f[0] and f[0] != ".DS_Store"]
    files += [(path.name, path) for path in extra]
    return sorted(files, key=lambda f: f[0] == "code.py")


def deploy(mount, extra):
    if not (mount / "boot_out.txt").exists():
        sys.exit("no CIRCUITPY drive at %s" % mount)
    existing = mount / "code.py"
    saved = BACKUP / "code.py.orig"
    if existing.exists() and not saved.exists():
        BACKUP.mkdir(exist_ok=True)
        shutil.copyfile(existing, saved)
        print("saved board's code.py to", saved.relative_to(ROOT))
    for path, source in board_files(extra):
        (mount / path).parent.mkdir(parents=True, exist_ok=True)
        copy_if_changed(source, mount / path, "/" + path.rsplit("/", 1)[0] if "/" in path else "/")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deploy", action="store_true", help="copy to the CIRCUITPY drive")
    parser.add_argument("--bench", action="store_true", help="also build (and deploy) the framebuffer benchmark")
    parser.add_argument("--mount", default="/Volumes/CIRCUITPY", type=pathlib.Path)
    options = parser.parse_args()
    extra = compile_all(options.bench)
    if options.deploy:
        deploy(options.mount, extra)


if __name__ == "__main__":
    main()
