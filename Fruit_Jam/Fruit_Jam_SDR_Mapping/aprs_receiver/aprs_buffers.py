# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The DSP's buffers, and the two native modules, loaded before anything
else (code.py imports this first): then they are in internal SRAM, where
demodulating and decoding a 16 ms block takes ~9 ms; in PSRAM it takes
~18 ms at worst, which only the USB ring's 128 ms of slack hides."""
# _aprs and _ham_dsp: *.armv7emsp.mpy are the Arm builds (Fruit Jam),
# *.rv32imc.mpy the RISC-V ones (Metro ESP32-P4): `import` loads the one
# for this board.
import _aprs
import _ham_dsp  # pylint: disable=unused-import

BLOCK = 8192                 # I/Q bytes per DSP call -> 512 PCM samples (16 ms)
dsp_state = bytearray(8192)
aprs_state = bytearray(_aprs.STATE_BYTES)
iq = bytearray(BLOCK)
