// SPDX-FileCopyrightText: 2004-2026 The Stockfish developers (see TeensyChess/src/engine/AUTHORS)
// SPDX-FileCopyrightText: 2026 Kris Kasprzak
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

// Teensy port: Stockfish's history tables need tens of megabytes (the
// continuation history alone is 8 MB). Here they are scaled to fit in a few
// tens of kilobytes:
//   - butterfly history indexed by from/to (12 bits) instead of the raw move
//   - capture history unchanged (16 KB)
//   - continuation, pawn and low-ply histories replaced by the classic killer
//     moves and counter move heuristics used by earlier Stockfish versions
//   - correction history keeps the pawn and minor-piece tables, 4096 entries each

#ifndef HISTORY_H_INCLUDED
#define HISTORY_H_INCLUDED

#include <cstdlib>
#include <type_traits>

#include "misc.h"
#include "types.h"

namespace Stockfish {

constexpr int CORRHIST_SIZE            = 4096;  // has to be a power of 2
constexpr int CORRECTION_HISTORY_LIMIT = 1024;

static_assert((CORRHIST_SIZE & (CORRHIST_SIZE - 1)) == 0, "CORRHIST_SIZE has to be a power of 2");

// StatsEntry is the container of various numerical statistics. We use a class
// instead of a naked value to directly call history update operator<<() on
// the entry. The first template parameter T is the base type of the array,
// and the second template parameter D limits the range of updates in [-D, D]
// when we update values with the << operator
template<typename T, int D>
struct StatsEntry {
    static_assert(std::is_integral_v<T> && std::is_signed_v<T>, "Not a signed integer type");

   private:
    T entry;

   public:
    void operator=(const T& v) { entry = v; }

    operator T() const { return entry; }

    void operator<<(int bonus) {
        // Make sure that bonus is in range [-D, D]
        int clampedBonus = bonus < -D ? -D : bonus > D ? D : bonus;
        T   val          = *this;
        *this            = T(val + clampedBonus - val * std::abs(clampedBonus) / D);

        assert(std::abs(T(*this)) <= D);
    }
};

// Sets every entry of a (multi-dimensional) stats table to the same value
template<typename Table>
void fill_stats(Table& table, int value) {
    using Entry = std::remove_all_extents_t<Table>;
    Entry* p    = reinterpret_cast<Entry*>(&table);
    for (usize i = 0; i < sizeof(Table) / sizeof(Entry); ++i)
        p[i] = value;
}

// ButterflyHistory records how often quiet moves have been successful or unsuccessful
// during the current search, and is used for reduction and move ordering decisions.
// It uses 2 tables (one for each color) indexed by the move's from and to squares,
// see https://www.chessprogramming.org/Butterfly_Boards
using ButterflyHistory = StatsEntry<i16, 7183>[COLOR_NB][SQUARE_NB * SQUARE_NB];

// CapturePieceToHistory is addressed by a move's [piece][to][captured piece type]
using CapturePieceToHistory = StatsEntry<i16, 10692>[PIECE_NB][SQUARE_NB][PIECE_TYPE_NB];

// CounterMoveHistory stores the quiet move that refuted the previous move,
// addressed by the previous move's [piece][to]
using CounterMoveHistory = Move[PIECE_NB][SQUARE_NB];

// Correction histories record differences between the static evaluation of
// positions and their search score. It is used to improve the static evaluation
// used by some search heuristics.
// see https://www.chessprogramming.org/Static_Evaluation_Correction_History
using CorrectionHistory = StatsEntry<i16, CORRECTION_HISTORY_LIMIT>[CORRHIST_SIZE][COLOR_NB];

using TTMoveHistory = StatsEntry<i16, 8192>;

}  // namespace Stockfish

#endif  // #ifndef HISTORY_H_INCLUDED
