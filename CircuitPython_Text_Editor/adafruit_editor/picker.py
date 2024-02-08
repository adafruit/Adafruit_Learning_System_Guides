# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import usb_cdc
from . import dang as curses
from . import util
#pylint: disable=redefined-builtin

def print(message):
    usb_cdc.data.write(f"{message}\r\n".encode("utf-8"))


always = ["code.py", "boot.py", "settings.toml", "boot_out.txt"]
good_extensions = [".py", ".toml", ".txt", ".json"]


def os_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False


def isdir(filename):
    return os.stat(filename)[0] & 0o40_000


def has_good_extension(filename):
    for g in good_extensions:
        if filename.endswith(g):
            return True
    return False


def picker(stdscr, options, notes=(), start_idx=0):
    stdscr.erase()
    stdscr.addstr(curses.LINES - 1, 0, "Enter: select | ^C: quit | ^N: New")
    del options[curses.LINES - 1:]
    for row, option in enumerate(options):
        if row < len(notes) and (note := notes[row]):
            option = f"{option} {note}"

        stdscr.addstr(row, 3, option)

    old_idx = None
    idx = start_idx
    while True:
        if idx != old_idx:
            if old_idx is not None:
                stdscr.addstr(old_idx, 0, "  ")
            stdscr.addstr(idx, 0, "=>")
            old_idx = idx

        k = stdscr.getkey()

        if k == "KEY_DOWN":
            idx = min(idx + 1, len(options) - 1)
        elif k == "KEY_UP":
            idx = max(idx - 1, 0)
        elif k == "\n":
            return options[idx]

        # ctrl-N
        elif k == "\x0E":
            if not util.readonly():
                new_file_name = new_file(stdscr)
                if new_file_name is not None:
                    return new_file_name


# pylint: disable=inconsistent-return-statements
def new_file(stdscr):
    stdscr.erase()
    new_file_name = input("New File Name: ")
    if os_exists(new_file_name):
        print("Error: File Already Exists")
        return
    with open(new_file_name, "w") as f:
        f.write("")

    return new_file_name


def pick_file():
    options = sorted(
        (
            g
            for g in os.listdir(".")
            if g not in always and not isdir(g) and not g.startswith(".")
        ),
        key=lambda filename: (not has_good_extension(filename), filename),
    ) + always[:]
    notes = [None if os_exists(filename) else "(NEW)" for filename in options]
    return curses.wrapper(picker, options, notes)
