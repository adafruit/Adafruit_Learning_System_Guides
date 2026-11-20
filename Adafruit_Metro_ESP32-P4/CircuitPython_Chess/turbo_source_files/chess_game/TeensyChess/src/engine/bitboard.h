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

// Teensy port: popcount/lsb/msb are written for a 32-bit core (Cortex-M7 has
// CLZ and RBIT but no 64-bit bit-scan or popcount instruction).

#ifndef BITBOARD_H_INCLUDED
#define BITBOARD_H_INCLUDED

#include <cassert>

#include "types.h"
#include "misc.h"

namespace Stockfish {

constexpr Bitboard FileABB = 0x0101010101010101ULL;
constexpr Bitboard FileBBB = FileABB << 1;
constexpr Bitboard FileCBB = FileABB << 2;
constexpr Bitboard FileDBB = FileABB << 3;
constexpr Bitboard FileEBB = FileABB << 4;
constexpr Bitboard FileFBB = FileABB << 5;
constexpr Bitboard FileGBB = FileABB << 6;
constexpr Bitboard FileHBB = FileABB << 7;

constexpr Bitboard Rank1BB = 0xFF;
constexpr Bitboard Rank2BB = Rank1BB << (8 * 1);
constexpr Bitboard Rank3BB = Rank1BB << (8 * 2);
constexpr Bitboard Rank4BB = Rank1BB << (8 * 3);
constexpr Bitboard Rank5BB = Rank1BB << (8 * 4);
constexpr Bitboard Rank6BB = Rank1BB << (8 * 5);
constexpr Bitboard Rank7BB = Rank1BB << (8 * 6);
constexpr Bitboard Rank8BB = Rank1BB << (8 * 7);

constexpr Bitboard square_bb(Square s) {
    assert(is_ok(s));
    return 1ULL << s;
}


// Overloads of bitwise operators between a Bitboard and a Square for testing
// whether a given bit is set in a bitboard, and for setting and clearing bits.

constexpr Bitboard  operator&(Bitboard b, Square s) { return b & square_bb(s); }
constexpr Bitboard  operator|(Bitboard b, Square s) { return b | square_bb(s); }
constexpr Bitboard  operator^(Bitboard b, Square s) { return b ^ square_bb(s); }
constexpr Bitboard& operator|=(Bitboard& b, Square s) { return b |= square_bb(s); }
constexpr Bitboard& operator^=(Bitboard& b, Square s) { return b ^= square_bb(s); }

constexpr Bitboard operator&(Square s, Bitboard b) { return b & s; }
constexpr Bitboard operator|(Square s, Bitboard b) { return b | s; }
constexpr Bitboard operator^(Square s, Bitboard b) { return b ^ s; }

constexpr Bitboard operator|(Square s1, Square s2) { return square_bb(s1) | s2; }

constexpr bool more_than_one(Bitboard b) { return b & (b - 1); }


// rank_bb() and file_bb() return a bitboard representing all the squares on
// the given file or rank.

constexpr Bitboard rank_bb(Rank r) { return Rank1BB << (8 * r); }

constexpr Bitboard rank_bb(Square s) { return rank_bb(rank_of(s)); }

constexpr Bitboard file_bb(File f) { return FileABB << f; }

constexpr Bitboard file_bb(Square s) { return file_bb(file_of(s)); }

// Moves a bitboard one or two steps as specified by the direction D
inline constexpr Bitboard shift(Bitboard b, Direction dir) {
    return dir == NORTH         ? b << 8
         : dir == SOUTH         ? b >> 8
         : dir == NORTH + NORTH ? b << 16
         : dir == SOUTH + SOUTH ? b >> 16
         : dir == EAST          ? (b & ~FileHBB) << 1
         : dir == WEST          ? (b & ~FileABB) >> 1
         : dir == NORTH_EAST    ? (b & ~FileHBB) << 9
         : dir == NORTH_WEST    ? (b & ~FileABB) << 7
         : dir == SOUTH_EAST    ? (b & ~FileHBB) >> 7
         : dir == SOUTH_WEST    ? (b & ~FileABB) >> 9
                                : 0;
}


// Returns the squares attacked by pawns of the given color
// from the squares in the given bitboard.
template<Color C>
constexpr Bitboard pawn_attacks_bb(Bitboard b) {
    return C == WHITE ? shift(b, NORTH_WEST) | shift(b, NORTH_EAST)
                      : shift(b, SOUTH_WEST) | shift(b, SOUTH_EAST);
}

inline constexpr Bitboard pawn_attacks_bb(Color c, Bitboard b) {
    return c == WHITE ? pawn_attacks_bb<WHITE>(b) : pawn_attacks_bb<BLACK>(b);
}

constexpr Bitboard pawn_single_push_bb(Color c, Bitboard b) {
    return shift(b, c == WHITE ? NORTH : SOUTH);
}

constexpr int edge_distance(File f) { return f < FILE_H - f ? f : FILE_H - f; }
constexpr int edge_distance(Rank r) { return r < RANK_8 - r ? r : RANK_8 - r; }

// Counts the number of non-zero bits in a 32-bit word (SWAR, no library call)
inline int popcount32(u32 x) {
    x = x - ((x >> 1) & 0x55555555u);
    x = (x & 0x33333333u) + ((x >> 2) & 0x33333333u);
    x = (x + (x >> 4)) & 0x0F0F0F0Fu;
    return int((x * 0x01010101u) >> 24);
}

// Counts the number of non-zero bits in a bitboard: the two halves are counted
// in 2-bit and 4-bit fields separately, then added (at most 8 per nibble).
inline int popcount(Bitboard b) {
    u32 lo = u32(b), hi = u32(b >> 32);
    lo     = lo - ((lo >> 1) & 0x55555555u);
    hi     = hi - ((hi >> 1) & 0x55555555u);
    lo     = (lo & 0x33333333u) + ((lo >> 2) & 0x33333333u);
    hi     = (hi & 0x33333333u) + ((hi >> 2) & 0x33333333u);
    lo += hi;
    lo = (lo & 0x0F0F0F0Fu) + ((lo >> 4) & 0x0F0F0F0Fu);
    return int((lo * 0x01010101u) >> 24);
}

#if (defined(__riscv) && !defined(__riscv_zbb)) || defined(SF_SOFT_BITSCAN)
// RISC-V cores without the Zbb extension (ESP32-P4) have no bit-scan instruction
// and GCC would call libgcc's __ctzsi2/__clzsi2: use de Bruijn multiplication.
// (SF_SOFT_BITSCAN forces this on other hosts, for testing.)
inline int ctz32(u32 x) {  // x != 0
    static constexpr u8 Index[32] = {0,  1,  28, 2,  29, 14, 24, 3,  30, 22, 20,
                                     15, 25, 17, 4,  8,  31, 27, 13, 23, 21, 19,
                                     16, 7,  26, 12, 18, 6,  11, 5,  10, 9};
    return Index[((x & (0u - x)) * 0x077CB531u) >> 27];
}
inline int msb32(u32 x) {  // index of the highest set bit, x != 0
    static constexpr u8 Index[32] = {0,  9,  1,  10, 13, 21, 2,  29, 11, 14, 16,
                                     18, 22, 25, 3,  30, 8,  12, 20, 28, 15, 17,
                                     24, 7,  19, 27, 23, 6,  26, 5,  4,  31};
    x |= x >> 1;
    x |= x >> 2;
    x |= x >> 4;
    x |= x >> 8;
    x |= x >> 16;
    return Index[(x * 0x07C4ACDDu) >> 27];
}
#else
inline int ctz32(u32 x) { return __builtin_ctz(x); }
inline int msb32(u32 x) { return 31 - __builtin_clz(x); }
#endif

// Returns the least significant bit in a non-zero bitboard.
inline Square lsb(Bitboard b) {
    assert(b);
    u32 lo = u32(b);
    return lo ? Square(ctz32(lo)) : Square(32 + ctz32(u32(b >> 32)));
}

// Returns the most significant bit in a non-zero bitboard.
inline Square msb(Bitboard b) {
    assert(b);
    u32 hi = u32(b >> 32);
    return hi ? Square(32 + msb32(hi)) : Square(msb32(u32(b)));
}

// Returns the bitboard of the least significant
// square of a non-zero bitboard. It is equivalent to square_bb(lsb(bb)).
inline Bitboard least_significant_square_bb(Bitboard b) {
    assert(b);
    return b & -b;
}

// Finds and clears the least significant bit in a non-zero bitboard.
inline Square pop_lsb(Bitboard& b) {
    assert(b);
    const Square s = lsb(b);
    b &= b - 1;
    return s;
}

}  // namespace Stockfish

#endif  // #ifndef BITBOARD_H_INCLUDED
