# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''CLUE boot configuration: optional Python-writable filesystem.

CircuitPython by default mounts CIRCUITPY as read-only when USB is
connected, so Python can't write files. To capture BLE packets to a
file (Listen Mode in code.py) while USB is connected, we need to flip
that.

Two ways to enter capture mode:

1. **Marker file**: drop a file named `capture_mode.txt` onto the
   CIRCUITPY drive while USB is connected, then reset. boot.py sees
   the marker and remounts the filesystem as Python-writable.

2. **NVM flag**: code.py can request "next boot in capture mode" via
   a byte in microcontroller.nvm. This survives reboots and works
   regardless of who currently owns the filesystem. boot.py also
   creates the marker file in this case so the user can see the
   mode is engaged.

To exit capture mode: open the REPL and run
    import os; os.remove("/capture_mode.txt")
then reset. The filesystem returns to host-writable.
'''
# Target: Adafruit CLUE (nRF52840) - the BLE remote
import os
import storage
import microcontroller

_MARKER = "/capture_mode.txt"
_NVM_FLAG_BYTE = 0  # NVM byte 0: 1 = request capture mode on this boot

marker_present = False
try:
    os.stat(_MARKER)
    marker_present = True
except OSError:
    pass

# NVM-requested capture mode: code.py wrote 1 to byte 0 to ask for
# capture mode on this boot. Honor it by remounting writable and
# creating the marker file (which clears the NVM flag for next time).
nvm_request = microcontroller.nvm[_NVM_FLAG_BYTE] == 1

if marker_present:
    storage.remount("/", readonly=False)
    print("[boot] Capture mode (marker file present)")
elif nvm_request:
    storage.remount("/", readonly=False)
    # Create the marker file so user can SEE that capture mode is active.
    # Content includes the literal REPL commands to undo it - paste-ready
    # without leading whitespace, so users who open the file in any text
    # editor can copy/paste directly into the serial REPL.
    try:
        with open(_MARKER, "w", encoding="utf-8") as f:
            f.write(
                "Capture mode active.\n"
                "This file makes CIRCUITPY Python-writable so Listen Mode\n"
                "can save captures. While this file exists, you CANNOT\n"
                "drag-drop new code onto the drive.\n"
                "\n"
                "To return to dev mode (drag-drop), open the serial REPL,\n"
                "press Ctrl+C to interrupt, then paste these lines:\n"
                "\n"
                "import os\n"
                "os.remove(\"/capture_mode.txt\")\n"
                "\n"
                "Then reset the CLUE.\n"
            )
        # Clear the NVM flag - we honored it
        microcontroller.nvm[_NVM_FLAG_BYTE] = 0
        print("[boot] Capture mode (NVM-requested, marker created)")
    except OSError as err:
        print(f"[boot] Capture mode requested but write failed: {err}")
else:
    print("[boot] Dev mode: USB host has filesystem write access")
