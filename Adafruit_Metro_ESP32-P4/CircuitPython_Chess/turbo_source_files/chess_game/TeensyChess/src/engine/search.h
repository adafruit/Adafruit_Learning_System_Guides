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

// Teensy port: a single search worker without threads, UCI output, syzygy
// tablebases or NNUE. Time control is a fixed time (and/or depth) per move.

#ifndef SEARCH_H_INCLUDED
#define SEARCH_H_INCLUDED

#include <cstring>

#include "history.h"
#include "misc.h"
#include "position.h"
#include "types.h"

namespace Stockfish {

namespace Search {

// Different node types, used as a template parameter
enum NodeType {
    NonPV,
    PV,
    Root
};

// One-time initialization of the search tables
void init();

// The reductions table (for the host tests)
const int* reduction_table();

struct PVMoves {
    Move moves[MAX_PLY + 1];
    int  length = 0;

    const Move* begin() const { return moves; }
    const Move* end() const { return moves + length; }

    const Move& operator[](int index) const { return moves[index]; }

    int  size() const { return length; }
    void clear() { length = 0; }

    void update(Move move, const PVMoves* childPv) {
        length = childPv ? childPv->length : 0;

        if (childPv)
            std::memcpy(moves + 1, childPv->moves, length * sizeof(Move));

        moves[0] = move;
        ++length;
    }
};

// The beginning of a root move's principal variation. Only the first moves
// are kept, which is all the user interface needs.
struct RootPV {
    static constexpr int Capacity = 16;

    Move moves[Capacity];
    int  length = 0;

    const Move* begin() const { return moves; }
    const Move* end() const { return moves + length; }

    Move&       operator[](int index) { return moves[index]; }
    const Move& operator[](int index) const { return moves[index]; }

    bool empty() const { return length == 0; }
    int  size() const { return length; }
    void resize(int newSize) { length = newSize; }
    void push_back(Move m) {
        if (length < Capacity)
            moves[length++] = m;
    }
};

// Stack struct keeps track of the information we need to remember from nodes
// shallower and deeper in the tree during the search. Each search thread has
// its own array of Stack objects, indexed by the current ply.
struct Stack {
    PVMoves* pv;
    int      ply;
    Move     currentMove;
    Move     excludedMove;
    Move     killers[2];
    Value    staticEval;
    int      statScore;
    int      moveCount;
    bool     inCheck;
    bool     ttPv;
    bool     ttHit;
    bool     followPV;
    int      cutoffCnt;
    int      reduction;
    int      priorNMPFailHigh;
};


// RootMove struct is used for moves at the root of the tree. For each root move
// we store a score and a PV (really a refutation in the case of moves which
// fail low). Score is normally set at -VALUE_INFINITE for all non-pv moves.
struct RootMove {

    void init(Move m) {
        effort             = 0;
        score              = -VALUE_INFINITE;
        previousScore      = -VALUE_INFINITE;
        averageScore       = -VALUE_INFINITE;
        meanSquaredScore   = -VALUE_INFINITE * VALUE_INFINITE;
        uciScore           = -VALUE_INFINITE;
        inexactLower       = false;
        inexactUpper       = false;
        previousScoreExact = false;
        selDepth           = 0;
        pv.resize(0);
        pv.push_back(m);
        previousPV.resize(0);
    }
    bool is_inexact() const { return inexactLower || inexactUpper; }
    bool is_exact_loss() const {
        return score != -VALUE_INFINITE && is_loss(score) && !is_inexact();
    }
    void unset_inexact() { inexactLower = inexactUpper = false; }
    bool operator==(const Move& m) const { return pv[0] == m; }
    // Sort in descending order
    bool operator<(const RootMove& m) const {
        return m.score != score ? m.score < score : m.previousScore < previousScore;
    }

    u64    effort;
    Value  score;
    Value  previousScore;
    Value  averageScore;
    Value  meanSquaredScore;
    Value  uciScore;
    bool   inexactLower;  // By default root scores are exact, unless flagged as a
    bool   inexactUpper;  // one-sided bound here. See also `enum Bound` in types.h
    bool   previousScoreExact;
    int    selDepth;
    RootPV pv, previousPV;
};


// LimitsType struct stores information sent by the caller about the analysis required.
struct LimitsType {
    TimePoint movetime = 0;  // milliseconds, 0 = no limit
    int       depth    = 0;  // 0 = no limit
    u64       nodes    = 0;  // 0 = no limit
};


// Skill structure is used to implement strength limit. Skill 0 .. 19 covers
// CCRL Blitz Elo from 1320 to 3190 in the original Stockfish, approximately.
struct Skill {
    explicit Skill(int skill_level) :
        level(skill_level) {}
    bool enabled() const { return level < 20; }
    bool time_to_pick(Depth depth) const { return depth == 1 + level; }
    Move pick_best(const RootMove* rootMoves, int multiPV);

    int  level;
    Move best = Move::none();
};


// What the user interface gets back from a search
struct Result {
    Move   best   = Move::none();
    Move   ponder = Move::none();
    Value  score  = VALUE_NONE;  // from the point of view of the side to move
    int    depth  = 0;
    u64    nodes  = 0;
    TimePoint time = 0;
    RootPV pv;
};


// Search::Worker is the class that does the actual search.
class Worker {
   public:
    // Reset histories, usually before a new game.
    void clear();

    // Searches 'pos' (which is left unchanged) and returns the best move.
    // skillLevel 0..19 plays weaker moves on purpose, 20 is full strength.
    Result start_searching(Position& pos, const LimitsType& limits, int skillLevel);

    // Public because they need to be updatable by the stats
    ButterflyHistory      mainHistory;
    CapturePieceToHistory captureHistory;
    CounterMoveHistory    counterMoves;
    TTMoveHistory         ttMoveHistory;

   private:
    void iterative_deepening();

    void do_move(Position& pos, const Move move, StateInfo& st, const bool givesCheck, Stack* const ss);
    void do_null_move(Position& pos, StateInfo& st, Stack* const ss);
    void undo_move(Position& pos, const Move move);
    void undo_null_move(Position& pos);

    // This is the main search function, for both PV and non-PV nodes
    template<NodeType nodeType>
    Value
    search(Position& pos, Stack* ss, Value alpha, Value beta, Depth depth, const bool cutNode);

    // Quiescence search function, which is called by the main search
    template<NodeType nodeType>
    Value qsearch(Position& pos, Stack* ss, Value alpha, Value beta);

    int reduction(bool i, Depth d, int mn) const;

    void check_time();

    Value evaluate(const Position&);

    RootMove* find_root_move(Move m, int first, int last);

    LimitsType limits;
    Skill      skill{20};

    int  pvIdx, pvLast;
    u64  nodes;
    int  selDepth, nmpMinPly;
    int  callsCnt;
    bool stop;

    TimePoint startTime;

    Position* rootPos;
    RootMove  rootMoves[MAX_MOVES];
    int       rootMovesCount;
    Depth     rootDepth, completedDepth;
    bool      seekMate = false;

    RootPV lastIterationIdxPV;
};

}  // namespace Search

}  // namespace Stockfish

#endif  // #ifndef SEARCH_H_INCLUDED
