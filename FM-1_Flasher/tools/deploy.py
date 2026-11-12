#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Copy the flasher UI to a CIRCUITPY drive, compiled to .mpy.

  .venv/bin/python tools/deploy.py --mpy-cross ref/cp-metro-p4/mpy-cross/build/mpy-cross

Copies FM-1_Flasher_Code (what the guide's Project Bundle has) to the board:
code.py, fonts/ (.fmf), the splash (art/splash_text_320.png as a 16-color
splash.bmp, needs Pillow; also refreshed in FM-1_Flasher_Code), and lib/ with
fm1ui and the fm1 libraries compiled to .mpy. It also sets
CIRCUITPY_SDCARD_USB = false in settings.toml (takes effect after a reset). The
mpy-cross must match the board's CircuitPython version. A .py of the same
name on the board is removed, so the .mpy is the one imported.

The board is the Metro ESP32-P4 (checked in the drive's boot_out.txt). It also
needs adafruit_ili9341, adafruit_focaltouch, adafruit_bus_device,
adafruit_usb_host_descriptors, adafruit_requests and
adafruit_connection_manager from the bundle in lib/.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "FM-1_Flasher_Code")  # what goes on CIRCUITPY, as the Project Bundle has it
FM1_LIBS = ("fm1proto.py", "fm1update.py", "fm1usb.py", "fm1catalog.py", "fm1pic.py")
# Keeps the computer from reading /sd over USB while the flasher uses it: two
# users of one FAT file system get stale sectors (DEVNOTES §6.18).
SETTINGS = {"CIRCUITPY_SDCARD_USB": "false"}
SPLASH = "art/splash_text_320.png"  # 320x240 (tools/make_splash.py); fm1ui.metro_p4.SPLASH
BOARD_ID = "adafruit_metro_esp32p4"


def board_id(drive):
    """The Board ID line of the drive's boot_out.txt, or None."""
    try:
        with open(os.path.join(drive, "boot_out.txt")) as f:
            for line in f:
                if line.startswith("Board ID:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def write_splash(drive):
    """Convert the splash PNG to an 8-bit BMP with 16 colors, which OnDiskBitmap
    reads (154 KB; Pillow writes no 4-bit BMP). Written only when it changed,
    so the board doesn't reload."""
    from PIL import Image
    im = Image.open(os.path.join(ROOT, SPLASH)).convert("RGB")
    im = im.quantize(16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    buf = BytesIO()
    im.save(buf, "BMP")
    data = buf.getvalue()
    dst = os.path.join(drive, "splash.bmp")
    try:
        with open(dst, "rb") as f:
            if f.read() == data:
                return
    except OSError:
        pass
    with open(dst, "wb") as f:
        f.write(data)


def update_settings(drive):
    """Set SETTINGS in the board's settings.toml, keeping any other lines."""
    path = os.path.join(drive, "settings.toml")
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError:
        lines = []
    lines = [ln for ln in lines if ln.split("=", 1)[0].strip() not in SETTINGS]
    lines += ["%s = %s" % kv for kv in SETTINGS.items()]
    text = "\n".join(lines) + "\n"
    try:
        with open(path) as f:
            if f.read() == text:
                return
    except OSError:
        pass
    with open(path, "w") as f:
        f.write(text)


def compile_to(mpy_cross, src, dst_dir):
    """Compile locally, then copy the whole file: mpy-cross's small writes
    straight to the CIRCUITPY drive are very slow."""
    name = os.path.splitext(os.path.basename(src))[0]
    dst = os.path.join(dst_dir, name + ".mpy")
    os.makedirs(dst_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, name + ".mpy")
        subprocess.run([mpy_cross, "-s", os.path.basename(src), "-o", out, src], check=True)
        with open(out, "rb") as f:
            data = f.read()
    try:
        with open(dst, "rb") as f:
            if f.read() == data:
                return dst  # unchanged: don't make the board reload
    except OSError:
        pass
    with open(dst, "wb") as f:
        f.write(data)
    stale = os.path.join(dst_dir, name + ".py")
    if os.path.exists(stale):
        os.remove(stale)
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drive", default="/Volumes/CIRCUITPY")
    ap.add_argument("--mpy-cross", required=True)
    args = ap.parse_args()
    found = board_id(args.drive)
    if found != BOARD_ID:
        print("warning: %s's boot_out.txt says %s, not %s" % (args.drive, found, BOARD_ID))

    lib = os.path.join(args.drive, "lib")
    n = 0
    for name in FM1_LIBS:
        compile_to(args.mpy_cross, os.path.join(CODE, "lib", name), lib)
        n += 1
    for src in sorted(glob.glob(os.path.join(CODE, "lib", "fm1ui", "*.py"))):
        compile_to(args.mpy_cross, src, os.path.join(lib, "fm1ui"))
        n += 1
    fonts = os.path.join(args.drive, "fonts")
    os.makedirs(fonts, exist_ok=True)
    for f in glob.glob(os.path.join(CODE, "fonts", "*.fmf")):
        dst = os.path.join(fonts, os.path.basename(f))
        if not (os.path.exists(dst) and open(dst, "rb").read() == open(f, "rb").read()):
            shutil.copy(f, fonts)
    write_splash(CODE)  # the Project Bundle's copy
    write_splash(args.drive)
    update_settings(args.drive)
    shutil.copy(os.path.join(CODE, "code.py"), os.path.join(args.drive, "code.py"))
    os.sync()
    print("deployed %d modules, fonts, the splash, settings.toml and code.py to %s" % (n, args.drive))


if __name__ == "__main__":
    sys.exit(main())
