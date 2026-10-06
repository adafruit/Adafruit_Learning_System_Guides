#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Relabel the @micropython.asm_thumb functions in a .mpy as viper functions.

CircuitPython's turbo builds (CIRCUITPY_LOAD_NATIVE) load viper machine code
but leave out the inline assembler, so an asm_thumb function in a .mpy comes
back as a broken bytecode function.

This rewrites every asm raw code in the file: ASM -> VIPER, and the two
asm-only header fields (argument count and type signature) dropped.
Run it after mpy-cross:

    mpy-cross -march=armv7emsp eyes_viper.py
    python3 asm_to_viper.py eyes_viper.mpy

"""
import sys

KIND_BYTECODE, KIND_NATIVE_PY, KIND_VIPER, KIND_ASM = range(4)
OBJ_TUPLE, OBJ_STR, OBJ_BYTES = 10, 5, 6
SCOPE_VIPERRELOC, SCOPE_VIPERRODATA, SCOPE_VIPERBSS = 0x20, 0x40, 0x80


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def byte(self):
        self.pos += 1
        return self.data[self.pos - 1]

    def uint(self):
        value = 0
        while True:
            c = self.byte()
            value = (value << 7) | (c & 0x7F)
            if not c & 0x80:
                return value

    def take(self, n):
        self.pos += n
        return self.data[self.pos - n : self.pos]

def encode_uint(value):
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(out))

def skip_obj(r):
    kind = r.byte()
    if kind <= 4:  # fun table, None, False, True, Ellipsis
        return
    length = r.uint()
    if kind == OBJ_TUPLE:
        for _ in range(length):
            skip_obj(r)
        return
    r.take(length)
    if kind in (OBJ_STR, OBJ_BYTES):
        r.byte()  # null terminator

def raw_code(r, out, stats): # pylint: disable=too-many-branches, too-many-locals
    """Copy one raw code (and its children) from r to out, relabelling asm."""
    start = r.pos
    kind_len = r.uint()
    kind = kind_len & 3
    has_children = kind_len & 4
    length = kind_len >> 3
    fun_data = r.take(length)
    scope_flags = 0
    if kind == KIND_ASM:
        scope_flags = r.uint()
        r.uint()  # argument count: viper gets it from the call
        r.uint()  # type signature: unused by a viper function
        out += encode_uint((length << 3) | has_children | KIND_VIPER)
        out += fun_data
        out += encode_uint(scope_flags & ~(SCOPE_VIPERRELOC | SCOPE_VIPERRODATA | SCOPE_VIPERBSS))
        stats["converted"] += 1
        head_end = None
    else:
        if kind == KIND_NATIVE_PY:
            r.uint()  # prelude offset
        elif kind == KIND_VIPER:
            scope_flags = r.uint()
            if scope_flags & SCOPE_VIPERRODATA:
                rodata = r.uint()
            else:
                rodata = 0
            if scope_flags & SCOPE_VIPERBSS:
                r.uint()
            r.take(rodata)
        head_end = r.pos
        out += r.data[start:head_end]
    if has_children:
        n = r.uint()
        out += encode_uint(n)
        for _ in range(n):
            raw_code(r, out, stats)
    if kind == KIND_VIPER and scope_flags & SCOPE_VIPERRELOC:
        reloc_start = r.pos
        while True:
            op = r.byte()
            if op == 0xFF:
                break
            if op & 1:
                r.uint()
            op >>= 1
            if op <= 5 and op & 1:
                r.uint()
        out += r.data[reloc_start : r.pos]

def convert(data):
    r = Reader(data)
    header = r.take(4)
    if header[0:1] != b"C" or header[1] != 6:
        raise ValueError("not a CircuitPython mpy v6 file")
    if (header[2] >> 2) & 0x2F == 0:
        raise ValueError("no native code in this file")
    if header[2] & 0x40:
        r.uint()  # arch flags
    n_qstr = r.uint()
    n_obj = r.uint()
    for _ in range(n_qstr):
        length = r.uint()
        if not length & 1:
            r.take((length >> 1) + 1)
    for _ in range(n_obj):
        skip_obj(r)
    out = bytearray(data[: r.pos])
    stats = {"converted": 0}
    raw_code(r, out, stats)
    if r.pos != len(data):
        raise ValueError("parsed %d of %d bytes; not touching it" % (r.pos, len(data)))
    return bytes(out), stats["converted"]

def main():
    for path in sys.argv[1:]:
        with open(path, "rb") as f:
            data = f.read()
        new, count = convert(data)
        if count:
            with open(path, "wb") as f:
                f.write(new)
        print("%s: %d asm function(s) relabelled as viper" % (path, count))

if __name__ == "__main__":
    main()
