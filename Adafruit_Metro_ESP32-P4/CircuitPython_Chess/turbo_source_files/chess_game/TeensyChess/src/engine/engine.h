// SPDX-FileCopyrightText: 2026 Kris Kasprzak
//
// SPDX-License-Identifier: GPL-3.0-or-later

/*
  Teensy Chess - Stockfish port for Teensy 4.0
  Copyright (C) 2026 the Teensy Chess authors

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
*/

// The interface between the user interface and the engine core

#ifndef ENGINE_H_INCLUDED
#define ENGINE_H_INCLUDED

#include "position.h"
#include "search.h"
#include "types.h"

namespace Stockfish::Engine {

// Initializes all engine tables. Call once at boot.
void init();

// Clears the hash table and the search histories
void new_game();

// Searches 'pos' (left unchanged) and returns the best move and its score
Search::Result think(Position& pos, const Search::LimitsType& limits, int skillLevel);

// Counts leaf nodes of the legal move tree, for testing the move generator
u64 perft(Position& pos, Depth depth);

// Writes a move in coordinate notation, e.g. "e2e4" or "e7e8q"
void move_to_uci(Move m, char* out);

}  // namespace Stockfish::Engine

#endif  // #ifndef ENGINE_H_INCLUDED
