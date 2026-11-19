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

// Handcrafted evaluation modeled on the classical evaluation of Stockfish 11
// (material, piece-square tables, mobility, pawn structure, passed pawns, king
// safety, threats, space, initiative and endgame scaling), plus the KXK and
// KBNK endgame rules. It is computed from scratch at every node: there is no
// pawn or material hash table, which keeps the RAM footprint small.

#include "evaluate.h"

#include <cstdlib>

#include "attacks.h"
#include "bitboard.h"
#include "position.h"

namespace Stockfish {

using namespace Attacks;

namespace {

// Score packs a midgame and an endgame value into a single integer, the
// endgame value in the upper 16 bits and the midgame value in the lower ones.
enum Score : int {
    SCORE_ZERO
};

constexpr Score make_score(int mg, int eg) { return Score(int(unsigned(eg) << 16) + mg); }

// Extracting the signed lower and upper 16 bits is not so trivial because
// according to the standard a simple cast to short is implementation defined
// and so is a right shift of a signed integer.
inline Value eg_value(Score s) { return Value(i16(u16(unsigned(s + 0x8000) >> 16))); }
inline Value mg_value(Score s) { return Value(i16(u16(unsigned(s)))); }

constexpr Score operator+(Score d1, Score d2) { return Score(int(d1) + int(d2)); }
constexpr Score operator-(Score d1, Score d2) { return Score(int(d1) - int(d2)); }
constexpr Score operator-(Score d) { return Score(-int(d)); }
inline Score&   operator+=(Score& d1, Score d2) { return d1 = d1 + d2; }
inline Score&   operator-=(Score& d1, Score d2) { return d1 = d1 - d2; }
inline Score    operator*(Score s, int i) { return Score(int(s) * i); }
inline Score    operator/(Score s, int i) { return make_score(mg_value(s) / i, eg_value(s) / i); }

#define S(mg, eg) make_score(mg, eg)

constexpr int PHASE_MIDGAME       = 128;
constexpr int SCALE_FACTOR_DRAW   = 0;
constexpr int SCALE_FACTOR_NORMAL = 64;
constexpr int SCALE_FACTOR_ONEPAWN = 48;

constexpr Value MidgameLimit   = 15258;
constexpr Value EndgameLimit   = 3915;
constexpr Value SpaceThreshold = 12222;
constexpr Value Tempo          = 28;

// Midgame and endgame piece values (Stockfish 11)
constexpr Value PieceValueMg[PIECE_TYPE_NB] = {0, 128, 781, 825, 1276, 2538, 0, 0};
constexpr Value PieceValueEg[PIECE_TYPE_NB] = {0, 213, 854, 915, 1380, 2682, 0, 0};

// clang-format off

// Piece-square bonuses. Pieces are symmetric around the d/e files, so only
// the queen side half of the board is given; pawns have a full table.
constexpr Score Bonus[KING + 1][RANK_NB][4] = {
  { },
  { },
  { // Knight
   { S(-175, -96), S(-92,-65), S(-74,-49), S(-73,-21) },
   { S( -77, -67), S(-41,-54), S(-27,-18), S(-15,  8) },
   { S( -61, -40), S(-17,-27), S(  6, -8), S( 12, 29) },
   { S( -35, -35), S(  8, -2), S( 40, 13), S( 49, 28) },
   { S( -34, -45), S( 13,-16), S( 44,  9), S( 51, 39) },
   { S(  -9, -51), S( 22,-44), S( 58,-16), S( 53, 17) },
   { S( -67, -69), S(-27,-50), S(  4,-51), S( 37, 12) },
   { S(-201,-100), S(-83,-88), S(-56,-56), S(-26,-17) }
  },
  { // Bishop
   { S(-53,-57), S( -5,-30), S( -8,-37), S(-23,-12) },
   { S(-15,-37), S(  8,-13), S( 19,-17), S(  4,  1) },
   { S( -7,-16), S( 21, -1), S( -5, -2), S( 17, 10) },
   { S( -5,-20), S( 11, -6), S( 25,  0), S( 39, 17) },
   { S(-12,-17), S( 29, -1), S( 22,-14), S( 31, 15) },
   { S(-16,-30), S(  6,  6), S(  1,  4), S( 11,  6) },
   { S(-17,-31), S(-14,-20), S(  5, -1), S(  0,  1) },
   { S(-48,-46), S(  1,-42), S(-14,-37), S(-23,-24) }
  },
  { // Rook
   { S(-31, -9), S(-20,-13), S(-14,-10), S(-5, -9) },
   { S(-21,-12), S(-13, -9), S( -8, -1), S( 6, -2) },
   { S(-25,  6), S(-11, -8), S( -1, -2), S( 3, -6) },
   { S(-13, -6), S( -5,  1), S( -4, -9), S(-6,  7) },
   { S(-27, -5), S(-15,  8), S( -4,  7), S( 3, -6) },
   { S(-22,  6), S( -2,  1), S(  6, -7), S(12, 10) },
   { S( -2,  4), S( 12,  5), S( 16, 20), S(18, -5) },
   { S(-17, 18), S(-19,  0), S( -1, 19), S( 9, 13) }
  },
  { // Queen
   { S( 3,-69), S(-5,-57), S(-5,-47), S( 4,-26) },
   { S(-3,-55), S( 5,-31), S( 8,-22), S(12, -4) },
   { S(-3,-39), S( 6,-18), S(13, -9), S( 7,  3) },
   { S( 4,-23), S( 5, -3), S( 9, 13), S( 8, 24) },
   { S( 0,-29), S(14, -6), S(12,  9), S( 5, 21) },
   { S(-4,-38), S(10,-18), S( 6,-12), S( 8,  1) },
   { S(-5,-50), S( 6,-27), S(10,-24), S( 8, -8) },
   { S(-2,-75), S(-2,-52), S( 1,-43), S(-2,-36) }
  },
  { // King
   { S(271,  1), S(327, 45), S(271, 85), S(198, 76) },
   { S(278, 53), S(303,100), S(234,133), S(179,135) },
   { S(195, 88), S(258,130), S(169,169), S(120,175) },
   { S(164,103), S(190,156), S(138,172), S( 98,172) },
   { S(154, 96), S(179,166), S(105,199), S( 70,199) },
   { S(123, 92), S(145,172), S( 81,184), S( 31,191) },
   { S( 88, 47), S(120,121), S( 65,116), S( 33,131) },
   { S( 59, 11), S( 89, 59), S( 45, 73), S( -1, 78) }
  }
};

constexpr Score PBonus[RANK_NB][FILE_NB] = {
  { },
  { S(  3,-10), S(  3, -6), S( 10, 10), S( 19,  0), S( 16, 14), S( 19,  7), S(  7, -5), S( -5,-19) },
  { S( -9,-10), S(-15,-10), S( 11,-10), S( 15,  4), S( 32,  4), S( 22,  3), S(  5, -6), S(-22, -4) },
  { S( -8,  6), S(-23, -2), S(  6, -8), S( 20, -4), S( 40,-13), S( 17,-12), S(  4,-10), S(-12, -9) },
  { S( 13,  9), S(  0,  4), S(-13,  3), S(  1,-12), S( 11,-12), S( -2, -6), S(-13, 13), S(  5,  8) },
  { S( -5, 28), S(-12, 20), S( -7, 21), S( 22, 28), S( -8, 30), S( -5,  7), S(-15,  6), S(-18, 13) },
  { S( -7,  0), S(  7,-11), S( -3, 12), S(-13, 21), S(  5, 25), S(-16, 19), S( 10,  4), S( -8,  7) }
};

// MobilityBonus[PieceType-2][attacked] contains bonuses for middle and end game,
// indexed by piece type and number of attacked squares in the mobility area.
constexpr Score MobilityBonus[4][28] = {
  { S(-62,-81), S(-53,-56), S(-12,-30), S( -4,-14), S(  3,  8), S( 13, 15), // Knight
    S( 22, 23), S( 28, 27), S( 33, 33) },
  { S(-48,-59), S(-20,-23), S( 16, -3), S( 26, 13), S( 38, 24), S( 51, 42), // Bishop
    S( 55, 54), S( 63, 57), S( 63, 65), S( 68, 73), S( 81, 78), S( 81, 86),
    S( 91, 88), S( 98, 97) },
  { S(-58,-76), S(-27,-18), S(-15, 28), S(-10, 55), S( -5, 69), S( -2, 82), // Rook
    S(  9,112), S( 16,118), S( 30,132), S( 29,142), S( 32,155), S( 38,165),
    S( 46,166), S( 48,169), S( 58,171) },
  { S(-39,-36), S(-21,-15), S(  3,  8), S(  3, 18), S( 14, 34), S( 22, 54), // Queen
    S( 28, 61), S( 41, 73), S( 43, 79), S( 48, 92), S( 56, 94), S( 60,104),
    S( 60,113), S( 66,120), S( 67,123), S( 70,126), S( 71,133), S( 73,136),
    S( 79,140), S( 88,143), S( 88,148), S( 99,166), S(102,170), S(102,175),
    S(106,184), S(109,191), S(113,206), S(116,212) }
};

// Pawn shelter strength of our pawns on the king's file and the adjacent files,
// indexed by the distance of the file to the edge and the rank of the pawn.
constexpr Value ShelterStrength[4][RANK_NB] = {
  {  -6,  81,  93,  58,  39,  18,   25 },
  { -43,  61,  35, -49, -29, -11,  -63 },
  { -10,  75,  23,  -2,  32,   3,  -45 },
  { -39, -13, -29, -52, -48, -67, -166 }
};

// Danger of enemy pawns moving toward our king, indexed by the distance of the
// file to the edge and the rank of the enemy pawn. Rank 0 means no enemy pawn.
constexpr Value UnblockedStorm[4][RANK_NB] = {
  {  89, -285, -185, 93, 57,  45,  51 },
  {  44,  -18,  123, 46, 39,  -7,  23 },
  {   4,   52,  162, 37,  7, -14,  -2 },
  { -10,  -14,   90, 15,  2,  -7, -16 }
};

// Pawn structure, passed pawns and threats
constexpr int   Connected[RANK_NB] = { 0, 7, 8, 12, 29, 48, 86 };
constexpr Score PassedRank[RANK_NB] = {
  S(0, 0), S(10, 28), S(17, 33), S(15, 41), S(62, 72), S(168, 177), S(276, 260)
};
constexpr Score ThreatByMinor[PIECE_TYPE_NB] = {
  S(0, 0), S(6, 32), S(59, 41), S(79, 56), S(90, 119), S(79, 161)
};
constexpr Score ThreatByRook[PIECE_TYPE_NB] = {
  S(0, 0), S(3, 44), S(38, 71), S(38, 61), S(0, 38), S(51, 38)
};
constexpr Score RookOnFile[] = { S(21, 4), S(47, 25) };

// King attack weights by piece type
constexpr int KingAttackWeights[PIECE_TYPE_NB] = { 0, 0, 81, 52, 44, 10 };

// Bonuses for safe checks
constexpr int QueenSafeCheck  = 772;
constexpr int RookSafeCheck   = 1084;
constexpr int BishopSafeCheck = 645;
constexpr int KnightSafeCheck = 792;

constexpr Score Backward           = S(  9, 24);
constexpr Score BishopPair         = S( 46, 74);
constexpr Score BishopPawns        = S(  3,  7);
constexpr Score BlockedStorm       = S( 82, 82);
constexpr Score Doubled            = S( 11, 56);
constexpr Score FlankAttacks       = S(  8,  0);
constexpr Score Hanging            = S( 69, 36);
constexpr Score Isolated           = S(  5, 15);
constexpr Score KingProtector      = S(  7,  8);
constexpr Score KnightOnQueen      = S( 16, 12);
constexpr Score LongDiagonalBishop = S( 45,  0);
constexpr Score MinorBehindPawn    = S( 18,  3);
constexpr Score Outpost            = S( 30, 21);
constexpr Score PassedFile         = S( 11,  8);
constexpr Score PawnlessFlank      = S( 17, 95);
constexpr Score RestrictedPiece    = S(  7,  7);
constexpr Score SliderOnQueen      = S( 59, 18);
constexpr Score ThreatByKing       = S( 24, 89);
constexpr Score ThreatByPawnPush   = S( 48, 39);
constexpr Score ThreatBySafePawn   = S(173, 94);
constexpr Score TrappedRook        = S( 52, 10);
constexpr Score WeakLever          = S(  0, 56);
constexpr Score WeakUnopposed      = S( 13, 27);

// clang-format on

#undef S

constexpr Bitboard AllSquares  = ~Bitboard(0);
constexpr Bitboard DarkSquares = 0xAA55AA55AA55AA55ULL;
constexpr Bitboard QueenSide   = FileABB | FileBBB | FileCBB | FileDBB;
constexpr Bitboard CenterFiles = FileCBB | FileDBB | FileEBB | FileFBB;
constexpr Bitboard KingSide    = FileEBB | FileFBB | FileGBB | FileHBB;
constexpr Bitboard Center      = (FileDBB | FileEBB) & (Rank4BB | Rank5BB);

constexpr Bitboard KingFlank[FILE_NB] = {QueenSide ^ FileDBB, QueenSide,   QueenSide,
                                         CenterFiles,         CenterFiles, KingSide,
                                         KingSide,            KingSide ^ FileEBB};

// Piece-square table with the piece values included, filled by Eval::init()
#ifdef SF_INCREMENTAL_PSQ
}  // namespace
int Eval::psqValues[16][64];
namespace {
int (&psq)[PIECE_NB][SQUARE_NB] = Eval::psqValues;
#else
Score psq[PIECE_NB][SQUARE_NB];
#endif

}  // namespace

#ifdef SF_PAWN_HASH
static_assert((SF_PAWN_HASH & (SF_PAWN_HASH - 1)) == 0, "SF_PAWN_HASH must be a power of two");

// The pawn terms of a pawn structure, and the king shelter of each side for one
// king square and castling rights. An entry matches only the same pawns (the
// bitboards are compared, not just the key), so there are no false hits.
struct Eval::PawnEntry {
    Bitboard pawns[COLOR_NB];
    Bitboard passedPawns[COLOR_NB];
    Bitboard pawnAttacksSpan[COLOR_NB];
    int      score;                // Score: white's pawn terms minus black's
    int      kingSafety[COLOR_NB]; // Score, valid for kingSquare/castling
    u8       kingSquare[COLOR_NB]; // SQ_NONE when not computed
    u8       castling[COLOR_NB];
};
static_assert(sizeof(Eval::PawnEntry) == 64, "pawn entry size");

    #ifdef SF_ARENA_TABLES
Eval::PawnEntry (*Eval::pawnTable_ptr)[SF_PAWN_HASH];
        #define pawnTable (*Eval::pawnTable_ptr)
    #else
static Eval::PawnEntry pawnTable[SF_PAWN_HASH] SF_BIGMEM;
    #endif

void Eval::clear_pawn_table() {
    for (auto& e : pawnTable)
    {
        // No position has a pawn on every square, so a cleared entry never matches
        e.pawns[WHITE] = e.pawns[BLACK] = ~Bitboard(0);
        e.kingSquare[WHITE] = e.kingSquare[BLACK] = u8(SQ_NONE);
    }
}
#endif

namespace {


// Bitboard helpers used only by the evaluation

inline int distance(Square s1, Square s2) {
    int fd = std::abs(int(file_of(s1)) - int(file_of(s2)));
    int rd = std::abs(int(rank_of(s1)) - int(rank_of(s2)));
    return fd > rd ? fd : rd;
}

inline int file_distance(Square s1, Square s2) {
    return std::abs(int(file_of(s1)) - int(file_of(s2)));
}

inline int rank_distance(Square s1, Square s2) {
    return std::abs(int(rank_of(s1)) - int(rank_of(s2)));
}

// Ranks strictly in front of the square, from the point of view of color c
inline Bitboard forward_ranks_bb(Color c, Square s) {
    return c == WHITE ? ~Rank1BB << 8 * relative_rank(WHITE, s)
                      : ~Rank8BB >> 8 * relative_rank(BLACK, s);
}

inline Bitboard forward_file_bb(Color c, Square s) { return forward_ranks_bb(c, s) & file_bb(s); }

inline Bitboard adjacent_files_bb(Square s) {
    return shift(file_bb(s), EAST) | shift(file_bb(s), WEST);
}

inline Bitboard pawn_attack_span(Color c, Square s) {
    return forward_ranks_bb(c, s) & adjacent_files_bb(s);
}

inline Bitboard passed_pawn_span(Color c, Square s) {
    return pawn_attack_span(c, s) | forward_file_bb(c, s);
}

template<Color C>
constexpr Bitboard pawn_double_attacks_bb(Bitboard b) {
    return C == WHITE ? shift(b, NORTH_WEST) & shift(b, NORTH_EAST)
                      : shift(b, SOUTH_WEST) & shift(b, SOUTH_EAST);
}

// The most advanced square of b from the point of view of color c
inline Square frontmost_sq(Color c, Bitboard b) { return c == WHITE ? msb(b) : lsb(b); }

inline int push_to_edge(Square s) {
    int rd = edge_distance(rank_of(s)), fd = edge_distance(file_of(s));
    return 90 - (7 * fd * fd / 2 + 7 * rd * rd / 2);
}

inline int push_to_corner(Square s) { return std::abs(7 - int(rank_of(s)) - int(file_of(s))); }

inline int push_close(Square s1, Square s2) { return 140 - 20 * distance(s1, s2); }

inline bool opposite_colors(Square s1, Square s2) {
    return ((int(s1) + int(rank_of(s1)) + int(s2) + int(rank_of(s2))) & 1) != 0;
}


// Mate with KX vs K. This function is used to evaluate positions with
// king and plenty of material vs a lone king. It simply gives the
// attacking side a bonus for driving the defending king towards the edge
// of the board, and for keeping the distance between the two kings small.
Value endgame_KXK(const Position& pos, Color strongSide) {

    Color  weakSide   = ~strongSide;
    Square strongKing = pos.square<KING>(strongSide);
    Square weakKing   = pos.square<KING>(weakSide);

    Value result = pos.non_pawn_material(strongSide) + pos.count<PAWN>(strongSide) * PieceValueEg[PAWN]
                 + push_to_edge(weakKing) + push_close(strongKing, weakKing);

    if (pos.count<QUEEN>(strongSide) || pos.count<ROOK>(strongSide)
        || (pos.count<BISHOP>(strongSide) && pos.count<KNIGHT>(strongSide))
        || ((pos.pieces(strongSide, BISHOP) & ~DarkSquares)
            && (pos.pieces(strongSide, BISHOP) & DarkSquares)))
        result = result + VALUE_KNOWN_WIN < VALUE_TB_WIN_IN_MAX_PLY - 1 ? result + VALUE_KNOWN_WIN
                                                                        : VALUE_TB_WIN_IN_MAX_PLY - 1;

    return strongSide == pos.side_to_move() ? result : -result;
}

// Mate with KBN vs K. This is similar to KX vs K, but we have to drive the
// defending king towards a corner square that our bishop attacks.
Value endgame_KBNK(const Position& pos, Color strongSide) {

    Color  weakSide   = ~strongSide;
    Square strongKing = pos.square<KING>(strongSide);
    Square weakKing   = pos.square<KING>(weakSide);
    Square bishopSq   = lsb(pos.pieces(strongSide, BISHOP));

    // If our bishop does not attack A1/H8, we flip the enemy king square
    // to drive to opposite corners (A8/H1).
    Value result = VALUE_KNOWN_WIN + 3520 + push_close(strongKing, weakKing)
                 + 420 * push_to_corner(opposite_colors(bishopSq, SQ_A1) ? flip_file(weakKing) : weakKing);

    return strongSide == pos.side_to_move() ? result : -result;
}


// Evaluation class computes and stores attacks tables and other working data
class Evaluation {

   public:
    Evaluation()                             = delete;
    explicit Evaluation(const Position& p) :
        pos(p) {}
    Evaluation& operator=(const Evaluation&) = delete;
    Value       value();

   private:
    template<Color Us>
    void initialize();
    template<Color Us>
    Score pawns();
    template<Color Us, PieceType Pt>
    Score pieces();
    template<Color Us>
    Score king() const;
    template<Color Us>
    Score shelter(Square ksq) const;
    template<Color Us>
    Score king_safety() const;
    template<Color Us>
    Score threats() const;
    template<Color Us>
    Score passed() const;
    template<Color Us>
    Score space() const;
    Score initiative(Score score) const;
    int   scale_factor(Value eg) const;

    const Position& pos;
#ifdef SF_PAWN_HASH
    Eval::PawnEntry* pe;
#endif
    Bitboard        mobilityArea[COLOR_NB];
    Score           mobility[COLOR_NB] = {SCORE_ZERO, SCORE_ZERO};

    // attackedBy[color][piece type] is a bitboard representing all squares
    // attacked by a given color and piece type. Special "piece types" which
    // is also calculated is ALL_PIECES.
    Bitboard attackedBy[COLOR_NB][PIECE_TYPE_NB];

    // attackedBy2[color] are the squares attacked by at least 2 units of a given
    // color, including x-rays. But diagonal x-rays through pawns are not computed.
    Bitboard attackedBy2[COLOR_NB];

    // kingRing[color] are the squares adjacent to the king plus some other
    // very near squares, depending on king position.
    Bitboard kingRing[COLOR_NB];

    // kingAttackersCount[color] is the number of pieces of the given color
    // which attack a square in the kingRing of the enemy king.
    int kingAttackersCount[COLOR_NB];

    // kingAttackersWeight[color] is the sum of the "weights" of the pieces of
    // the given color which attack a square in the kingRing of the enemy king.
    int kingAttackersWeight[COLOR_NB];

    // kingAttacksCount[color] is the number of attacks by the given color to
    // squares directly adjacent to the enemy king.
    int kingAttacksCount[COLOR_NB];

    Bitboard passedPawns[COLOR_NB];
    Bitboard pawnAttacks[COLOR_NB];
    Bitboard pawnAttacksSpan[COLOR_NB];
};


// Pawn structure: computes the pawn attacks and passed pawns of the given color
// and returns the pawn structure score.
template<Color Us>
Score Evaluation::pawns() {

    SF_PROF(PROF_EVAL_PAWNS);
    constexpr Color     Them = ~Us;
    constexpr Direction Up   = pawn_push(Us);

    Bitboard neighbours, stoppers, support, phalanx, opposed;
    Bitboard lever, leverPush;
    bool     backward, passed, doubled;
    Score    score = SCORE_ZERO;

    Bitboard b         = pos.pieces(Us, PAWN);
    Bitboard ourPawns  = pos.pieces(Us, PAWN);
    Bitboard theirPawns = pos.pieces(Them, PAWN);

    passedPawns[Us] = pawnAttacksSpan[Us] = 0;
    pawnAttacks[Us]                        = pawn_attacks_bb<Us>(ourPawns);

    while (b)
    {
        Square s = pop_lsb(b);
        Rank   r = relative_rank(Us, s);

        // Flag the pawn
        opposed    = theirPawns & forward_file_bb(Us, s);
        stoppers   = theirPawns & passed_pawn_span(Us, s);
        lever      = theirPawns & attacks_bb(PAWN, s, Us);
        leverPush  = theirPawns & attacks_bb(PAWN, s + Up, Us);
        doubled    = ourPawns & (s - Up);
        neighbours = ourPawns & adjacent_files_bb(s);
        phalanx    = neighbours & rank_bb(s);
        support    = neighbours & rank_bb(s - Up);

        pawnAttacksSpan[Us] |= pawn_attack_span(Us, s);

        // A pawn is backward when it is behind all pawns of the same color on
        // the adjacent files and cannot safely advance.
        backward =
          !(neighbours & forward_ranks_bb(Them, s + Up)) && (leverPush | (theirPawns & (s + Up)));

        // A pawn is passed if no enemy pawn can stop it
        passed = !stoppers;

        if (passed)
            passedPawns[Us] |= s;

        // Score this pawn
        if (support | phalanx)
        {
            int v = Connected[r] * (2 + bool(phalanx) - bool(opposed)) + 21 * popcount(support);

            score += make_score(v, v * (r - 2) / 4);
        }

        else if (!neighbours)
            score -= Isolated + WeakUnopposed * !opposed;

        else if (backward)
            score -= Backward + WeakUnopposed * !opposed;

        if (!support)
            score -= Doubled * doubled + WeakLever * more_than_one(lever);
    }

    return score;
}


// Computes king and pawn attacks, and the king ring bitboard for a given color.
// This is done at the beginning of the evaluation.
template<Color Us>
void Evaluation::initialize() {

    SF_PROF(PROF_EVAL_INIT);
    constexpr Color     Them     = ~Us;
    constexpr Direction Down     = -pawn_push(Us);
    constexpr Bitboard  LowRanks = (Us == WHITE ? Rank2BB | Rank3BB : Rank7BB | Rank6BB);

    const Square ksq = pos.square<KING>(Us);

    Bitboard dblAttackByPawn = pawn_double_attacks_bb<Us>(pos.pieces(Us, PAWN));

    // Find our pawns that are blocked or on the first two ranks
    Bitboard b = pos.pieces(Us, PAWN) & (shift(pos.pieces(), Down) | LowRanks);

    // Squares occupied by those pawns, by our king or queen, by blockers to attacks on our king
    // or controlled by enemy pawns are excluded from the mobility area.
    mobilityArea[Us] =
      ~(b | pos.pieces(Us, KING, QUEEN) | pos.blockers_for_king(Us) | pawnAttacks[Them]);

    // Initialize attackedBy[] for king and pawns
    attackedBy[Us][KING]       = attacks_bb(KING, ksq);
    attackedBy[Us][PAWN]       = pawnAttacks[Us];
    attackedBy[Us][KNIGHT]     = attackedBy[Us][BISHOP] = 0;
    attackedBy[Us][ROOK]       = attackedBy[Us][QUEEN]  = 0;
    attackedBy[Us][ALL_PIECES] = attackedBy[Us][KING] | attackedBy[Us][PAWN];
    attackedBy2[Us]            = dblAttackByPawn | (attackedBy[Us][KING] & attackedBy[Us][PAWN]);

    // Init our king safety tables
    File   kf = file_of(ksq) < FILE_B ? FILE_B : file_of(ksq) > FILE_G ? FILE_G : file_of(ksq);
    Rank   kr = rank_of(ksq) < RANK_2 ? RANK_2 : rank_of(ksq) > RANK_7 ? RANK_7 : rank_of(ksq);
    Square s  = make_square(kf, kr);
    kingRing[Us] = attacks_bb(KING, s) | s;

    kingAttackersCount[Them] = popcount(kingRing[Us] & pawnAttacks[Them]);
    kingAttacksCount[Them] = kingAttackersWeight[Them] = 0;

    // Remove from kingRing[] the squares defended by two pawns
    kingRing[Us] &= ~dblAttackByPawn;
}


// Evaluates bonuses and penalties of the pieces of a given color and type
template<Color Us, PieceType Pt>
Score Evaluation::pieces() {

    SF_PROF(PROF_EVAL_PIECES);
    constexpr Color     Them = ~Us;
    constexpr Direction Down = -pawn_push(Us);
    constexpr Bitboard  OutpostRanks =
      (Us == WHITE ? Rank4BB | Rank5BB | Rank6BB : Rank5BB | Rank4BB | Rank3BB);

    Bitboard b1    = pos.pieces(Us, Pt);
    Bitboard b, bb;
    Score    score = SCORE_ZERO;

    while (b1)
    {
        Square s = pop_lsb(b1);

        // Find attacked squares, including x-ray attacks for bishops and rooks
        b = Pt == BISHOP ? attacks_bb(BISHOP, s, pos.pieces() ^ pos.pieces(QUEEN))
          : Pt == ROOK   ? attacks_bb(ROOK, s, pos.pieces() ^ pos.pieces(QUEEN) ^ pos.pieces(Us, ROOK))
                         : attacks_bb(Pt, s, pos.pieces());

        if (pos.blockers_for_king(Us) & s)
            b &= line_bb(pos.square<KING>(Us), s);

        attackedBy2[Us] |= attackedBy[Us][ALL_PIECES] & b;
        attackedBy[Us][Pt] |= b;
        attackedBy[Us][ALL_PIECES] |= b;

        if (b & kingRing[Them])
        {
            kingAttackersCount[Us]++;
            kingAttackersWeight[Us] += KingAttackWeights[Pt];
            kingAttacksCount[Us] += popcount(b & attackedBy[Them][KING]);
        }

        int mob = popcount(b & mobilityArea[Us]);

        mobility[Us] += MobilityBonus[Pt - 2][mob];

        if (Pt == BISHOP || Pt == KNIGHT)
        {
            // Bonus if piece is on an outpost square or can reach one
            bb = OutpostRanks & attackedBy[Us][PAWN] & ~pawnAttacksSpan[Them];
            if (bb & s)
                score += Outpost * (Pt == KNIGHT ? 2 : 1);

            else if (Pt == KNIGHT && (bb & b & ~pos.pieces(Us)))
                score += Outpost;

            // Bonus for a knight or bishop shielded by pawn
            if (shift(pos.pieces(PAWN), Down) & s)
                score += MinorBehindPawn;

            // Penalty if the piece is far from the king
            score -= KingProtector * distance(pos.square<KING>(Us), s);

            if (Pt == BISHOP)
            {
                // Penalty according to number of pawns on the same color square as the
                // bishop, bigger when the center files are blocked with pawns and smaller
                // when the bishop is outside the pawn chain.
                Bitboard blocked = pos.pieces(Us, PAWN) & shift(pos.pieces(), Down);
                int      sameColorPawns =
                  popcount(pos.pieces(Us, PAWN) & ((DarkSquares & s) ? DarkSquares : ~DarkSquares));

                score -= BishopPawns * sameColorPawns
                       * (!(attackedBy[Us][PAWN] & s) + popcount(blocked & CenterFiles));

                // Bonus for bishop on a long diagonal which can "see" both center squares
                // (the empty-board test first skips the slider lookup on most squares)
                if (more_than_one(attacks_bb(BISHOP, s) & Center)
                    && more_than_one(attacks_bb(BISHOP, s, pos.pieces(PAWN)) & Center))
                    score += LongDiagonalBishop;
            }
        }

        if (Pt == ROOK)
        {
            // Bonus for rook on an open or semi-open file
            if (!(pos.pieces(Us, PAWN) & file_bb(s)))
                score += RookOnFile[!(pos.pieces(Them, PAWN) & file_bb(s))];

            // Penalty when trapped by the king, even more if the king cannot castle
            else if (mob <= 3)
            {
                File kf = file_of(pos.square<KING>(Us));
                if ((kf < FILE_E) == (file_of(s) < kf))
                    score -= TrappedRook * (1 + !pos.can_castle(Us & ANY_CASTLING));
            }
        }
    }

    return score;
}


// Pawn shelter and storm in front of a king placed on ksq
template<Color Us>
Score Evaluation::shelter(Square ksq) const {

    constexpr Color Them = ~Us;

    Bitboard b          = pos.pieces(PAWN) & ~forward_ranks_bb(Them, ksq);
    Bitboard ourPawns   = b & pos.pieces(Us);
    Bitboard theirPawns = b & pos.pieces(Them);

    Score bonus = make_score(5, 5);

    File center = file_of(ksq) < FILE_B ? FILE_B : file_of(ksq) > FILE_G ? FILE_G : file_of(ksq);
    for (File f = File(center - 1); f <= File(center + 1); ++f)
    {
        b             = ourPawns & file_bb(f);
        int ourRank   = b ? relative_rank(Us, frontmost_sq(Them, b)) : 0;

        b             = theirPawns & file_bb(f);
        int theirRank = b ? relative_rank(Us, frontmost_sq(Them, b)) : 0;

        int d = edge_distance(f);
        bonus += make_score(ShelterStrength[d][ourRank], 0);

        if (ourRank && (ourRank == theirRank - 1))
            bonus -= BlockedStorm * int(theirRank == RANK_3);
        else
            bonus -= make_score(UnblockedStorm[d][theirRank], 0);
    }

    return bonus;
}


// King shelter, taking castling into account, and the distance to our closest pawn
template<Color Us>
Score Evaluation::king_safety() const {
    SF_PROF(PROF_EVAL_SHELTER);

    Square ksq = pos.square<KING>(Us);

    Score best = shelter<Us>(ksq);

    // If we can castle use the bonus after castling if it is bigger
    if (pos.can_castle(Us & KING_SIDE))
    {
        Score s = shelter<Us>(relative_square(Us, SQ_G1));
        if (mg_value(s) > mg_value(best))
            best = s;
    }

    if (pos.can_castle(Us & QUEEN_SIDE))
    {
        Score s = shelter<Us>(relative_square(Us, SQ_C1));
        if (mg_value(s) > mg_value(best))
            best = s;
    }

    // In endgame we like to bring our king near our closest pawn
    Bitboard pawns       = pos.pieces(Us, PAWN);
    int      minPawnDist = 6;

    if (pawns & attacks_bb(KING, ksq))
        minPawnDist = 1;
    else
        while (pawns)
        {
            int d = distance(ksq, pop_lsb(pawns));
            if (d < minPawnDist)
                minPawnDist = d;
        }

    return best - make_score(0, 16 * minPawnDist);
}


// Evaluates bonuses and penalties of the king of a given color
template<Color Us>
Score Evaluation::king() const {

    SF_PROF(PROF_EVAL_KING);
    constexpr Color    Them = ~Us;
    constexpr Bitboard Camp =
      (Us == WHITE ? AllSquares ^ Rank6BB ^ Rank7BB ^ Rank8BB : AllSquares ^ Rank1BB ^ Rank2BB ^ Rank3BB);

    Bitboard weak, b1, b2, b3, safe, unsafeChecks = 0;
    Bitboard rookChecks, queenChecks, bishopChecks, knightChecks;
    int      kingDanger = 0;
    const Square ksq    = pos.square<KING>(Us);

    // Init the score with king shelter and enemy pawns storm
#ifdef SF_PAWN_HASH
    const u8 castling = u8(pos.can_castle(Us & KING_SIDE)) | u8(pos.can_castle(Us & QUEEN_SIDE)) << 1;
    if (pe->kingSquare[Us] != u8(ksq) || pe->castling[Us] != castling)
    {
        pe->kingSafety[Us] = int(king_safety<Us>());
        pe->kingSquare[Us] = u8(ksq);
        pe->castling[Us]   = castling;
    }
    Score score = Score(pe->kingSafety[Us]);
#else
    Score score = king_safety<Us>();
#endif

    // Attacked squares defended at most once by our queen or king
    weak = attackedBy[Them][ALL_PIECES] & ~attackedBy2[Us]
         & (~attackedBy[Us][ALL_PIECES] | attackedBy[Us][KING] | attackedBy[Us][QUEEN]);

    // Analyse the safe enemy's checks which are possible on next move
    safe = ~pos.pieces(Them);
    safe &= ~attackedBy[Us][ALL_PIECES] | (weak & attackedBy2[Them]);

    b1 = attacks_bb(ROOK, ksq, pos.pieces() ^ pos.pieces(Us, QUEEN));
    b2 = attacks_bb(BISHOP, ksq, pos.pieces() ^ pos.pieces(Us, QUEEN));

    // Enemy rooks checks
    rookChecks = b1 & safe & attackedBy[Them][ROOK];
    if (rookChecks)
        kingDanger += RookSafeCheck;
    else
        unsafeChecks |= b1 & attackedBy[Them][ROOK];

    // Enemy queen safe checks: we count them only if they are from squares from
    // which we can't give a rook check, because rook checks are more valuable.
    queenChecks =
      (b1 | b2) & attackedBy[Them][QUEEN] & safe & ~attackedBy[Us][QUEEN] & ~rookChecks;
    if (queenChecks)
        kingDanger += QueenSafeCheck;

    // Enemy bishops checks: we count them only if they are from squares from
    // which we can't give a queen check, because queen checks are more valuable.
    bishopChecks = b2 & attackedBy[Them][BISHOP] & safe & ~queenChecks;
    if (bishopChecks)
        kingDanger += BishopSafeCheck;
    else
        unsafeChecks |= b2 & attackedBy[Them][BISHOP];

    // Enemy knights checks
    knightChecks = attacks_bb(KNIGHT, ksq) & attackedBy[Them][KNIGHT];
    if (knightChecks & safe)
        kingDanger += KnightSafeCheck;
    else
        unsafeChecks |= knightChecks;

    // Find the squares that opponent attacks in our king flank, the squares
    // which they attack twice in that flank, and the squares that we defend.
    b1 = attackedBy[Them][ALL_PIECES] & KingFlank[file_of(ksq)] & Camp;
    b2 = b1 & attackedBy2[Them];
    b3 = attackedBy[Us][ALL_PIECES] & KingFlank[file_of(ksq)] & Camp;

    int kingFlankAttack  = popcount(b1) + popcount(b2);
    int kingFlankDefense = popcount(b3);

    kingDanger += kingAttackersCount[Them] * kingAttackersWeight[Them]
                + 185 * popcount(kingRing[Us] & weak) + 148 * popcount(unsafeChecks)
                + 98 * popcount(pos.blockers_for_king(Us)) + 69 * kingAttacksCount[Them]
                + 3 * kingFlankAttack * kingFlankAttack / 8 + mg_value(mobility[Them] - mobility[Us])
                - 873 * !pos.count<QUEEN>(Them)
                - 100 * bool(attackedBy[Us][KNIGHT] & attackedBy[Us][KING])
                - 6 * mg_value(score) / 8 - 4 * kingFlankDefense + 37;

    // Transform the kingDanger units into a Score, and subtract it from the evaluation
    if (kingDanger > 100)
        score -= make_score(kingDanger * kingDanger / 4096, kingDanger / 16);

    // Penalty when our king is on a pawnless flank
    if (!(pos.pieces(PAWN) & KingFlank[file_of(ksq)]))
        score -= PawnlessFlank;

    // Penalty if king flank is under attack, potentially moving toward the king
    score -= FlankAttacks * kingFlankAttack;

    return score;
}


// Evaluates the threats to the pieces of the enemy color
template<Color Us>
Score Evaluation::threats() const {

    SF_PROF(PROF_EVAL_THREATS);
    constexpr Color     Them     = ~Us;
    constexpr Direction Up       = pawn_push(Us);
    constexpr Bitboard  TRank3BB = (Us == WHITE ? Rank3BB : Rank6BB);

    Bitboard b, weak, defended, nonPawnEnemies, stronglyProtected, safe;
    Score    score = SCORE_ZERO;

    // Non-pawn enemies
    nonPawnEnemies = pos.pieces(Them) & ~pos.pieces(PAWN);

    // Squares strongly protected by the enemy, either because they defend the
    // square with a pawn, or because they defend the square twice and we don't.
    stronglyProtected = attackedBy[Them][PAWN] | (attackedBy2[Them] & ~attackedBy2[Us]);

    // Non-pawn enemies, strongly protected
    defended = nonPawnEnemies & stronglyProtected;

    // Enemies not strongly protected and under our attack
    weak = pos.pieces(Them) & ~stronglyProtected & attackedBy[Us][ALL_PIECES];

    // Bonus according to the kind of attacking pieces
    if (defended | weak)
    {
        b = (defended | weak) & (attackedBy[Us][KNIGHT] | attackedBy[Us][BISHOP]);
        while (b)
            score += ThreatByMinor[type_of(pos.piece_on(pop_lsb(b)))];

        b = weak & attackedBy[Us][ROOK];
        while (b)
            score += ThreatByRook[type_of(pos.piece_on(pop_lsb(b)))];

        if (weak & attackedBy[Us][KING])
            score += ThreatByKing;

        b = ~attackedBy[Them][ALL_PIECES] | (nonPawnEnemies & attackedBy2[Us]);
        score += Hanging * popcount(weak & b);
    }

    // Bonus for restricting their piece moves
    b = attackedBy[Them][ALL_PIECES] & ~stronglyProtected & attackedBy[Us][ALL_PIECES];
    score += RestrictedPiece * popcount(b);

    // Protected or unattacked squares
    safe = ~attackedBy[Them][ALL_PIECES] | attackedBy[Us][ALL_PIECES];

    // Bonus for attacking enemy pieces with our relatively safe pawns
    b = pos.pieces(Us, PAWN) & safe;
    b = pawn_attacks_bb<Us>(b) & nonPawnEnemies;
    score += ThreatBySafePawn * popcount(b);

    // Find squares where our pawns can push on the next move
    b = shift(pos.pieces(Us, PAWN), Up) & ~pos.pieces();
    b |= shift(b & TRank3BB, Up) & ~pos.pieces();

    // Keep only the squares which are relatively safe
    b &= ~attackedBy[Them][PAWN] & safe;

    // Bonus for safe pawn threats on the next move
    b = pawn_attacks_bb<Us>(b) & nonPawnEnemies;
    score += ThreatByPawnPush * popcount(b);

    // Bonus for threats on the next moves against enemy queen
    if (pos.count<QUEEN>(Them) == 1)
    {
        Square s = pos.square<QUEEN>(Them);
        safe     = mobilityArea[Us] & ~stronglyProtected;

        b = attackedBy[Us][KNIGHT] & attacks_bb(KNIGHT, s);

        score += KnightOnQueen * popcount(b & safe);

        b = (attackedBy[Us][BISHOP] & attacks_bb(BISHOP, s, pos.pieces()))
          | (attackedBy[Us][ROOK] & attacks_bb(ROOK, s, pos.pieces()));

        score += SliderOnQueen * popcount(b & safe & attackedBy2[Us]);
    }

    return score;
}


// Evaluates the passed pawns and candidate passed pawns of the given color
template<Color Us>
Score Evaluation::passed() const {

    SF_PROF(PROF_EVAL_PASSED);
    constexpr Color     Them = ~Us;
    constexpr Direction Up   = pawn_push(Us);

    auto king_proximity = [&](Color c, Square s) {
        int d = distance(pos.square<KING>(c), s);
        return d < 5 ? d : 5;
    };

    Bitboard b, bb, squaresToQueen, unsafeSquares;
    Score    score = SCORE_ZERO;

    b = passedPawns[Us];

    while (b)
    {
        Square s = pop_lsb(b);

        int   r     = relative_rank(Us, s);
        Score bonus = PassedRank[r];

        if (r > RANK_3)
        {
            int    w       = 5 * r - 13;
            Square blockSq = s + Up;

            // Adjust bonus based on the king's proximity
            bonus += make_score(0, ((king_proximity(Them, blockSq) * 19) / 4
                                    - king_proximity(Us, blockSq) * 2)
                                     * w);

            // If blockSq is not the queening square then consider also a second push
            if (r != RANK_7)
                bonus -= make_score(0, king_proximity(Us, blockSq + Up) * w);

            // If the pawn is free to advance, then increase the bonus
            if (pos.empty(blockSq))
            {
                squaresToQueen = forward_file_bb(Us, s);
                unsafeSquares  = passed_pawn_span(Us, s);

                bb = forward_file_bb(Them, s) & pos.pieces(ROOK, QUEEN);

                if (!(pos.pieces(Them) & bb))
                    unsafeSquares &= attackedBy[Them][ALL_PIECES];

                // If there are no enemy attacks on passed pawn span, assign a big bonus.
                // Otherwise assign a smaller bonus if the path to queen is not attacked
                // and even smaller bonus if it is attacked but block square is not.
                int k = !unsafeSquares                    ? 35
                      : !(unsafeSquares & squaresToQueen) ? 20
                      : !(unsafeSquares & blockSq)        ? 9
                                                          : 0;

                // Assign a larger bonus if the block square is defended
                if ((pos.pieces(Us) & bb) || (attackedBy[Us][ALL_PIECES] & blockSq))
                    k += 5;

                bonus += make_score(k * w, k * w);
            }
        }

        // Scale down bonus for passers with a pawn of ours in front of them
        if (pos.pieces(PAWN) & (s + Up))
            bonus = bonus / 2;

        score += bonus - PassedFile * edge_distance(file_of(s));
    }

    return score;
}


// Evaluates the space of a given side. The aim is to improve play on game
// opening. It is based on the number of safe squares on the 4 central files
// on ranks 2 to 4. Completely safe squares behind a friendly pawn are counted
// twice. Finally, the space bonus is multiplied by a weight which decreases
// according to occupancy.
template<Color Us>
Score Evaluation::space() const {

    SF_PROF(PROF_EVAL_SPACE);
    if (pos.non_pawn_material() < SpaceThreshold)
        return SCORE_ZERO;

    constexpr Color     Them      = ~Us;
    constexpr Direction Down      = -pawn_push(Us);
    constexpr Bitboard  SpaceMask = Us == WHITE ? CenterFiles & (Rank2BB | Rank3BB | Rank4BB)
                                                : CenterFiles & (Rank7BB | Rank6BB | Rank5BB);

    // Find the available squares for our pieces inside the area defined by SpaceMask
    Bitboard safe = SpaceMask & ~pos.pieces(Us, PAWN) & ~attackedBy[Them][PAWN];

    // Find all squares which are at most three squares behind some friendly pawn
    Bitboard behind = pos.pieces(Us, PAWN);
    behind |= shift(behind, Down);
    behind |= shift(behind, Down + Down);

    int bonus  = popcount(safe) + popcount(behind & safe & ~attackedBy[Them][ALL_PIECES]);
    int weight = pos.count<ALL_PIECES>(Us) - 1;

    return make_score(bonus * weight * weight / 16, 0);
}


// Computes the initiative correction value for the position. It is a second
// order bonus/malus based on the known attacking/defending status of the players.
Score Evaluation::initiative(Score score) const {

    SF_PROF(PROF_EVAL_FINAL);
    Value mg = mg_value(score);
    Value eg = eg_value(score);

    Square wksq = pos.square<KING>(WHITE);
    Square bksq = pos.square<KING>(BLACK);

    int outflanking = file_distance(wksq, bksq) - rank_distance(wksq, bksq);

    bool pawnsOnBothFlanks = (pos.pieces(PAWN) & QueenSide) && (pos.pieces(PAWN) & KingSide);

    int passedCount = popcount(passedPawns[WHITE] | passedPawns[BLACK]);

    bool almostUnwinnable = !passedCount && outflanking < 0 && !pawnsOnBothFlanks;

    // Compute the initiative bonus for the attacking side
    int complexity = 9 * passedCount + 11 * pos.count<PAWN>() + 9 * outflanking
                   + 21 * pawnsOnBothFlanks + 51 * !pos.non_pawn_material()
                   - 43 * almostUnwinnable - 100;

    // Now apply the bonus: note that we find the attacking side by extracting
    // the sign of the midgame or endgame values, and that we carefully cap the
    // bonus so that the midgame and endgame scores do not change sign after
    // the bonus.
    int cu = complexity + 50 < 0 ? complexity + 50 : 0;  // min(complexity + 50, 0)
    if (cu < -std::abs(mg))
        cu = -std::abs(mg);

    int cv = complexity;
    if (cv < -std::abs(eg))
        cv = -std::abs(eg);

    int u = ((mg > 0) - (mg < 0)) * cu;
    int v = ((eg > 0) - (eg < 0)) * cv;

    return make_score(u, v);
}


// Computes the scale factor for the winning side
int Evaluation::scale_factor(Value eg) const {

    SF_PROF(PROF_EVAL_FINAL);
    Color strongSide = eg > VALUE_DRAW ? WHITE : BLACK;
    Color weakSide   = ~strongSide;

    Value npmStrong = pos.non_pawn_material(strongSide);
    Value npmWeak   = pos.non_pawn_material(weakSide);

    int sf = SCALE_FACTOR_NORMAL;

    // No pawns: the side with the extra material usually needs at least a rook
    // more to win. One pawn: winning chances are reduced.
    if (!pos.count<PAWN>(strongSide) && npmStrong - npmWeak <= BishopValue)
        sf = npmStrong < RookValue ? SCALE_FACTOR_DRAW : npmWeak <= BishopValue ? 4 : 14;

    else if (pos.count<PAWN>(strongSide) == 1 && npmStrong - npmWeak <= BishopValue)
        sf = SCALE_FACTOR_ONEPAWN;

    if (sf == SCALE_FACTOR_NORMAL || sf == SCALE_FACTOR_ONEPAWN)
    {
        if (pos.opposite_bishops() && pos.non_pawn_material() == 2 * BishopValue)
            sf = 22;
        else
        {
            int cap = 36 + (pos.opposite_bishops() ? 2 : 7) * pos.count<PAWN>(strongSide);
            if (cap < sf)
                sf = cap;
        }
    }

    return sf;
}


// Main function of the class. It computes the various parts of the evaluation
// and returns the value of the position from the point of view of the side to move.
Value Evaluation::value() {

    // Material and piece-square tables
#ifdef SF_INCREMENTAL_PSQ
    Score score = Score(pos.psq_score());
#else
    Score score = SCORE_ZERO;
    {
    SF_PROF(PROF_EVAL_PSQ);
    for (Bitboard b = pos.pieces(); b;)
    {
        Square s = pop_lsb(b);
        score += psq[pos.piece_on(s)][s];
    }
    }
#endif

    // Bishop pair
    if (pos.count<BISHOP>(WHITE) >= 2)
        score += BishopPair;
    if (pos.count<BISHOP>(BLACK) >= 2)
        score -= BishopPair;

    // Pawn structure, which also computes pawn attacks and passed pawns
#ifdef SF_PAWN_HASH
    pe = &pawnTable[pos.pawn_key() & (SF_PAWN_HASH - 1)];
    if (pe->pawns[WHITE] != pos.pieces(WHITE, PAWN) || pe->pawns[BLACK] != pos.pieces(BLACK, PAWN))
    {
        pe->score = int(pawns<WHITE>() - pawns<BLACK>());
        for (Color c : {WHITE, BLACK})
        {
            pe->pawns[c]           = pos.pieces(c, PAWN);
            pe->passedPawns[c]     = passedPawns[c];
            pe->pawnAttacksSpan[c] = pawnAttacksSpan[c];
            pe->kingSquare[c]      = u8(SQ_NONE);
        }
    }
    else
        for (Color c : {WHITE, BLACK})
        {
            passedPawns[c]     = pe->passedPawns[c];
            pawnAttacksSpan[c] = pe->pawnAttacksSpan[c];
        }
    pawnAttacks[WHITE] = pawn_attacks_bb<WHITE>(pos.pieces(WHITE, PAWN));
    pawnAttacks[BLACK] = pawn_attacks_bb<BLACK>(pos.pieces(BLACK, PAWN));
    score += Score(pe->score);
#else
    score += pawns<WHITE>() - pawns<BLACK>();
#endif

    // Main evaluation begins here
    initialize<WHITE>();
    initialize<BLACK>();

    // Pieces evaluated first (also populates attackedBy, attackedBy2).
    // Note that the order of evaluation of the terms is left unspecified.
    score += pieces<WHITE, KNIGHT>() - pieces<BLACK, KNIGHT>() + pieces<WHITE, BISHOP>()
           - pieces<BLACK, BISHOP>() + pieces<WHITE, ROOK>() - pieces<BLACK, ROOK>()
           + pieces<WHITE, QUEEN>() - pieces<BLACK, QUEEN>();

    score += mobility[WHITE] - mobility[BLACK];

    // More complex interactions that require fully populated attack bitboards
    score += king<WHITE>() - king<BLACK>() + threats<WHITE>() - threats<BLACK>()
           + passed<WHITE>() - passed<BLACK>() + space<WHITE>() - space<BLACK>();

    score += initiative(score);

    // Interpolate between a middlegame and a (scaled by 'sf') endgame score
    int   sf  = scale_factor(eg_value(score));
    Value npm = pos.non_pawn_material();
    npm       = npm < EndgameLimit ? EndgameLimit : npm > MidgameLimit ? MidgameLimit : npm;
    int phase = ((npm - EndgameLimit) * PHASE_MIDGAME) / (MidgameLimit - EndgameLimit);

    Value v = mg_value(score) * phase
            + eg_value(score) * (PHASE_MIDGAME - phase) * sf / SCALE_FACTOR_NORMAL;

    v /= PHASE_MIDGAME;

    // Side to move point of view
    return (pos.side_to_move() == WHITE ? v : -v) + Tempo;
}

}  // namespace


// Fills the piece-square table, including the piece values. Black entries are
// the mirrored and negated white ones.
void Eval::init() {

#ifdef SF_PAWN_HASH
    clear_pawn_table();
#endif

    for (int c = 0; c < PIECE_NB; ++c)
        for (Square s = SQ_A1; s <= SQ_H8; ++s)
            psq[c][s] = SCORE_ZERO;

    for (PieceType pt = PAWN; pt <= KING; ++pt)
    {
        Piece pc = make_piece(WHITE, pt);
        Score v  = make_score(PieceValueMg[pt], PieceValueEg[pt]);

        for (Square s = SQ_A1; s <= SQ_H8; ++s)
        {
            File f = File(edge_distance(file_of(s)));

            psq[pc][s] = v
                       + (pt == PAWN ? PBonus[rank_of(s)][file_of(s)] : Bonus[pt][rank_of(s)][f]);
            psq[~pc][flip_rank(s)] = -psq[pc][s];
        }
    }
}


// Evaluate is the evaluator for the outer world. It returns a static evaluation
// of the position from the point of view of the side to move.
Value Eval::evaluate(const Position& pos) {

    SF_PROF(PROF_EVAL);
    // Insufficient material: KvK, KNvK, KBvK and KNNvK are dead draws
    if (!pos.count<PAWN>())
    {
        Value npm = pos.non_pawn_material();
        if (npm <= BishopValue
            || (npm == 2 * KnightValue
                && (pos.count<KNIGHT>(WHITE) == 2 || pos.count<KNIGHT>(BLACK) == 2)))
            return VALUE_DRAW;
    }

    // Special endgames: a lone king against enough material to mate
    for (Color c : {WHITE, BLACK})
    {
        if (!more_than_one(pos.pieces(~c)))
        {
            if (!pos.count<PAWN>(c) && pos.non_pawn_material(c) == KnightValue + BishopValue
                && pos.count<BISHOP>(c) == 1)
                return endgame_KBNK(pos, c);

            if (pos.non_pawn_material(c) >= RookValue)
                return endgame_KXK(pos, c);
        }
    }

    return Evaluation(pos).value();
}

}  // namespace Stockfish
