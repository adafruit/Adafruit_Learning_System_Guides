#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Run a Python file on the Fruit Jam through the raw REPL and print its output.

    python3 tools/run_on_board.py probe.py

Interrupts whatever code.py is doing, and restarts it afterwards (soft
reboot) so the demo comes back; --stay leaves the board at the REPL.
"""

import argparse
import sys
import time

import serial

from serial_log import find_port


class Reader:
    """Serial input with lookahead, so bytes after one marker aren't lost."""

    def __init__(self, port):
        self.port = port
        self.pending = b""

    def until(self, marker, timeout):
        end = time.monotonic() + timeout
        while marker not in self.pending:
            if time.monotonic() > end:
                raise TimeoutError("waiting for %r, got %r" % (marker, self.pending[-200:]))
            self.pending += self.port.read(4096)
        data, _, self.pending = self.pending.partition(marker)
        return data + marker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--port")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--stay", action="store_true", help="stay at the REPL instead of restarting code.py")
    options = parser.parse_args()
    with open(options.file, "rb") as source:
        code = source.read()
    with serial.Serial(options.port or find_port(), 115200, timeout=0.1) as port:
        reader = Reader(port)
        # Interrupt until we reach the REPL; code.py may be (re)starting from an
        # auto-reload, which swallows an early Ctrl-C.
        for _ in range(20):
            port.write(b"\x03")
            time.sleep(0.3)
            reader.pending += port.read(65536)
            if b"Press any key" in reader.pending:
                port.write(b"\r")
                time.sleep(0.3)
                reader.pending += port.read(65536)
            if reader.pending.endswith(b">>> "):
                break
        reader.until(b">>> ", 5)
        reader.pending = b""
        port.write(b"\x01")  # raw REPL
        reader.until(b"raw REPL; CTRL-B to exit\r\n>", 5)
        for i in range(0, len(code), 256):
            port.write(code[i : i + 256])
            time.sleep(0.01)
        port.write(b"\x04")
        reader.until(b"OK", 5)
        # output, \x04, errors, \x04, then the next > prompt
        try:
            data = reader.until(b"\x04>", options.timeout)
        except (serial.SerialException, TimeoutError) as error:
            # e.g. the watchdog reset the board: show what it printed first
            sys.stdout.write(reader.pending.decode("utf-8", "replace"))
            sys.exit("\nboard stopped answering: %s" % error)
        output, _, errors = data[:-2].partition(b"\x04")
        sys.stdout.write(output.decode("utf-8", "replace"))
        if errors.strip():
            sys.stdout.write(errors.decode("utf-8", "replace"))
        port.write(b"\x02")  # back to the friendly REPL
        if not options.stay:
            time.sleep(0.2)
            port.write(b"\x04")  # soft reboot: code.py runs again


if __name__ == "__main__":
    main()
