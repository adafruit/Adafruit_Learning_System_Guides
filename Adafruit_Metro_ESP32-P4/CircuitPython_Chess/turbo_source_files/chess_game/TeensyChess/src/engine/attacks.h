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

// Teensy port: always uses Stockfish's hyperbola quintessence slider attacks
// (the ARM64 code path). The Cortex-M7 has a single-cycle RBIT instruction, and
// this avoids the ~840 KB of magic bitboard tables, which would not fit in RAM.

#ifndef ATTACKS_H_INCLUDED
#define ATTACKS_H_INCLUDED

#include <array>
#include <cassert>
#include <initializer_list>
#include <utility>

#include "misc.h"
#include "types.h"
#include "bitboard.h"

namespace Stockfish::Attacks {

void init();

inline u32 reverse_u32(u32 x) {
#if defined(__arm__)
    u32 r;
    asm("rbit %0, %1" : "=r"(r) : "r"(x));
    return r;
#else
    x = ((x >> 1) & 0x55555555u) | ((x & 0x55555555u) << 1);
    x = ((x >> 2) & 0x33333333u) | ((x & 0x33333333u) << 2);
    x = ((x >> 4) & 0x0F0F0F0Fu) | ((x & 0x0F0F0F0Fu) << 4);
    x = ((x >> 8) & 0x00FF00FFu) | ((x & 0x00FF00FFu) << 8);
    return (x >> 16) | (x << 16);
#endif
}

inline Bitboard reverse_bb(Bitboard bb) {
    return (Bitboard(reverse_u32(u32(bb))) << 32) | reverse_u32(u32(bb >> 32));
}

// Hyperbola quintessence implementation, thanks to the availability of an
// efficient bit reversal instruction.
// See https://www.chessprogramming.org/Hyperbola_Quintessence
struct Magic {
    // For rooks: file attacks, rank attacks. For bishops: diagonal/antidiagonal
    Bitboard mask1, mask2;

    Bitboard hyperbola(Square s, Bitboard occupied, Bitboard mask) const {
        Bitboard o   = occupied & mask;
        Bitboard fwd = o - square_bb(s);
        Bitboard rev = reverse_bb(o) - square_bb(Square(63 - int(s)));
        return (fwd ^ reverse_bb(rev)) & mask;
    }

    Bitboard attacks_bb(Square s, Bitboard occupied) const {
        return hyperbola(s, occupied, mask1) | hyperbola(s, occupied, mask2);
    }
};

extern Magic Magics[SQUARE_NB][2];

inline const Magic& magic(Square s, PieceType pt) {
    assert((pt == BISHOP || pt == ROOK) && is_ok(s));
    return Magics[s][pt - BISHOP];
}

#if defined(__riscv) || defined(SF_FOLD_SLIDERS)
    #define SF_USE_FOLD_SLIDERS 1
// RISC-V (ESP32-P4) has no bit-reverse instruction, so hyperbola quintessence
// costs ~315 cycles per slider. Instead each line (rank, file, diagonal) is
// folded into one byte of occupancy, looked up in a 512-byte first-rank table
// and spread back: 32-bit operations only, ~8x faster on the P4.
// (SF_FOLD_SLIDERS forces this on other hosts, for testing.)

// FirstRankAttacks[i][occ6]: the squares attacked from square i of a line of 8,
// as a bit mask, when the inner six squares have occupancy occ6 (bits 1..6).
    // Out of line by default: smaller code is faster with the P4's 16 KB I-cache
    #ifndef SF_FOLD_INLINE
        #define SF_FOLD_INLINE __attribute__((noinline))
    #endif
inline constexpr auto FirstRankAttacks = []() constexpr {
    std::array<std::array<u8, 64>, 8> t{};
    for (int i = 0; i < 8; ++i)
        for (int o = 0; o < 64; ++o)
        {
            int occ = o << 1, a = 0;
            for (int j = i + 1; j < 8; ++j)
            {
                a |= 1 << j;
                if (occ & (1 << j))
                    break;
            }
            for (int j = i - 1; j >= 0; --j)
            {
                a |= 1 << j;
                if (occ & (1 << j))
                    break;
            }
            t[i][o] = u8(a);
        }
    return t;
}();

// A line with at most one square per file (rank or diagonal): OR the two halves
// and the four bytes together to get its occupancy by file, look it up, and copy
// the result byte to every rank before masking with the line again.
sf_always_inline Bitboard fold_line_attacks(u32 occLo, u32 occHi, Bitboard mask, int file) {
    u32 mLo = u32(mask), mHi = u32(mask >> 32);
    u32 w   = (occLo & mLo) | (occHi & mHi);
    w |= w >> 16;
    w |= w >> 8;
    u32 a = FirstRankAttacks[file][(w >> 1) & 63] * 0x01010101u;
    return (Bitboard(a & mHi) << 32) | (a & mLo);
}

// A file: gather its eight bits into a byte by rank (the multiplications move
// bits 0, 8, 16, 24 to 24..27 without carries), look up, and spread back.
sf_always_inline Bitboard fold_file_attacks(u32 occLo, u32 occHi, int file, int rank) {
    u32 lo  = (occLo >> file) & 0x01010101u;
    u32 hi  = (occHi >> file) & 0x01010101u;
    u32 occ = ((lo * 0x01020408u) >> 24) | ((hi * 0x01020408u) >> 20);
    u32 a   = FirstRankAttacks[rank][(occ >> 1) & 63];
    u32 aLo = ((a & 15) * 0x00204081u) & 0x01010101u;
    u32 aHi = ((a >> 4) * 0x00204081u) & 0x01010101u;
    return (Bitboard(aHi << file) << 32) | (aLo << file);
}

SF_FOLD_INLINE Bitboard fold_bishop_attacks(Square s, Bitboard occupied) {
    const Magic& m = Magics[s][0];
    u32          lo = u32(occupied), hi = u32(occupied >> 32);
    return fold_line_attacks(lo, hi, m.mask1, int(s) & 7) | fold_line_attacks(lo, hi, m.mask2, int(s) & 7);
}

SF_FOLD_INLINE Bitboard fold_rook_attacks(Square s, Bitboard occupied) {
    u32 lo = u32(occupied), hi = u32(occupied >> 32);
    return fold_file_attacks(lo, hi, int(s) & 7, int(s) >> 3)
         | fold_line_attacks(lo, hi, Magics[s][1].mask2, int(s) & 7);
}
#endif

#ifdef SF_ARENA_TABLES
extern Bitboard (*LineBB_ptr)[SQUARE_NB][SQUARE_NB];
extern Bitboard (*BetweenBB_ptr)[SQUARE_NB][SQUARE_NB];
    #define LineBB (*LineBB_ptr)
    #define BetweenBB (*BetweenBB_ptr)
#else
extern Bitboard LineBB[SQUARE_NB][SQUARE_NB];
extern Bitboard BetweenBB[SQUARE_NB][SQUARE_NB];
#endif
extern Bitboard DiagBB[SQUARE_NB];
extern Bitboard AntiDiagBB[SQUARE_NB];

// horizontal/vertical/diagonal line passing through s1 and s2
inline Bitboard line_bb(Square s1, Square s2) {
    assert(is_ok(s1) && is_ok(s2));
    return LineBB[s1][s2];
}

// horizontal/vertical/diagonal line segment from s1 to s2,
// excluding s1 but including s2
inline Bitboard between_bb(Square s1, Square s2) {
    assert(is_ok(s1) && is_ok(s2));
    return BetweenBB[s1][s2];
}

inline Bitboard diag_bb(Square s) {
    assert(is_ok(s));
    return DiagBB[s];
}

inline Bitboard antidiag_bb(Square s) {
    assert(is_ok(s));
    return AntiDiagBB[s];
}

// Returns the bitboard of target square for the given step
// from the given square. If the step is off the board, returns empty bitboard.
constexpr Bitboard safe_destination(Square s, int step) {
    constexpr auto abs = [](int v) { return v < 0 ? -v : v; };
    Square         to  = Square(s + step);
    return is_ok(to) && abs(file_of(s) - file_of(to)) <= 2 ? square_bb(to) : Bitboard(0);
}

constexpr Bitboard sliding_attack(PieceType pt, Square sq, Bitboard occupied) {
    Bitboard            attacks             = 0;
    constexpr Direction RookDirections[4]   = {NORTH, SOUTH, EAST, WEST};
    constexpr Direction BishopDirections[4] = {NORTH_EAST, SOUTH_EAST, SOUTH_WEST, NORTH_WEST};

    for (Direction d : (pt == ROOK ? RookDirections : BishopDirections))
        for (Square s = sq; Bitboard dest = safe_destination(s, d); s += d)
        {
            attacks |= dest;
            if (occupied & dest)
                break;
        }

    return attacks;
}

constexpr Bitboard knight_attack(Square sq) {
    Bitboard b = {};
    for (int step : {-17, -15, -10, -6, 6, 10, 15, 17})
        b |= safe_destination(sq, step);
    return b;
}

constexpr Bitboard king_attack(Square sq) {
    Bitboard b = {};
    for (int step : {-9, -8, -7, -1, 1, 7, 8, 9})
        b |= safe_destination(sq, step);
    return b;
}

constexpr Bitboard pseudo_attacks(PieceType pt, Square sq) {
    switch (pt)
    {
    case PieceType::ROOK :
    case PieceType::BISHOP :
        return sliding_attack(pt, sq, 0);
    case PieceType::QUEEN :
        return sliding_attack(PieceType::ROOK, sq, 0) | sliding_attack(PieceType::BISHOP, sq, 0);
    case PieceType::KNIGHT :
        return knight_attack(sq);
    case PieceType::KING :
        return king_attack(sq);
    default :
        return 0;
    }
}

inline constexpr auto PseudoAttacks = []() constexpr {
    std::array<std::array<Bitboard, SQUARE_NB>, PIECE_TYPE_NB> attacks{};

    for (Square s1 = SQ_A1; s1 <= SQ_H8; ++s1)
    {
        attacks[WHITE][s1] = pawn_attacks_bb<WHITE>(square_bb(s1));
        attacks[BLACK][s1] = pawn_attacks_bb<BLACK>(square_bb(s1));

        attacks[KING][s1]   = pseudo_attacks(KING, s1);
        attacks[KNIGHT][s1] = pseudo_attacks(KNIGHT, s1);
        attacks[QUEEN][s1] = attacks[BISHOP][s1] = pseudo_attacks(BISHOP, s1);
        attacks[QUEEN][s1] |= attacks[ROOK][s1]  = pseudo_attacks(ROOK, s1);
    }

    return attacks;
}();

// Returns the pseudo attacks of the given piece type
// assuming an empty board.
sf_always_inline Bitboard attacks_bb(PieceType pt, Square s, Color c = COLOR_NB) {

    assert((pt != PAWN || c < COLOR_NB) && is_ok(s));
    return pt == PAWN ? PseudoAttacks[c][s] : PseudoAttacks[pt][s];
}

// Returns the attacks by the given piece
// assuming the board is occupied according to the passed Bitboard.
// Sliding piece attacks do not continue past an occupied square.
sf_always_inline Bitboard attacks_bb(PieceType pt, Square s, Bitboard occupied) {

    assert(pt != PAWN && is_ok(s));

    switch (pt)
    {
#ifdef SF_USE_FOLD_SLIDERS
    case BISHOP :
        return fold_bishop_attacks(s, occupied);
    case ROOK :
        return fold_rook_attacks(s, occupied);
    case QUEEN :
        return fold_bishop_attacks(s, occupied) | fold_rook_attacks(s, occupied);
#else
    case BISHOP :
    case ROOK :
        return magic(s, pt).attacks_bb(s, occupied);
    case QUEEN :
        return magic(s, BISHOP).attacks_bb(s, occupied) | magic(s, ROOK).attacks_bb(s, occupied);
#endif
    default :
        return PseudoAttacks[pt][s];
    }
}

inline std::pair<Bitboard, Bitboard> both_attacks_bb(Square s, Bitboard occupied) {
    return {attacks_bb(BISHOP, s, occupied), attacks_bb(ROOK, s, occupied)};
}

inline Bitboard attacks_bb(Piece pc, Square s, Bitboard occupied) {
    return type_of(pc) == PAWN ? PseudoAttacks[color_of(pc)][s]
                               : attacks_bb(type_of(pc), s, occupied);
}

}  // namespace Stockfish::Attacks

#endif  // #ifndef ATTACKS_H_INCLUDED
