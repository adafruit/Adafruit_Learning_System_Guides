# CircuitPython Chess: the engine module's source

This folder is the source of `_chess_engine.rv32imc.mpy` in `../../chess_game/`, the
chess engine that CircuitPython Chess plays against on the Metro ESP32-P4. Everything else
the game runs is a Python file in `chess_game/` or an indexed BMP / LVGL font in its
`assets/` (5" display) and `assets_s/` (2.8" shield) folders.

**Credits:** CircuitPython Chess is a port of
[Teensy Chess](https://github.com/KrisKasprzak/TeensyChess), a touch-screen chess game for[CircuitPython_Chess](..%2F..%2F..%2F..%2F..%2F..%2F..%2Fpi_mount%2Fcircuitpython_workspace%2FAdafruit_Learning_System_Guides%2FAdafruit_Metro_ESP32-P4%2FCircuitPython_Chess)
the Teensy 4.0. Its engine, TeensyFish, is based on
[Stockfish](https://github.com/official-stockfish/Stockfish) (Copyright (C) 2004-2026 The
Stockfish developers, see `TeensyChess/src/engine/AUTHORS`). The engine and the game rules in
`TeensyChess/` are Teensy Chess's sources with the changes needed to build them for the
Metro ESP32-P4. CircuitPython Chess is not made or endorsed by the Teensy Chess or Stockfish
authors. Like them, it is free software under the GNU General Public License v3 or later.

```
build.py                  builds _chess_engine.rv32imc.mpy (runs the Makefile)
Makefile                  builds _chess_engine.mpy, the native module
tf_api.cpp/.h             C API; one translation unit that #includes the engine and game.cpp
modchess_engine.c         CircuitPython bindings (module _chess_engine)
tf_ctx_rv32.S             stack switch, so the search runs in slices on its own stack
runtime.h                 small libc/libgcc helpers (no libc in native modules)
mpy_ld_fixed.py           CircuitPython's tools/mpy_ld.py with a RISC-V store relocation fix
TeensyChess/src/engine/   TeensyFish: the Stockfish port (search, movegen, SF11 eval)
TeensyChess/game.cpp/.h   game rules: history, legal targets, SAN, results
```

## Building

You need:

- A CircuitPython checkout at the same `.mpy` version as the firmware. The shipped module
  was built against CircuitPython 11.x sources (`.mpy` format 6.3, arch rv32imc) and loads on
  11.0.0-alpha.3 and later 11.x.
- `pyelftools` for the checkout's `tools/mpy_ld.py` (`pip install pyelftools`).
- Espressif's RISC-V GCC (`riscv32-esp-elf`, e.g. esp-15.2.0_20251204 from ESP-IDF's tool
  installer).

```
python3 build.py --circuitpython /path/to/circuitpython \
    --toolchain ~/.espressif/tools/riscv32-esp-elf/esp-15.2.0_20251204/riscv32-esp-elf/bin
```

This writes `_chess_engine.rv32imc.mpy`. Copy it next to `code.py`, and
`import _chess_engine` loads it on a board whose `microcontroller.cpu.architecture` is
`rv32imc`. Building from this folder gives a module byte-identical to the one in
`chess_game/`.

Notes:

- `mpy_ld_fixed.py` wraps the CircuitPython tree's `mpy_ld.py` and patches one relocation
  (S-type stores: `R_RISCV_PCREL_LO12_S` / `R_RISCV_LO12_S` must keep the instruction's
  register, funct3 and opcode bits, mask `0x01FFF07F`). Without it the module hard-faults.
- The Makefile links `tf_api.o` last (the entry trampoline needs `mpy_init`'s object first in
  the code section), moves `.bss` into the code block (PC-relative `.bss` references aren't
  relocated correctly on rv32) and fails if a static constructor (`.init_array`) appears,
  since the loader drops them.
- `tf_api.cpp` defines `SF_NOW_HOOK`, `SF_YIELD_HOOK`, `SF_EXTERNAL_TT`,
  `SF_NO_STATIC_CONSTRUCTORS`, `SF_ARENA_TABLES`, `SF_INCREMENTAL_PSQ` and `SF_PAWN_HASH`
  before it includes the engine; without these macros the same engine sources build the
  Teensy sketch. On RISC-V the engine also uses its folded slider attacks and software bit
  scans (`bitboard.h`, `attacks.h`).
- `make DEBUG=1` adds step tracing (`TF_DEBUG_STEPS`) and `make PROFILE=1` adds search
  profiling counters (`TF_PROFILE` / `SF_PROFILE`).
