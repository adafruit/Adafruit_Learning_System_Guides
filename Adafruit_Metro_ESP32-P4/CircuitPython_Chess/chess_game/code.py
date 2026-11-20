# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""CircuitPython Chess for the Adafruit Metro ESP32-P4.

Play against the computer, against a friend on the same screen, or against
another board over Adafruit IO. Runs on a Raspberry Pi Touch Display 2 (5") or
the Adafruit 2.8" TFT Touch Shield (resistive or capacitive).

The display is detected automatically; set CPCHESS_DISPLAY = "dsi" or "shield"
in settings.toml to force one. Online play needs Wi-Fi and Adafruit IO settings
in settings.toml, plus CPCHESS_OPPONENT (the other player's Adafruit IO username).

The chess engine is the native module _chess_engine.rv32imc.mpy. Its source,
and build script are in turbo_source_files/chess_game/.

Credits: CircuitPython Chess is a port of
[Teensy Chess](https://github.com/KrisKasprzak/TeensyChess), a touch-screen chess game for
the Teensy 4.0. Its engine, TeensyFish, is based on
[Stockfish](https://github.com/official-stockfish/Stockfish) (Copyright (C) 2004-2026 The
Stockfish developers, see `TeensyChess/src/engine/AUTHORS` inside turbo_source_files).
"""

try:
    import chess_app
except (ImportError, ValueError) as error:
    print("CircuitPython Chess could not start:", error)
    print("It needs CircuitPython 11 for the Adafruit Metro ESP32-P4, with")
    print("_chess_engine.rv32imc.mpy, the assets folders and the lib/ files")
    print("from the project bundle.")
    raise

chess_app.App().run()
