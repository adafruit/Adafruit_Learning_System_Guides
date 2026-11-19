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

#include "movepick.h"

#include <cassert>
#include <climits>

#include "bitboard.h"
#include "misc.h"
#include "position.h"

namespace Stockfish {

enum Stages : i8 {
    TT_MOVE,
    INIT_FIRST_STAGE,

    GOOD_CAPTURE,
    GOOD_QUIET,
    BAD_MOVES,

    QSEARCH,

    EVASION,

    PROBCUT,
};

namespace {

// Ordering bonuses for the killer moves and the counter move. They are large
// enough to put these moves in front of the other quiet moves.
constexpr int Killer1Bonus     = 1 << 20;
constexpr int Killer2Bonus     = (1 << 20) - (1 << 18);
constexpr int CounterMoveBonus = 1 << 19;

// Sort moves in descending order up to and including a given limit.
// The order of moves smaller than the limit is left unspecified.
void partial_insertion_sort(ExtMove* begin, ExtMove* end, int limit) {

    for (ExtMove *sortedEnd = begin, *p = begin + 1; p < end; ++p)
        if (p->value >= limit)
        {
            ExtMove tmp = *p, *q;
            *p          = *++sortedEnd;
            for (q = sortedEnd; q != begin && *(q - 1) < tmp; --q)
                *q = *(q - 1);
            *q = tmp;
        }
}

}  // namespace


// Constructors of the MovePicker class. As arguments, we pass information
// to decide which class of moves to emit, to help sorting the (presumably)
// good moves first, and how important move ordering is at the current node.

// MovePicker constructor for the main search and for the quiescence search
MovePicker::MovePicker(const Position&              p,
                       Move                         ttm,
                       Depth                        d,
                       const ButterflyHistory*      mh,
                       const CapturePieceToHistory* cph,
                       const Move*                  killers,
                       Move                         cm) :
    pos(p),
    mainHistory(mh),
    captureHistory(cph),
    ttMove(ttm),
    killer1(killers ? killers[0] : Move::none()),
    killer2(killers ? killers[1] : Move::none()),
    counterMove(cm),
    depth(d) {
    SF_PROF(PROF_MOVEPICKER_INIT);

    if (pos.checkers())
        first_stage = EVASION;
    else
        first_stage = depth > 0 ? GOOD_CAPTURE : QSEARCH;

    stage = ttm && pos.legal(ttm) ? TT_MOVE : INIT_FIRST_STAGE;
}

// MovePicker constructor for ProbCut: we generate captures with Static Exchange
// Evaluation (SEE) greater than or equal to the given threshold.
MovePicker::MovePicker(const Position& p, Move ttm, int th, const CapturePieceToHistory* cph) :
    pos(p),
    mainHistory(nullptr),
    captureHistory(cph),
    ttMove(ttm),
    killer1(Move::none()),
    killer2(Move::none()),
    counterMove(Move::none()),
    threshold(th),
    depth(0) {

    assert(!pos.checkers());

    first_stage = PROBCUT;
    stage       = ttm && pos.capture_stage(ttm) && pos.legal(ttm) ? TT_MOVE : INIT_FIRST_STAGE;
}

// Assigns a numerical value to each move in a list, used for sorting.
// Captures are ordered by Most Valuable Victim (MVV), preferring captures
// with a good history. Quiet moves are ordered using the history tables.
template<GenType Type>
ExtMove* MovePicker::generate_and_score() {

    static_assert(Type == CAPTURES || Type == QUIETS || Type == EVASIONS, "Wrong type");

    Color us = pos.side_to_move();

    [[maybe_unused]] Bitboard threatByLesser[KING + 1];
    if constexpr (Type == QUIETS)
    {
        threatByLesser[PAWN]   = 0;
        threatByLesser[KNIGHT] = threatByLesser[BISHOP] = pos.threats_by(PAWN);
        threatByLesser[ROOK] =
          pos.threats_by(KNIGHT) | pos.threats_by(BISHOP) | threatByLesser[KNIGHT];
        threatByLesser[QUEEN] = pos.threats_by(ROOK) | threatByLesser[ROOK];
        threatByLesser[KING]  = 0;
    }

    MoveList<Type> ml(pos);  // move generation

    ExtMove* it = cur;
    for (auto move : ml)
    {
        ExtMove& m = *it++;
        m          = move;

        const Square    from          = m.from_sq();
        const Square    to            = m.to_sq();
        const Piece     pc            = pos.moved_piece(m);
        const PieceType pt            = type_of(pc);
        const Piece     capturedPiece = pos.piece_on(to);

        if constexpr (Type == CAPTURES)
            m.value = (*captureHistory)[pc][to][type_of(capturedPiece)]
                    + 7 * int(PieceValue[capturedPiece]);

        else if constexpr (Type == QUIETS)
        {
            // histories
            int value = 2 * (*mainHistory)[us][m.from_to()];

            // refutations: killer moves and counter move
            value += m == killer1 ? Killer1Bonus
                   : m == killer2 ? Killer2Bonus
                   : m == counterMove ? CounterMoveBonus
                                      : 0;

            // bonus for checks
            value += ((pos.check_squares(pt) & to) && pos.see_ge(m, -75)) * 16384;

            // penalty for moving to a square threatened by a lesser piece
            // or bonus for escaping an attack by a lesser piece.
            int v = 20 * (bool(threatByLesser[pt] & from) - bool(threatByLesser[pt] & to));
            value += PieceValue[pt] * v;

            m.value = value;
        }

        else  // Type == EVASIONS
        {
            if (pos.capture_stage(m))
                m.value = PieceValue[capturedPiece] + (1 << 28);
            else
                m.value = (*mainHistory)[us][m.from_to()];
        }
    }
    return it;
}

// Returns the next move satisfying a predicate function.
// This never returns the TT move, as it was emitted before.
template<typename Pred>
Move MovePicker::select(Pred filter) {

    for (; cur < endCur; ++cur)
        if (*cur != ttMove && filter())
            return *cur++;

    return Move::none();
}

// This is the most important method of the MovePicker class. We emit one
// new legal move on every call until there are no more moves left,
// picking the move with the highest score from a list of generated moves.
Move MovePicker::next_move() {

    SF_PROF(PROF_NEXT_MOVE);
    constexpr int goodQuietThreshold = -14000;
dispatch:
    switch (stage)
    {

    case TT_MOVE :
        stage = INIT_FIRST_STAGE;
        return ttMove;

    case INIT_FIRST_STAGE :
        cur = endBadMoves = moves;

        if (first_stage == EVASION)
            endCur = generate_and_score<EVASIONS>();
        else
            endCur = generate_and_score<CAPTURES>();

        partial_insertion_sort(cur, endCur, INT_MIN);

        stage = first_stage;
        goto dispatch;

    case GOOD_CAPTURE :
        if (select([&]() {
                if (pos.see_ge(*cur, -cur->value / 18))
                    return true;
                *endBadMoves++ = *cur;
                return false;
            }))
            return *(cur - 1);

        endBadCaptures = endBadMoves;

        if (!skipQuiets)
        {
            // initialize quiet moves
            cur    = endBadMoves;
            endCur = generate_and_score<QUIETS>();

            partial_insertion_sort(cur, endCur, -3560 * depth);

            stage = GOOD_QUIET;
            [[fallthrough]];

        case GOOD_QUIET :
            if (select([&]() {
                    if (cur->value > goodQuietThreshold)
                        return true;
                    *endBadMoves++ = *cur;
                    return false;
                }))
                return *(cur - 1);
        }

        // Prepare the pointers to loop over the bad captures
        cur    = moves;
        endCur = endBadMoves;

        stage = BAD_MOVES;
        [[fallthrough]];

    case BAD_MOVES :
    case QSEARCH :
    case EVASION :
        return select([]() { return true; });

    case PROBCUT :
        return select([&]() { return pos.see_ge(*cur, threshold); });

    default :
        assert(false);
        return Move::none();
    }
}

void MovePicker::skip_quiet_moves() {
    skipQuiets = true;
    if (stage == BAD_MOVES || stage == GOOD_QUIET)
    {
        endCur      = endBadCaptures;  // discards any quiet moves in the current stage
        endBadMoves = endBadCaptures;  // discards bad quiet moves
    }
}

}  // namespace Stockfish
