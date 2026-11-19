// SPDX-FileCopyrightText: 2004-2026 The Stockfish developers (see TeensyChess/src/engine/AUTHORS)
// SPDX-FileCopyrightText: 2026 Kris Kasprzak
// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: GPL-3.0-or-later

/*
  Stockfish, a UCI chess playing engine derived from Glaurung 2.1
  Copyright (C) 2004-2026 The Stockfish developers (see AUTHORS file)

  Stockfish is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  Stockfish is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

// Teensy port: current Stockfish evaluates with an NNUE network whose weights
// are far larger than the Teensy 4.0's 2 MB of flash. This is a handcrafted
// evaluation in the style of Stockfish 11, the last release with a classical
// evaluation function.

#ifndef EVALUATE_H_INCLUDED
#define EVALUATE_H_INCLUDED

#include "types.h"

namespace Stockfish {

class Position;

namespace Eval {

// One pawn in the endgame, used to convert internal values to pawns for display
constexpr Value PawnValueEg = 213;

void init();

#ifdef SF_INCREMENTAL_PSQ
// SF_INCREMENTAL_PSQ: Position keeps the sum of the piece-square values (with
// material) up to date as pieces move, instead of the evaluation adding them up
// at every call. The values are packed scores (endgame << 16) + midgame.
extern int psqValues[16][64];
#endif

// Static evaluation from the point of view of the side to move
Value evaluate(const Position& pos);

#ifdef SF_PAWN_HASH
// SF_PAWN_HASH (a power of two) enables a pawn hash table of that many entries
// (64 bytes each): the pawn structure terms and king shelter are cached per
// pawn structure, as in Stockfish 11. An entry is only used when the pawns are
// exactly the same, so the evaluation is unchanged. Off by default.
struct PawnEntry;
    #ifdef SF_ARENA_TABLES
extern PawnEntry (*pawnTable_ptr)[SF_PAWN_HASH];
    #endif
void clear_pawn_table();
#endif

}  // namespace Eval

}  // namespace Stockfish

#endif  // #ifndef EVALUATE_H_INCLUDED
