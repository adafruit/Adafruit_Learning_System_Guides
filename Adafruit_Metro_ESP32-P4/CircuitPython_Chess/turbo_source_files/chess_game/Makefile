# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: GPL-3.0-or-later
# Builds _chess_engine.mpy, the chess engine as a CircuitPython native module.
#
#   make MPY_DIR=/path/to/circuitpython
#
# Needs the ESP RISC-V toolchain (riscv32-esp-elf-*) on PATH. build.py runs this
# in a temporary copy of the folder and names the output _chess_engine.rv32imc.mpy.

ifndef MPY_DIR
$(error set MPY_DIR to a CircuitPython checkout: make MPY_DIR=/path/to/circuitpython)
endif
MOD = _chess_engine
ARCH = rv32imc
# dynruntime.mk names a generic RISC-V toolchain; use the ESP one
override CROSS := riscv32-esp-elf-

# C glue (QSTRs are scanned from it), the context switch, and the C++ engine
SRC = modchess_engine.c tf_ctx_rv32.S

ifeq ($(DEBUG),1)
CFLAGS_EXTRA += -DTF_DEBUG_STEPS
CXXFLAGS_EXTRA += -DTF_DEBUG_STEPS
endif

ifeq ($(PROFILE),1)
CFLAGS_EXTRA += -DTF_PROFILE
CXXFLAGS_EXTRA += -DSF_PROFILE
endif

include $(MPY_DIR)/py/dynruntime.mk

# mpy_ld with a fix for RISC-V S-type store relocations (see mpy_ld_fixed.py)
MPY_LD = $(PYTHON) mpy_ld_fixed.py $(MPY_DIR)/tools/mpy_ld.py

# The engine object is linked last: mpy_ld computes the entry trampoline's target
# before it lays out the sections, so mpy_init's object must come first (the
# link recipe uses $^, which lists this extra prerequisite after SRC's objects).
$(BUILD)/$(MOD).mpy: $(BUILD)/tf_api.o

CXX = $(CROSS)g++
OPT ?= -O2
CXXFLAGS = -std=gnu++17 $(OPT) -DNDEBUG -fpic -fno-common -march=rv32imac -mabi=ilp32 -mno-relax \
	-fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-use-cxa-atexit \
	-fno-asynchronous-unwind-tables -fno-unwind-tables -fno-stack-protector \
	-Wall -Wno-unused-function -ITeensyChess/src/engine $(CXXFLAGS_EXTRA)

ENGINE_SRC = $(wildcard TeensyChess/src/engine/*.cpp TeensyChess/src/engine/*.h) \
	TeensyChess/game.cpp TeensyChess/game.h

# mpy_ld can't place .bss for this code: on rv32 it keeps .bss in a separate heap
# block, but GCC addresses local statics PC-relative (auipc/addi) as if they sat
# next to the code, and mpy_ld resolves those without a check. So .bss becomes a
# zero-filled data section that mpy_ld puts in the code block (executable RAM,
# which is writable on the P4). Static constructors would be dropped silently, so
# the build fails if there are any.
OBJCOPY = $(CROSS)objcopy
READELF = $(CROSS)readelf

$(BUILD)/tf_api.o: tf_api.cpp tf_api.h runtime.h $(ENGINE_SRC) Makefile $(CONFIG_H)
	$(ECHO) "CXX $<"
	$(Q)$(CXX) $(CXXFLAGS) -include runtime.h -o $(BUILD)/tf_api_raw.o -c $<
	$(Q)if $(READELF) -SW $(BUILD)/tf_api_raw.o | grep -qE '\.(init_array|ctors)'; then \
		echo "error: static constructors in tf_api.o"; exit 1; fi
	$(Q)$(OBJCOPY) --set-section-flags .bss=alloc,load,contents,data \
		--rename-section .bss=.data.rel.ro.tf_bss $(BUILD)/tf_api_raw.o $@
