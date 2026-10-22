# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Desktop stand-in for CircuitPython's micropython module.

Viper functions run as plain Python (pass memoryviews cast to the pointer
width); asm_thumb functions can't run here and raise if called.
"""

import builtins

for _name in ("ptr", "ptr8", "ptr16", "ptr32", "uint"):
    setattr(builtins, _name, object)


def const(value):
    return value


def viper(function):
    return function


native = viper


def asm_thumb(function):
    def unavailable(*args):
        raise RuntimeError("%s is asm_thumb: it only runs on the board" % function.__name__)

    return unavailable
