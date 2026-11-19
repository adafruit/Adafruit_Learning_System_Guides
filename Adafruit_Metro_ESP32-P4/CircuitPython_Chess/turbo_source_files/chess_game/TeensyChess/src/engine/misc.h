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

// Teensy port: a trimmed misc.h with only what the engine core needs
// (no iostream, threads, NUMA or large pages).

#ifndef MISC_H_INCLUDED
#define MISC_H_INCLUDED

// Asserts are compiled out unless SF_DEBUG is defined
#ifndef SF_DEBUG
    #ifndef NDEBUG
        #define NDEBUG
    #endif
#endif

#include <cassert>
#include <cstddef>
#include <cstdint>

// Large tables are placed in the Teensy 4's second RAM bank (OCRAM, 512 KB) so the
// fast DTCM bank stays free for the search stack. DMAMEM is NOT zeroed at boot,
// so every table placed there is cleared explicitly at init.
#if defined(ARDUINO)
    #define SF_BIGMEM __attribute__((section(".dmabuffers"), used))
#else
    #define SF_BIGMEM
#endif

// SF_ARENA_TABLES: the large tables (LineBB, BetweenBB, cuckoo, the correction
// histories, the search worker, the game's state history) are not static arrays
// but pointers that the application sets before Engine::init(). Each keeps its
// name through a macro that dereferences the pointer, so indexing, sizeof and
// fill_stats() see the same array type. Used by the CircuitPython native module,
// whose static data has to fit in a small block of executable RAM.

#define sf_always_inline inline __attribute__((always_inline))

namespace Stockfish {

using u64 = std::uint64_t;
using u32 = std::uint32_t;
using u16 = std::uint16_t;
using u8  = std::uint8_t;

using i64 = std::int64_t;
using i32 = std::int32_t;
using i16 = std::int16_t;
using i8  = std::int8_t;

using usize = std::size_t;
using isize = std::ptrdiff_t;

// Milliseconds since boot
using TimePoint = i64;
TimePoint now();

}  // namespace Stockfish

// Hooks for embedding the engine (both optional, defined by the application):
//   SF_NOW_HOOK    names a function returning milliseconds, used by now()
//   SF_YIELD_HOOK  names a function called every 512 nodes; it may pause the
//                  search (switch away and back) and returns true to stop it
#ifdef SF_NOW_HOOK
extern "C" long long SF_NOW_HOOK(void);
#endif
#ifdef SF_YIELD_HOOK
extern "C" bool SF_YIELD_HOOK(void);
#endif

// SF_PROFILE: SF_PROF(id) at the top of a function counts its calls and its
// cycles, exclusive of nested SF_PROF scopes. The application defines
// sf_prof_now() (a cycle counter) and reads sf_prof_data. Off by default.
namespace Stockfish {
enum ProfId {
    PROF_EVAL,
    PROF_EVAL_PAWNS,
    PROF_EVAL_PIECES,
    PROF_EVAL_KING,
    PROF_EVAL_THREATS,
    PROF_EVAL_PASSED,
    PROF_EVAL_PSQ,
    PROF_EVAL_INIT,
    PROF_EVAL_SPACE,
    PROF_EVAL_FINAL,
    PROF_EVAL_SHELTER,
    PROF_DO_MOVE,
    PROF_UNDO_MOVE,
    PROF_EXTRA_BB,
    PROF_THREATS,
    PROF_NEXT_MOVE,
    PROF_GENERATE,
    PROF_SEE,
    PROF_LEGAL,
    PROF_GIVES_CHECK,
    PROF_TT_PROBE,
    PROF_REPETITION,
    PROF_SEARCH,
    PROF_QSEARCH,
    PROF_HISTORY,
    PROF_CORRECTION,
    PROF_MOVEPICKER_INIT,
    PROF_TT_STORE,
    PROF_NB
};
}
#ifdef SF_PROFILE
extern "C" unsigned sf_prof_now(void);
extern "C" unsigned sf_prof_instret(void);  // instructions retired (0 if unknown)
namespace Stockfish {
struct ProfScope;
}
struct SfProfData {
    unsigned long long     calls[Stockfish::PROF_NB], cycles[Stockfish::PROF_NB],
      instret[Stockfish::PROF_NB];
    Stockfish::ProfScope*  current;
};
extern SfProfData sf_prof_data;  // zero-initialized storage (no constructor)
namespace Stockfish {
struct ProfScope {
    ProfScope*               parent;
    int                      id;
    unsigned                 t0, i0, nested, nestedI;
    explicit ProfScope(int i) :
        parent(sf_prof_data.current),
        id(i),
        nested(0),
        nestedI(0) {
        sf_prof_data.current = this;
        i0                   = sf_prof_instret();
        t0                   = sf_prof_now();
    }
    ~ProfScope() {
        unsigned dt = sf_prof_now() - t0;
        unsigned di = sf_prof_instret() - i0;
        sf_prof_data.calls[id]++;
        sf_prof_data.cycles[id] += dt - nested;
        sf_prof_data.instret[id] += di - nestedI;
        if (parent)
        {
            parent->nested += dt;
            parent->nestedI += di;
        }
        sf_prof_data.current = parent;
    }
};
}
    #define SF_PROF(id) Stockfish::ProfScope sf_prof_scope_(Stockfish::id)
#else
    #define SF_PROF(id) ((void) 0)
#endif

namespace Stockfish {

template<typename T, usize MaxSize>
class ValueList {

   public:
    usize size() const { return size_; }
    void  push_back(const T& value) {
        assert(size_ < MaxSize);
        values_[size_++] = value;
    }
    const T* begin() const { return values_; }
    const T* end() const { return values_ + size_; }
    const T& operator[](int index) const { return values_[index]; }

   private:
    T     values_[MaxSize];
    usize size_ = 0;
};

// xorshift64star Pseudo-Random Number Generator
// This class is based on original code written and dedicated
// to the public domain by Sebastiano Vigna (2014).
class PRNG {

    u64 s;

    u64 rand64() {

        s ^= s >> 12, s ^= s << 25, s ^= s >> 27;
        return s * 2685821657736338717LL;
    }

   public:
    PRNG(u64 seed) :
        s(seed) {
        assert(seed);
    }

    template<typename T>
    T rand() {
        return T(rand64());
    }
};

// High 32 bits of (a * b) / 2^32 using only the top half of the key. Used to index
// the transposition table; the low key bits are kept for the in-cluster check.
inline u32 mul_hi64(u64 a, u32 b) { return u32(((a >> 32) * u64(b)) >> 32); }

}  // namespace Stockfish

#endif  // #ifndef MISC_H_INCLUDED
