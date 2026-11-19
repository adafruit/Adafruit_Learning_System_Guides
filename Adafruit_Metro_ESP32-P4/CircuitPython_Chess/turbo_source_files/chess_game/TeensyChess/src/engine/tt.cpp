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

#include "tt.h"

#include <cstdlib>
#include <cstring>

#include "bitboard.h"
#include "misc.h"

namespace Stockfish {


// TTEntry struct is the 8 bytes transposition table entry, defined as:
//
// depth       8 bit
// pv node     1 bit
// bound type  2 bit
// generation  5 bit
// move       16 bit
// value      16 bit
// evaluation 16 bit
//
// The 21 bit key of each entry is stored in the cluster header.
//
// We use `bool(depth8)` as the cheap internal occupancy check, corresponding
// to `depth == DEPTH_NONE` externally, so we offset the internal depth by DEPTH_NONE.
//
// Pv, bound and generation are packed in a single byte.

static constexpr u8 GENERATION_BITS = 5;
static constexpr u8 GENERATION_MASK = (1 << GENERATION_BITS) - 1;
static constexpr u8 BOUND_SHIFT     = GENERATION_BITS;
static constexpr u8 BOUND_MASK      = 0b11 << BOUND_SHIFT;
static constexpr u8 PV_SHIFT        = BOUND_SHIFT + 2;
static constexpr u8 PV_MASK         = 1 << PV_SHIFT;

struct TTEntry {

    // Extract data from the TT entry. We have to convert TT internal bitfields
    // to external types.
    TTData read() const {
        return TTData{Move(move16),
                      Value(value16),
                      Value(eval16),
                      Depth(DEPTH_NONE + depth8),
                      Bound((genBound8 & BOUND_MASK) >> BOUND_SHIFT),
                      bool(genBound8 & PV_MASK)};
    }

    // Check if the TT entry is occupied
    bool is_occupied() const { return bool(depth8); }

    // Return TT entry age
    u8 relative_age(const u8 curr_generation) const {
        return (curr_generation - genBound8) & GENERATION_MASK;
    }

    u8  depth8;
    u8  genBound8;
    u16 move16;
    i16 value16;
    i16 eval16;
};

// A TranspositionTable is an array of Cluster, of size TT_CLUSTER_COUNT. Each
// cluster consists of ClusterSize number of TTEntry. Each non-empty TTEntry
// contains information on exactly one position.

static constexpr int ClusterSize = 3;
static constexpr int KeyBits     = 21;

struct Cluster {
    // keys contains the low 21 bits of the Zobrist keys of the 3 TT entries in this cluster,
    // packed together into 63 bits of an u64
    u64     keys;
    TTEntry entry[ClusterSize];
};

static_assert(sizeof(Cluster) == 32, "Suboptimal Cluster size");

#ifdef SF_EXTERNAL_TT
// The application hands over the memory with TranspositionTable::set_memory()
static Cluster* table;
static u32      clusterCount;
#else
alignas(32) static Cluster table[TT_CLUSTER_COUNT] SF_BIGMEM;
static constexpr u32 clusterCount = TT_CLUSTER_COUNT;
#endif

TranspositionTable TT;

// Populates the TTEntry and its key with a new node's data, possibly overwriting
// an old position. We convert external types to internal bitfields.
constexpr u64 MASK21 = (1ULL << KeyBits) - 1;
void          TTWriter::write(
  Key k, Value v, bool pv, Bound b, Depth d, Move m, Value ev, u8 curr_generation) {
    SF_PROF(PROF_TT_STORE);

    u64        keys  = cluster->keys;
    const auto key21 = keys >> KeyBits * index & MASK21;
    auto&      entry = cluster->entry[index];

    // Preserve the old ttmove if we don't have a new one
    if (m || (k & MASK21) != key21)
        entry.move16 = m.raw();

    // Overwrite less valuable entries (cheapest checks first)
    if (b == BOUND_EXACT || (k & MASK21) != key21 || d - DEPTH_NONE + 2 * pv > entry.depth8 - 4
        || entry.relative_age(curr_generation))
    {
        assert(d > DEPTH_NONE);
        assert(d - DEPTH_NONE < 256);
        assert(curr_generation <= GENERATION_MASK);  // TT::new_search() plays nice

        keys &= ~(MASK21 << (KeyBits * index));
        keys |= (k & MASK21) << (KeyBits * index);
        cluster->keys   = keys;
        entry.depth8    = u8(d - DEPTH_NONE);
        entry.genBound8 = u8(curr_generation | b << BOUND_SHIFT | u8(pv) << PV_SHIFT);
        entry.value16   = i16(v);
        entry.eval16    = i16(ev);
    }

    // Secondary aging. Important for elementary mate finding.
    else if (entry.depth8 + DEPTH_NONE >= 5
             && Bound((entry.genBound8 & BOUND_MASK) >> BOUND_SHIFT) != BOUND_EXACT)
    {
        Value v16 = entry.value16;

        if (std::abs(v16) < VALUE_INFINITE && is_decisive(v16))
            entry.depth8 = u8(entry.depth8 > 0 ? entry.depth8 - 1 : 0);
    }
}


// TTWriter is but a very thin wrapper around the pointer
TTWriter::TTWriter(Cluster* cl, int idx) :
    cluster(cl),
    index(idx) {}

// Flag a TTEntry as useless (decrementing the stored depth by the given penalty)
void TTWriter::penalize(int penalty) {
    auto& entry  = cluster->entry[index];
    int   depth  = int(entry.depth8) - penalty;
    entry.depth8 = u8(depth > 0 ? depth : 0);
}


#ifdef SF_EXTERNAL_TT
// Uses 'bytes' of memory at 'mem' for the table (rounded down to whole 32-byte
// clusters). Returns the number of clusters; at least 1024 are needed.
u32 TranspositionTable::set_memory(void* mem, usize bytes) {
    usize addr = (usize(mem) + 31) & ~usize(31);
    bytes -= addr - usize(mem);
    table        = reinterpret_cast<Cluster*>(addr);
    clusterCount = u32(bytes / sizeof(Cluster));
    if (clusterCount < 1024)
        table = nullptr, clusterCount = 0;
    clear();
    return clusterCount;
}
#endif

// Initializes the entire transposition table to zero
void TranspositionTable::clear() {
    generation8 = 0;
#ifdef SF_EXTERNAL_TT
    if (!table)
        return;
#endif
    std::memset(static_cast<void*>(table), 0, usize(clusterCount) * sizeof(Cluster));
}


// Returns an approximation of the hashtable occupation during a search.
// The hash is x permill full, as per UCI protocol. Only counts entries
// which are younger than maxAge.
int TranspositionTable::hashfull(int maxAge) const {
    int cnt = 0;
    for (int i = 0; i < 1000; ++i)
        for (int j = 0; j < ClusterSize; ++j)
            cnt += table[i].entry[j].is_occupied()
                && table[i].entry[j].relative_age(generation8) <= maxAge;

    return cnt / ClusterSize;
}


// Must be called at the beginning of each root search to track entry aging
void TranspositionTable::new_search() {
    ++generation8;
    // Don't overflow into the other bits of TTEntry::genBound8
    generation8 &= GENERATION_MASK;
}


// The current age, used when writing new data to the TT
u8 TranspositionTable::generation() const { return generation8; }


// Looks up the current position in the transposition table. Calling probe(key)
// returns true if the key is found (which may be a collision) and has non-null
// data. Otherwise, it returns false and a pointer to an empty or least valuable
// TTEntry to be replaced later. The value of an entry is its depth minus 8 times
// its relative age.
TTProbe TranspositionTable::probe(const Key key) const {

    SF_PROF(PROF_TT_PROBE);
    Cluster* const cluster = get_cluster(key);
    auto&          tte     = cluster->entry;
    const u64      key21   = key & MASK21;  // Use the low 21 bits as key inside the cluster

    constexpr u64 KeyLsb  = 1ULL | (1ULL << KeyBits) | (1ULL << 2 * KeyBits);
    constexpr u64 KeyMsb  = KeyLsb << 20;
    u64           keys    = cluster->keys;
    const u64     keyXors = (keys ^ (KeyLsb * key21));
    // this bit twiddling trick will produce a one in the first (=least significant) bit of
    // the first 21bit block matching key21. The bits before that first matching block will
    // be all zeros, but after the first matching block there could be garbage.
    const u64 matches = (keyXors - KeyLsb) & ~keyXors & KeyMsb;

    if (matches)
    {
        const int i = int(lsb(matches)) / KeyBits;
        return {tte[i].is_occupied(), tte[i].read(), TTWriter(cluster, i)};
    }

    // Find an entry to be replaced according to the replacement strategy
    int replace = 0;
    for (int i = 1; i < ClusterSize; ++i)
        if (tte[replace].depth8 - 8 * tte[replace].relative_age(generation8)
            > tte[i].depth8 - 8 * tte[i].relative_age(generation8))
            replace = i;

    return {false, TTData{Move::none(), VALUE_NONE, VALUE_NONE, DEPTH_NONE, BOUND_NONE, false},
            TTWriter(cluster, replace)};
}


// The hash function
Cluster* TranspositionTable::get_cluster(const Key key) const {
    return &table[mul_hi64(key, clusterCount)];
}

}  // namespace Stockfish
