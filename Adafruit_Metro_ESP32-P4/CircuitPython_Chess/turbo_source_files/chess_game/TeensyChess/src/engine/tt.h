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

// Teensy port: single-threaded, fixed-size table in the second RAM bank.

#ifndef TT_H_INCLUDED
#define TT_H_INCLUDED

#include "misc.h"
#include "types.h"

namespace Stockfish {

struct Cluster;

// Number of 32-byte clusters (3 entries each). 6144 clusters = 192 KB.
constexpr u32 TT_CLUSTER_COUNT = 6144;

// A copy of the data already in an entry (possibly collided).
struct TTData {
    Move  move;
    Value value, eval;
    Depth depth;
    Bound bound;
    bool  is_pv;
};

// This is used to write to the TT. Writes are not "guaranteed": for chess
// reasons, we may decide the new data is less important than the old.
struct TTWriter {
   public:
    void write(Key k, Value v, bool pv, Bound b, Depth d, Move m, Value ev, u8 generation8);
    void penalize(int penalty);  // decrement stored depth by the penalty

   private:
    friend class TranspositionTable;
    Cluster* cluster;
    int      index;
    TTWriter(Cluster* cl, int idx);
};

struct TTProbe {
    bool     hit;
    TTData   data;
    TTWriter writer;
};

class TranspositionTable {

   public:
    // Zero the whole table
    void clear();
    // Must be called at the beginning of each root search to track entry aging
    void new_search();
    // The current age, used when writing new data to the TT
    u8 generation() const;
    // Approximate what fraction of entries (permille) have been written to
    // during this root search.
    int hashfull(int maxAge = 0) const;
    // Given a board position, we lookup its entry in the table, and return
    //   1) whether the entry already had data on this position
    //   2) a copy of the prior data, if any
    //   3) a writer object to the entry
    TTProbe probe(const Key key) const;
#ifdef SF_EXTERNAL_TT
    // Uses caller-owned memory for the table; returns the cluster count (0 if too small)
    u32 set_memory(void* mem, usize bytes);
#endif

   private:
    Cluster* get_cluster(const Key key) const;

    u8 generation8 = 0;
};

// There is only one global hash table for the engine
extern TranspositionTable TT;

}  // namespace Stockfish

#endif  // #ifndef TT_H_INCLUDED
