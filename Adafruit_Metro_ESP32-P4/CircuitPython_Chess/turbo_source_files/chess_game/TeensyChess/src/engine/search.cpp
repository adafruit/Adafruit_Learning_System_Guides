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

// Teensy port of Stockfish's search. The numbered steps of search() and
// qsearch() follow the original. Differences:
//   - one thread, no UCI output, no tablebases, no NNUE accumulator stack
//   - continuation, pawn and low-ply histories are replaced by killer moves and
//     counter moves (see history.h); terms that used them are adapted to the
//     butterfly history
//   - only the pawn and minor-piece correction histories are kept
//   - time control is a fixed time per move

#include "search.h"

#include <cstdlib>

#include "bitboard.h"
#include "evaluate.h"
#include "history.h"
#include "movegen.h"
#include "movepick.h"
#include "position.h"
#include "tt.h"

namespace Stockfish {

inline int lmr_divisor(int depth) {
    int d = depth < 16 ? depth : 16;
    return 3000 + 7 * (d - 8) * (d - 8);
}

using namespace Search;

namespace {

constexpr int SEARCHEDLIST_CAPACITY = 32;
using SearchedList                  = ValueList<Move, SEARCHEDLIST_CAPACITY>;

template<typename T>
constexpr T clamp(T v, T lo, T hi) {
    return v < lo ? lo : v > hi ? hi : v;
}

// Reductions lookup table indexed by depth or move number:
// reductions[i] = int(2872 / 128.0 * std::log(double(i))), reductions[0] = 0.
// Precomputed so the engine needs no floating point (tools/host_test checks it).
constexpr int reductions[MAX_MOVES] = {
    0, 0, 15, 24, 31, 36, 40, 43, 46, 49, 51, 53, 55, 57, 59, 60,
    62, 63, 64, 66, 67, 68, 69, 70, 71, 72, 73, 73, 74, 75, 76, 77,
    77, 78, 79, 79, 80, 81, 81, 82, 82, 83, 83, 84, 84, 85, 85, 86,
    86, 87, 87, 88, 88, 89, 89, 89, 90, 90, 91, 91, 91, 92, 92, 92,
    93, 93, 94, 94, 94, 95, 95, 95, 95, 96, 96, 96, 97, 97, 97, 98,
    98, 98, 98, 99, 99, 99, 99, 100, 100, 100, 100, 101, 101, 101, 101, 102,
    102, 102, 102, 103, 103, 103, 103, 103, 104, 104, 104, 104, 105, 105, 105, 105,
    105, 106, 106, 106, 106, 106, 107, 107, 107, 107, 107, 107, 108, 108, 108, 108,
    108, 109, 109, 109, 109, 109, 109, 110, 110, 110, 110, 110, 110, 111, 111, 111,
    111, 111, 111, 111, 112, 112, 112, 112, 112, 112, 113, 113, 113, 113, 113, 113,
    113, 114, 114, 114, 114, 114, 114, 114, 114, 115, 115, 115, 115, 115, 115, 115,
    116, 116, 116, 116, 116, 116, 116, 116, 117, 117, 117, 117, 117, 117, 117, 117,
    117, 118, 118, 118, 118, 118, 118, 118, 118, 118, 119, 119, 119, 119, 119, 119,
    119, 119, 119, 120, 120, 120, 120, 120, 120, 120, 120, 120, 121, 121, 121, 121,
    121, 121, 121, 121, 121, 121, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122,
    122, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 124, 124, 124, 124};

// Correction histories, indexed by pawn and minor piece keys. 16 KB each.
#ifdef SF_ARENA_TABLES
CorrectionHistory* pawnCorrectionHistory_ptr;
CorrectionHistory* minorPieceCorrectionHistory_ptr;
    #define pawnCorrectionHistory (*pawnCorrectionHistory_ptr)
    #define minorPieceCorrectionHistory (*minorPieceCorrectionHistory_ptr)
#else
CorrectionHistory pawnCorrectionHistory SF_BIGMEM;
CorrectionHistory minorPieceCorrectionHistory SF_BIGMEM;
#endif

auto& pawn_correction_entry(const Position& pos) {
    return pawnCorrectionHistory[pos.pawn_key() & (CORRHIST_SIZE - 1)];
}

auto& minor_piece_correction_entry(const Position& pos) {
    return minorPieceCorrectionHistory[pos.minor_piece_key() & (CORRHIST_SIZE - 1)];
}

// (*Scalers):
// The values with Scaler asterisks have proven non-linear scaling.
// They are optimized to time controls of 180 + 1.8 and longer,
// so changing them or adding conditions that are similar requires
// tests at these types of time controls.

int correction_value(const Position& pos) {
    SF_PROF(PROF_CORRECTION);
    const Color us   = pos.side_to_move();
    const int   pcv  = pawn_correction_entry(pos)[us];
    const int   micv = minor_piece_correction_entry(pos)[us];

    return 13806 * pcv + 9512 * micv;
}

// Add correctionHistory value to raw staticEval and guarantee evaluation
// does not hit the tablebase range.
Value to_corrected_static_eval(const Value v, const int cv) {
    return clamp(v + cv / 131072, VALUE_TB_LOSS_IN_MAX_PLY + 1, VALUE_TB_WIN_IN_MAX_PLY - 1);
}

void update_correction_history(const Position& pos, const int bonus) {
    SF_PROF(PROF_CORRECTION);
    const Color us = pos.side_to_move();

    pawn_correction_entry(pos)[us] << bonus;
    minor_piece_correction_entry(pos)[us] << bonus * 150 / 128;
}

// Add a small random component to draw evaluations to avoid 3-fold blindness
Value value_draw(u64 nodes) { return VALUE_DRAW - 1 + Value(nodes & 0x2); }
Value value_to_tt(Value v, int ply);
Value value_from_tt(Value v, int ply, int r50c);
void  update_quiet_histories(const Position& pos, Search::Worker& workerThread, Move move, int bonus);
void  update_refutations(const Position& pos, Stack* ss, Search::Worker& workerThread, Move move);
void  update_all_stats(const Position& pos,
                       Stack*          ss,
                       Search::Worker& workerThread,
                       Move            bestMove,
                       SearchedList&   quietsSearched,
                       SearchedList&   capturesSearched,
                       Depth           depth,
                       Move            ttMove,
                       bool            PvNode);

// Detect shuffling moves in order to limit search explosions. This code was
// added in #6447 as non-regression, and so its parameters should not be tuned.
bool is_shuffling(Move move, Stack* const ss, const Position& pos) {
    if (pos.capture_stage(move) || pos.rule50_count() < 10)
        return false;
    if (pos.state()->pliesFromNull < 6 || ss->ply < 20)
        return false;
    return move.from_sq() == (ss - 2)->currentMove.to_sq()
        && (ss - 2)->currentMove.from_sq() == (ss - 4)->currentMove.to_sq();
}

// Stable sort (insertion sort) of root moves in descending order
void stable_sort(RootMove* first, RootMove* last) {
    for (RootMove* p = first + 1; p < last; ++p)
    {
        RootMove  tmp = *p;
        RootMove* q   = p;
        for (; q != first && tmp < *(q - 1); --q)
            *q = *(q - 1);
        *q = tmp;
    }
}

}  // namespace


void Search::init() {}

const int* Search::reduction_table() { return reductions; }


Search::Result Search::Worker::start_searching(Position& pos, const LimitsType& lim, int skillLevel) {

    rootPos   = &pos;
    limits    = lim;
    startTime = now();
    stop      = false;
    callsCnt  = 512;
    nodes     = 0;
    nmpMinPly = 0;
    skill     = Skill(skillLevel);

    TT.new_search();

    rootMovesCount = 0;
    for (Move m : MoveList<ALL>(pos))
        rootMoves[rootMovesCount++].init(m);

    Result result;

    if (!rootMovesCount)
    {
        result.score = pos.checkers() ? -VALUE_MATE : VALUE_DRAW;
        return result;
    }

    iterative_deepening();

    const RootMove& rm = rootMoves[0];
    result.best        = rm.pv[0];
    result.ponder      = rm.pv.size() > 1 ? rm.pv[1] : Move::none();
    result.score       = rm.score != -VALUE_INFINITE ? rm.uciScore : rm.previousScore;
    result.depth       = completedDepth;
    result.nodes       = nodes;
    result.time        = now() - startTime;
    result.pv          = rm.pv;

    if (!is_valid(result.score) || result.score == -VALUE_INFINITE)
        result.score = VALUE_ZERO;

    return result;
}

// Main iterative deepening loop. It calls search() repeatedly with increasing
// depth until the allocated thinking time has been consumed, the user stops
// the search, or the maximum search depth is reached.
void Search::Worker::iterative_deepening() {

    PVMoves pv;

    RootPV lastBestMovePV;
    Value  lastBestMoveScore = -VALUE_INFINITE;

    Value alpha, beta;
    Value bestValue = -VALUE_INFINITE;
    int   delta;

    // Allocate stack with extra size to allow access from (ss - 7) to (ss + 2):
    // (ss - 7) is needed for update_continuation_histories(ss - 1) which accesses (ss - 6),
    // (ss + 2) is needed for initialization of cutOffCnt.
    Stack  stack[MAX_PLY + 10] = {};
    Stack* ss                  = stack + 7;

    for (int i = 7; i > 0; --i)
        (ss - i)->staticEval = VALUE_NONE;

    for (int i = 0; i <= MAX_PLY + 2; ++i)
        (ss + i)->ply = i;

    ss->pv = &pv;

    int multiPV = 1;

    // When playing with strength handicap enable MultiPV search that we will
    // use behind-the-scenes to retrieve a set of possible moves.
    if (skill.enabled())
        multiPV = 4;

    multiPV = multiPV < rootMovesCount ? multiPV : rootMovesCount;

    int failHighRecovery = 0;

    for (int c = 0; c < COLOR_NB; ++c)
        for (int i = 0; i < SQUARE_NB * SQUARE_NB; i++)
            mainHistory[c][i] = i16(mainHistory[c][i] * 729 / 1024);

    rootDepth = completedDepth = 0;

    // Iterative deepening loop until requested to stop or the target depth is reached
    while (rootDepth + 1 < MAX_PLY && !stop && !(limits.depth && rootDepth >= limits.depth))
    {
        rootDepth++;

        // Do not tune these values. They are not intended for playing strength.
        int seekMateThreshold = 750 + 220000 / (rootDepth * rootDepth);

        // Save the last iteration's scores before the first PV line is searched and
        // all the move scores except the (new) PV are set to -VALUE_INFINITE.
        for (int i = 0; i < rootMovesCount; ++i)
        {
            rootMoves[i].previousScore      = rootMoves[i].score;
            rootMoves[i].previousPV         = rootMoves[i].pv;
            rootMoves[i].previousScoreExact = i < multiPV;
        }

        int pvFirst = pvLast = 0;

        // MultiPV loop: we perform a full root search for each PV line
        for (pvIdx = 0; pvIdx < multiPV; ++pvIdx)
        {
            if (pvIdx == pvLast)
            {
                pvFirst = pvLast;
                pvLast  = rootMovesCount;
            }

            lastIterationIdxPV = rootMoves[pvIdx].previousPV;

            // Reset selDepth for each depth and each PV line
            selDepth = 0;

            // Reset aspiration window starting size
            delta     = 5 + std::abs(rootMoves[pvIdx].meanSquaredScore) / 10193;
            Value avg = rootMoves[pvIdx].averageScore;
            alpha     = avg - delta > -VALUE_INFINITE ? avg - delta : -VALUE_INFINITE;
            beta      = avg + delta < VALUE_INFINITE ? avg + delta : VALUE_INFINITE;

            // For multiPV we use previousScore because score is often -VALUE_INFINITE
            Value seekMateScore = pvIdx ? rootMoves[pvIdx].previousScore : rootMoves[pvIdx].score;
            seekMate =
              seekMateScore != -VALUE_INFINITE && std::abs(seekMateScore) >= seekMateThreshold;

            // Start with a small aspiration window and, in the case of a fail
            // high/low, enlarge the window progressively.
            int failedHighCnt = 0;
            if (!pvIdx)
                failHighRecovery = failHighRecovery > 2 ? failHighRecovery - 2 : 0;
            while (true)
            {
                // Adjust the effective depth searched after a fail high
                Depth adjustedDepth = rootDepth - failedHighCnt - failHighRecovery;
                adjustedDepth       = adjustedDepth > 1 ? adjustedDepth : 1;
                bestValue           = search<Root>(*rootPos, ss, alpha, beta, adjustedDepth, false);

                // Bring the best move to the front. It is critical that sorting
                // is done with a stable algorithm because all the values but the
                // first and eventually the new best one is set to -VALUE_INFINITE
                // and we want to keep the same order for all the moves except the
                // new PV that goes to the front. Note that in the case of MultiPV
                // search the already searched PV lines are preserved.
                stable_sort(rootMoves + pvIdx, rootMoves + pvLast);

                // If search has been stopped, we break immediately. Sorting is
                // safe because RootMoves is still valid, although it refers to
                // the previous iteration.
                if (stop)
                    break;

                // In case of failing low/high increase aspiration window and re-search,
                // otherwise exit the loop.
                if (bestValue <= alpha)
                {
                    beta  = alpha;
                    alpha = bestValue - delta > -VALUE_INFINITE ? bestValue - delta : -VALUE_INFINITE;

                    failedHighCnt = 0;
                }
                else if (bestValue >= beta)
                {
                    alpha = beta - delta > alpha ? beta - delta : alpha;
                    beta  = bestValue + delta < VALUE_INFINITE ? bestValue + delta : VALUE_INFINITE;
                    ++failedHighCnt;
                }
                else
                    break;

                delta += 47 * delta / 128;

                assert(alpha >= -VALUE_INFINITE && beta <= VALUE_INFINITE);
            }

            // Gradually increase depth after reduced depth search
            if (failedHighCnt > 0 && !pvIdx)
                failHighRecovery = (failedHighCnt + 1) / 2 + 2;

            // Sort the PV lines searched so far
            stable_sort(rootMoves + pvFirst, rootMoves + pvIdx + 1);

            if (stop)
                break;
        }

        const bool forgottenMate = lastBestMoveScore != -VALUE_INFINITE
                                && is_mate_or_mated(lastBestMoveScore)
                                && (std::abs(rootMoves[0].score) < std::abs(lastBestMoveScore)
                                    || rootMoves[0].is_inexact());

        if (!stop)
        {
            completedDepth = rootDepth;

            // Do not replace (shorter) mate scores from a previous iteration
            if (!forgottenMate)
            {
                lastBestMovePV    = rootMoves[0].pv;
                lastBestMoveScore = rootMoves[0].score;
            }
        }

        const bool abortedLossSearch = stop && !pvIdx && rootMoves[0].is_exact_loss();

        // An exact mated-in loss score from an aborted search cannot be
        // trusted: the loss could be delayed or refuted upon exploring the
        // remaining root-moves. Thus here we roll back to the score from the
        // previous iteration. We do the same if a search has failed to recover
        // a mate score that was found in a previous iteration.
        if (abortedLossSearch || (rootMoves[0].score != -VALUE_INFINITE && forgottenMate))
        {
            // Bring the last best move to the front
            if (!lastBestMovePV.empty())
            {
                RootMove* rm = find_root_move(lastBestMovePV[0], 0, rootMovesCount);
                if (rm)
                {
                    RootMove tmp = *rm;
                    for (RootMove* p = rm; p > rootMoves; --p)
                        *p = *(p - 1);
                    rootMoves[0]       = tmp;
                    rootMoves[0].score = rootMoves[0].uciScore = lastBestMoveScore;
                    rootMoves[0].pv                            = lastBestMovePV;
                    rootMoves[0].unset_inexact();
                }
            }
            // For an aborted d1 search we label the loss score as inexact
            else if (abortedLossSearch)
                rootMoves[0].inexactLower = true;
        }

        // If the skill level is enabled and time is up, pick a sub-optimal best move
        if (skill.enabled() && skill.time_to_pick(rootDepth))
            skill.pick_best(rootMoves, multiPV);

        // Do we have time for the next iteration? Can we stop searching now?
        if (!stop)
        {
            TimePoint elapsedTime = now() - startTime;

            // The next iteration usually takes at least as long as all the previous
            // ones, so do not start it when more than half of the time is used.
            // Also stop if we know that there are no better moves.
            if ((limits.movetime && elapsedTime > limits.movetime / 2)
                || rootMoves[multiPV - 1].score >= mate_in(3) || rootMoves[0].score == mated_in(2))
                stop = true;
        }
    }

    // If the skill level is enabled, swap the best PV line with the sub-optimal one
    if (skill.enabled())
    {
        Move      best = skill.best ? skill.best : skill.pick_best(rootMoves, multiPV);
        RootMove* rm   = find_root_move(best, 0, rootMovesCount);
        if (rm && rm != rootMoves)
        {
            RootMove tmp = rootMoves[0];
            rootMoves[0] = *rm;
            *rm          = tmp;
        }
    }
}


Search::RootMove* Search::Worker::find_root_move(Move m, int first, int last) {
    for (int i = first; i < last; ++i)
        if (rootMoves[i] == m)
            return &rootMoves[i];
    return nullptr;
}


void Search::Worker::do_move(
  Position& pos, const Move move, StateInfo& st, const bool givesCheck, Stack* const ss) {

    ++nodes;

    pos.do_move(move, st, givesCheck);

    if (ss != nullptr)
        ss->currentMove = move;
}

void Search::Worker::do_null_move(Position& pos, StateInfo& st, Stack* const ss) {
    pos.do_null_move(st);
    ss->currentMove = Move::null();
}

void Search::Worker::undo_move(Position& pos, const Move move) { pos.undo_move(move); }

void Search::Worker::undo_null_move(Position& pos) { pos.undo_null_move(); }


// Reset histories, usually before a new game
void Search::Worker::clear() {
    fill_stats(mainHistory, -5);
    fill_stats(captureHistory, -742);
    fill_stats(pawnCorrectionHistory, -5);
    fill_stats(minorPieceCorrectionHistory, -5);

    for (auto& to : counterMoves)
        for (auto& m : to)
            m = Move::none();

    ttMoveHistory = 0;
}


// Main search function for both PV and non-PV nodes
template<NodeType nodeType>
Value Search::Worker::search(
  Position& pos, Stack* ss, Value alpha, Value beta, Depth depth, const bool cutNode) {
    SF_PROF(PROF_SEARCH);

    constexpr bool PvNode   = nodeType != NonPV;
    constexpr bool rootNode = nodeType == Root;
    const bool     allNode  = !(PvNode || cutNode);

    // Dive into quiescence search when the depth reaches zero
    if (depth <= 0)
        return qsearch<PvNode ? PV : NonPV>(pos, ss, alpha, beta);

    // Limit the depth if extensions made it too large
    depth = depth < MAX_PLY - 1 ? depth : MAX_PLY - 1;

    // Check if we have an upcoming move that draws by repetition
    if (!rootNode && alpha < VALUE_DRAW && pos.upcoming_repetition(ss->ply))
    {
        alpha = value_draw(nodes);
        if (alpha >= beta)
            return alpha;
    }

    assert(-VALUE_INFINITE <= alpha && alpha < beta && beta <= VALUE_INFINITE);
    assert(PvNode || (alpha == beta - 1));
    assert(0 < depth && depth < MAX_PLY);
    assert(!(PvNode && cutNode));

    PVMoves   pv;
    StateInfo st;

    Key   posKey;
    Move  move, excludedMove, bestMove;
    Depth extension, newDepth;
    Value bestValue, value, eval, maxValue, probCutBeta;
    bool  givesCheck, improving, priorCapture, opponentWorsening;
    bool  capture, ttCapture;
    int   priorReduction;
    Piece movedPiece;

    SearchedList capturesSearched;
    SearchedList quietsSearched;

    // Step 1. Initialize node
    ss->inCheck   = pos.checkers();
    priorCapture  = pos.captured_piece();
    Color us      = pos.side_to_move();
    ss->moveCount = 0;
    bestValue     = -VALUE_INFINITE;
    maxValue      = VALUE_INFINITE;

    ss->followPV = rootNode
                || ((ss - 1)->followPV
                    && (ss->ply - 1 < lastIterationIdxPV.size()
                        && (ss - 1)->currentMove == lastIterationIdxPV[ss->ply - 1]));

    // Check for the available remaining time
    check_time();

    // Used to track the selective depth (selDepth counts from 1, ply from 0)
    if (PvNode && selDepth < ss->ply + 1)
        selDepth = ss->ply + 1;

    if (!rootNode)
    {
        // Step 2. Check for aborted search or immediate draw
        if (stop || pos.is_draw(ss->ply) || ss->ply >= MAX_PLY)
            return (ss->ply >= MAX_PLY && !ss->inCheck) ? evaluate(pos) : value_draw(nodes);

        // Step 3. Mate distance pruning. Even if we mate at the next move our score
        // would be at best mate_in(ss->ply + 1), but if alpha is already bigger because
        // a shorter mate was found upward in the tree then there is no need to search
        // because we will never beat the current alpha. Equal and opposite logic applies
        // when being mated. In either case, return a fail-high score.
        alpha = mated_in(ss->ply) > alpha ? mated_in(ss->ply) : alpha;
        beta  = mate_in(ss->ply + 1) < beta ? mate_in(ss->ply + 1) : beta;
        if (alpha >= beta)
            return alpha;
    }

    assert(0 <= ss->ply && ss->ply < MAX_PLY);

    Square prevSq  = ((ss - 1)->currentMove).is_ok() ? ((ss - 1)->currentMove).to_sq() : SQ_NONE;
    bestMove       = Move::none();
    priorReduction = (ss - 1)->reduction;
    (ss - 1)->reduction        = 0;
    ss->statScore              = 0;
    (ss + 2)->cutoffCnt        = 0;
    (ss + 1)->priorNMPFailHigh = 0;
    (ss + 2)->killers[0] = (ss + 2)->killers[1] = Move::none();

    const auto correctionValue = correction_value(pos);

    // Step 4. Transposition table lookup
    excludedMove                   = ss->excludedMove;
    posKey                         = pos.key();
    auto [ttHit, ttData, ttWriter] = TT.probe(posKey);

    ss->ttHit    = ttHit;
    ttData.move  = rootNode ? rootMoves[pvIdx].pv[0] : ttHit ? ttData.move : Move::none();
    ttData.value = ttHit ? value_from_tt(ttData.value, ss->ply, pos.rule50_count()) : VALUE_NONE;
    ss->ttPv     = excludedMove ? ss->ttPv : PvNode || (ttHit && ttData.is_pv);
    ttCapture    = ttData.move && pos.capture_stage(ttData.move);

    // Step 5. Static evaluation of the position
    Value unadjustedStaticEval = VALUE_NONE;

    // Skip early pruning when in check
    if (ss->inCheck)
        ss->staticEval = eval = (ss - 2)->staticEval;
    else if (excludedMove)
        unadjustedStaticEval = eval = ss->staticEval;
    else if (ss->ttHit)
    {
        // Never assume anything about values stored in TT
        unadjustedStaticEval = ttData.eval;
        if (!is_valid(unadjustedStaticEval))
            unadjustedStaticEval = evaluate(pos);

        ss->staticEval = eval = to_corrected_static_eval(unadjustedStaticEval, correctionValue);

        // ttValue can be used as a better position evaluation
        if (is_valid(ttData.value)
            && (ttData.bound & (ttData.value > eval ? BOUND_LOWER : BOUND_UPPER)))
            eval = ttData.value;
    }
    else
    {
        unadjustedStaticEval = evaluate(pos);
        ss->staticEval = eval = to_corrected_static_eval(unadjustedStaticEval, correctionValue);

        // Static evaluation is saved as it was before adjustment by correction history
        ttWriter.write(posKey, VALUE_NONE, ss->ttPv, BOUND_NONE, DEPTH_UNSEARCHED, Move::none(),
                       unadjustedStaticEval, TT.generation());
    }

    // Set up the improving flag, which is true if current static evaluation is
    // bigger than the previous static evaluation at our turn (if we were in
    // check at our previous move we go back until we weren't in check) and is
    // false otherwise. The improving flag is used in various pruning heuristics.
    // Similarly, opponentWorsening is true if our static evaluation is better
    // for us than at the last ply.
    improving         = ss->staticEval > (ss - 2)->staticEval;
    opponentWorsening = ss->staticEval > -(ss - 1)->staticEval;

    // Hindsight adjustment of reductions based on static evaluation difference
    if (priorReduction >= 3 && !opponentWorsening)
        depth++;
    if (priorReduction >= 2 && depth >= 2 && ss->staticEval + (ss - 1)->staticEval > 166)
        depth--;

    // Step 6. At non-PV nodes we check for an early TT cutoff
    if (!PvNode && !excludedMove && is_valid(ttData.value)
        && ttData.depth > depth - (ttData.value <= beta))
    {
        // Case A: TT entry can produce a cutoff
        if ((ttData.bound & (ttData.value >= beta ? BOUND_LOWER : BOUND_UPPER))
            && (cutNode == (ttData.value >= beta) || depth > 4))
        {
            // If the ttMove is quiet, update move sorting heuristics on TT hit
            if (ttData.move && ttData.value >= beta)
            {
                // Bonus for a quiet ttMove that fails high
                if (!ttCapture)
                {
                    update_quiet_histories(pos, *this, ttData.move, 131 * depth);
                    update_refutations(pos, ss, *this, ttData.move);
                }

                // Extra penalty for early quiet moves of the previous ply
                if (prevSq != SQ_NONE && (ss - 1)->moveCount < 5 && !priorCapture)
                    mainHistory[~us][((ss - 1)->currentMove).from_to()] << -2210 / 2;
            }

            // Partial workaround for the graph history interaction problem.
            // For high rule50 counts don't produce transposition table cutoffs.
            if (pos.rule50_count() < 96)
            {
                if (depth >= 7 && ttData.move && pos.legal(ttData.move)
                    && !is_decisive(ttData.value))
                {
                    pos.do_move(ttData.move, st);
                    Key nextPosKey                             = pos.key();
                    auto [ttHitNext, ttDataNext, ttWriterNext] = TT.probe(nextPosKey);
                    pos.undo_move(ttData.move);

                    // Check that the ttValue after the tt move would also trigger a cutoff
                    if (!is_valid(ttDataNext.value))
                        return ttData.value;

                    if ((ttData.value >= beta) == (-ttDataNext.value >= beta))
                        return ttData.value;
                }
                else
                    return ttData.value;
            }
        }
        // Case B: No cutoff, but depth was sufficient, so the bound points the wrong way.
        else if (depth > 5)
        {
            assert(!(ttData.bound & (ttData.value >= beta ? BOUND_LOWER : BOUND_UPPER)));

            // If such a mismatch is the only reason cutoff failed, the TT entry is now useless
            ttWriter.penalize(1);
        }
    }

    if (ss->inCheck)
        goto moves_loop;

    // Use static evaluation difference to improve quiet move ordering
    if (((ss - 1)->currentMove).is_ok() && !(ss - 1)->inCheck && !priorCapture)
    {
        int evalDiff = clamp(-int((ss - 1)->staticEval + ss->staticEval), -189, 194) + 60;
        mainHistory[~us][((ss - 1)->currentMove).from_to()] << evalDiff * 11;
    }


    // Step 8. Razoring
    // If eval is really low, skip search entirely and return the qsearch value
    if (allNode && eval < alpha - 342 * depth && !seekMate)
        return qsearch<NonPV>(pos, ss, alpha, beta);

    // Step 9. Futility pruning: child node
    // The depth condition is important for mate finding. It should NOT be tuned.
    if (!ss->ttPv && depth < (seekMate ? 6 : 19) && eval >= beta && (!ttData.move || ttCapture)
        && !is_loss(beta) && !is_win(eval))
    {
        Value futilityMult = 45 + depth * 4 < 85 ? 45 + depth * 4 : 85;
        futilityMult -= 20 * !ss->ttHit;

        Value futilityMargin = futilityMult * depth
                             - (2789 * improving + 335 * opponentWorsening) * futilityMult / 1024
                             + std::abs(correctionValue) / 198435;

        if (eval - futilityMargin >= beta)
            return (661 * beta + 363 * eval) / 1024;
    }

    // Step 10. Null move search with verification search
    if (cutNode
        && ss->staticEval + 50 * ss->priorNMPFailHigh >= beta - 13 * depth - 47 * improving + 365
        && !excludedMove && pos.non_pawn_material(us) && ss->ply >= nmpMinPly && beta >= -2000)
    {
        assert((ss - 1)->currentMove != Move::null());

        // Null move dynamic reduction based on depth
        int   evalMargin = (ss->staticEval - beta) / 256;
        Depth R          = 7 + depth / 3 + (evalMargin > 0 ? evalMargin : 0);
        R -= seekMate * R / 2;
        do_null_move(pos, st, ss);

        Value nullValue = -search<NonPV>(pos, ss + 1, -beta, -beta + 1, depth - R, false);

        undo_null_move(pos);

        // Do not return unproven mate or TB scores
        if (nullValue >= beta && !is_win(nullValue))
        {
            if (nmpMinPly || depth < 16)
            {
                ++ss->priorNMPFailHigh;
                return nullValue;
            }

            // Recursive verification is not allowed
            assert(!nmpMinPly);

            // Do verification search at high depths, with null move pruning
            // disabled until ply exceeds nmpMinPly.
            nmpMinPly = ss->ply + 3 * (depth - R) / 4;

            Value v = search<NonPV>(pos, ss, beta - 1, beta, depth - R, false);

            nmpMinPly = 0;

            if (v >= beta)
            {
                ++ss->priorNMPFailHigh;
                return nullValue;
            }
        }
    }

    improving |= ss->staticEval >= beta;

    // Step 11. Internal iterative reductions
    // At sufficient depth, reduce depth for PV/Cut nodes without a TTMove.
    // (*Scaler) Making IIR more aggressive scales poorly.
    if (!ss->followPV && !allNode && depth >= 6 && !ttData.move)
        depth--;

    // Step 12. ProbCut
    // If we have a good enough capture (or queen promotion) and a reduced search
    // returns a value much above beta, we can (almost) safely prune the previous move.
    probCutBeta = beta + 241 - 64 * improving;
    if (depth >= 3 && !is_decisive(beta) && !(is_valid(ttData.value) && ttData.value < probCutBeta))
    {
        assert(probCutBeta < VALUE_INFINITE && probCutBeta > beta);

        MovePicker mp(pos, ttData.move, probCutBeta - ss->staticEval, &captureHistory);
        Depth      probCutDepth = depth - (improving ? 5 : 3);

        while ((move = mp.next_move()) != Move::none())
        {
            assert(move.is_ok());

            if (move == excludedMove)
                continue;

            assert(pos.capture_stage(move));

            do_move(pos, move, st, pos.gives_check(move), ss);
            // Perform a preliminary qsearch to verify that the move holds
            value = -qsearch<NonPV>(pos, ss + 1, -probCutBeta, -probCutBeta + 1);

            // If the qsearch held, perform the regular search
            if (value >= probCutBeta && probCutDepth > 0)
                value = -search<NonPV>(pos, ss + 1, -probCutBeta, -probCutBeta + 1, probCutDepth,
                                       !cutNode);

            undo_move(pos, move);

            if (value >= probCutBeta)
            {
                // Save ProbCut data into transposition table
                ttWriter.write(posKey, value_to_tt(value, ss->ply), ss->ttPv, BOUND_LOWER,
                               probCutDepth + 1, move, unadjustedStaticEval, TT.generation());

                if (!is_decisive(value))
                    return value - (probCutBeta - beta);
            }
        }
    }

moves_loop:  // When in check, search starts here

    // Step 13. A small ProbCut idea
    probCutBeta = beta + 428;
    if ((ttData.bound & BOUND_LOWER) && ttData.depth >= depth - 4 && ttData.value >= probCutBeta
        && !is_decisive(beta) && is_valid(ttData.value) && !is_decisive(ttData.value) && !seekMate)
        return probCutBeta;

    Move counterMove = prevSq != SQ_NONE ? counterMoves[pos.piece_on(prevSq)][prevSq] : Move::none();

    MovePicker mp(pos, ttData.move, depth, &mainHistory, &captureHistory, ss->killers, counterMove);

    value = bestValue;

    int moveCount = 0;

    // Step 14. Loop through all legal moves until no moves remain
    // or a beta cutoff occurs.
    while ((move = mp.next_move()) != Move::none())
    {
        assert(move.is_ok());

        if (move == excludedMove)
            continue;

        // At root skip moves not listed in the root move list. In MultiPV mode we
        // also skip PV moves that have been already searched.
        if (rootNode && !find_root_move(move, pvIdx, pvLast))
            continue;

        ss->moveCount = ++moveCount;

        if (PvNode)
            (ss + 1)->pv = nullptr;

        extension  = 0;
        capture    = pos.capture_stage(move);
        movedPiece = pos.moved_piece(move);
        givesCheck = pos.gives_check(move);

        // Calculate new depth for this move
        newDepth = depth - 1;

        int r = reduction(improving, depth, moveCount);

        // Decrease reduction for PvNodes
        if (PvNode)
            r -= 512;

        // Increase reduction for ttPv nodes
        // (*Scaler) Larger values scale well.
        if (ss->ttPv)
            r += 929;

        // Step 15. Pruning at shallow depths.
        // Depth conditions are important for mate finding.
        if (!rootNode && pos.non_pawn_material(us) && !is_loss(bestValue))
        {
            // Skip quiet moves if movecount exceeds our threshold
            if (moveCount >= (3 + depth * depth) / (2 - improving))
                mp.skip_quiet_moves();

            // Reduced depth of the next LMR search
            int lmrDepth = newDepth - r / 1024;

            if (capture || givesCheck)
            {
                Piece capturedPiece = pos.piece_on(move.to_sq());
                int   captHist = captureHistory[movedPiece][move.to_sq()][type_of(capturedPiece)];

                // Futility pruning for captures
                if (!givesCheck && lmrDepth < 8)
                {
                    Value futilityValue = ss->staticEval + 234 + 247 * lmrDepth
                                        + PieceValue[capturedPiece] + 134 * captHist / 1024;

                    if (futilityValue <= alpha)
                        continue;
                }

                // SEE based pruning for captures and checks.
                // Avoid pruning sacrifices of our last piece for stalemate.
                int margin = 177 * depth + captHist * 34 / 1024;
                if ((alpha >= VALUE_DRAW || pos.non_pawn_material(us) != PieceValue[movedPiece])
                    && !pos.see_ge(move, -margin))
                    continue;
            }
            else if (!ss->followPV || !PvNode)
            {
                int history = 2 * mainHistory[us][move.from_to()];

                // History based pruning
                if (history < -4136 * depth)
                    continue;

                history += 69 * mainHistory[us][move.from_to()] / 32;

                // (*Scaler): Generally, lower divisors scale well
                lmrDepth += history / lmr_divisor(depth);

                Value futilityValue =
                  ss->staticEval + 119 * lmrDepth + 90 * (ss->staticEval > alpha) + 164;

                // Futility pruning: parent node
                // (*Scaler): Generally, more frequent futility pruning scales well
                if (!ss->inCheck && lmrDepth < 12 && futilityValue <= alpha)
                {
                    if (bestValue <= futilityValue && !is_decisive(bestValue)
                        && !is_win(futilityValue))
                        bestValue = futilityValue;
                    continue;
                }

                lmrDepth = lmrDepth > 0 ? lmrDepth : 0;

                // Prune moves with negative SEE
                if (!pos.see_ge(move, -23 * lmrDepth * lmrDepth))
                    continue;
            }
        }

        // Step 16. Singular Extensions
        //
        // We check for "only moves": if one move fails high on (alpha, beta) but all
        // others fail low on (alpha-s, beta-s), then that move is singular. Singular
        // moves are extended to better estimate the result of the (putatively)
        // forced line. If it's non-singular, we may do some pruning or reduction.
        //
        // Recursive excluded search is avoided. The `excludedMove` mechanism
        // was historically a hack and remains a bit fragile.
        if (!rootNode && move == ttData.move && !excludedMove && depth >= 6 + ss->ttPv
            && is_valid(ttData.value) && !is_decisive(ttData.value) && (ttData.bound & BOUND_LOWER)
            && ttData.depth >= depth - 3 && !is_shuffling(move, ss, pos) && !seekMate)
        {
            Value singularBeta  = ttData.value - (59 + 66 * (ss->ttPv && !PvNode)) * depth / 63;
            Depth singularDepth = newDepth / 2;

            ss->excludedMove = move;
            value = search<NonPV>(pos, ss, singularBeta - 1, singularBeta, singularDepth, cutNode);
            ss->excludedMove = Move::none();

            if (value < singularBeta)
            {
                int corrValAdj   = std::abs(correctionValue) / 198368;
                int doubleMargin = -2 + 204 * PvNode - 152 * !ttCapture - corrValAdj
                                 - 1175 * ttMoveHistory / 114178 - (ss->ply > rootDepth) * 38;
                int tripleMargin = 70 + 279 * PvNode - 188 * !ttCapture + 81 * ss->ttPv - corrValAdj
                                 - (ss->ply > rootDepth) * 43;

                extension =
                  1 + (value < singularBeta - doubleMargin) + (value < singularBeta - tripleMargin);

                depth++;
            }

            // Multi-cut pruning
            // Our ttMove is assumed to fail high based on the bound of the TT entry,
            // and if after excluding the ttMove with a reduced search we fail high
            // over the original beta, we assume this expected cut-node is not
            // singular (multiple moves fail high), and we can prune the whole
            // subtree by returning a softbound.
            else if (value >= beta && !is_decisive(value))
            {
                ttMoveHistory << -421 - 110 * depth;

                if (!ss->inCheck && value > ss->staticEval)
                {
                    const int bonus =
                      clamp(int(value - ss->staticEval) * 664 / 1024,
                            -CORRECTION_HISTORY_LIMIT / 4, CORRECTION_HISTORY_LIMIT / 4);
                    update_correction_history(pos, bonus);
                }

                return value;
            }

            // Negative extensions
            // If other moves failed high over (ttValue - margin) without the
            // ttMove on a reduced search, but we cannot do multi-cut because
            // (ttValue - margin) is lower than the original beta, we do not know
            // if the ttMove is singular or can do a multi-cut, so we reduce the
            // ttMove in favor of other moves based on some conditions:

            // If the ttMove is assumed to fail high over current beta or
            // if we are on a cutNode
            else if (ttData.value >= beta || cutNode)
                extension = -3;
        }

        u64 nodeCount = rootNode ? nodes : 0;

        // Step 17. Make the move
        do_move(pos, move, st, givesCheck, ss);

        // Add extension to new depth
        newDepth += extension;

        // Step 18. Compute and apply late moves reductions/extensions (LMR)

        // Decrease reduction for PvNodes (*Scaler)
        if (ss->ttPv)
            r -= 3023 + PvNode * 1004 + (ttData.value > alpha) * 885
               + (ttData.depth >= depth) * (816 + cutNode * 940);

        // Base reduction offset to compensate for other tweaks
        r += 697;

        r -= moveCount * 65;
        r -= std::abs(correctionValue) / 26310;

        // Increase reduction for cut nodes
        if (cutNode)
            r += 4026 + 933 * !ttData.move;

        // Increase reduction if ttMove is a capture
        if (ttCapture)
            r += 1079;

        // Increase reduction if next ply has a lot of fail high
        if ((ss + 1)->cutoffCnt > 1)
            r += 264 + 1095 * ((ss + 1)->cutoffCnt > 2) + 1138 * allNode;

        // For first picked move (ttMove) reduce reduction
        else if (move == ttData.move)
            r -= 2179;

        if (capture)
            ss->statScore = 873 * int(PieceValue[pos.captured_piece()]) / 128
                          + captureHistory[movedPiece][move.to_sq()][type_of(pos.captured_piece())];
        else
            ss->statScore = 2252 * 2 * mainHistory[us][move.from_to()] / 1024;

        // Decrease/increase reduction for moves with a good/bad history
        r -= ss->statScore * 439 / 4096;

        if (!capture && !is_decisive(alpha))
            r += 3 * clamp(alpha - eval, -64, 96);

        // Scale up reductions for expected ALL nodes
        if (allNode)
            r += r * 276 / (256 * depth + 268);

        // When seeking a mate, reduce non-checking moves more and checking moves less
        if (seekMate && r > 0)
            r += (givesCheck ? -r : r) / 4;

        // Apply the computed LMR
        if (depth >= 2 && moveCount > 1)
        {
            // In general we want to cap the LMR depth search at newDepth, but when
            // reduction is negative, we allow this move a limited search extension
            // beyond the first move depth. To avoid search explosion, extensions
            // are not allowed deep, relative to rootDepth, in the search tree.
            int   ext = -r / 1024 < (ss->ply < 2 * rootDepth ? 2 : 0) ? -r / 1024
                                                                       : (ss->ply < 2 * rootDepth ? 2 : 0);
            Depth d   = (newDepth + ext > 1 ? newDepth + ext : 1) + PvNode;

            ss->reduction = newDepth - d;
            value         = -search<NonPV>(pos, ss + 1, -(alpha + 1), -alpha, d, true);
            ss->reduction = 0;

            // Do a full-depth search when reduced LMR search fails high
            // (*Scaler) Shallower searches here don't scale well
            if (value > alpha)
            {
                // Adjust full-depth search based on LMR results - if the result was
                // good enough search deeper, if it was bad enough search shallower.
                const bool doDeeperSearch    = d < newDepth && value > bestValue + 53;
                const bool doShallowerSearch = value < bestValue + 8;

                newDepth += doDeeperSearch - doShallowerSearch;

                if (newDepth > d)
                    value = -search<NonPV>(pos, ss + 1, -(alpha + 1), -alpha, newDepth, !cutNode);
            }
        }

        // Step 19. Full-depth search when LMR is skipped
        else if (!PvNode || moveCount > 1)
        {
            // Increase reduction if ttMove is not present
            if (!ttData.move)
                r += 1127;

            // If expected reduction is high, we reduce search depth here
            value = -search<NonPV>(pos, ss + 1, -(alpha + 1), -alpha,
                                   newDepth - (r > 5234) - (r > 5487 && newDepth > 2), !cutNode);
        }

        // Step 20. For PV nodes only, do a full PV search on the first move
        // or after a fail high, otherwise let the parent node fail low with
        // value <= alpha and try another move.
        if (PvNode && (moveCount == 1 || value > alpha))
        {
            (ss + 1)->pv = &pv;
            (ss + 1)->pv->clear();

            // Extend move from transposition table if we are about to dive
            // into qsearch. Decisive score handling improves mate finding
            // and retrograde analysis.
            if (move == ttData.move
                && ((is_valid(ttData.value) && is_decisive(ttData.value) && ttData.depth > 0)
                    || ttData.depth > 1))
                newDepth = newDepth > 1 ? newDepth : 1;

            value = -search<PV>(pos, ss + 1, -beta, -alpha, newDepth, false);
        }

        // Step 21. Undo move
        undo_move(pos, move);

        assert(value > -VALUE_INFINITE && value < VALUE_INFINITE);

        // Step 22. Check for a new best move
        // If a stop occurred, the value of the search cannot be trusted,
        // and we return immediately without updating the best move,
        // principal variation or transposition table.
        if (stop)
            return VALUE_ZERO;

        if (rootNode)
        {
            RootMove& rm = *find_root_move(move, 0, rootMovesCount);

            rm.effort += nodes - nodeCount;

            u64 N      = nodes - nodeCount;
            u64 E_prev = rm.effort - N > 1 ? rm.effort - N : 1;

            // Exponential moving average parameters for root move
            constexpr u64 Scale          = 32;
            constexpr u64 ChiNumerator   = 3;
            constexpr u64 ChiDenominator = 2;   // Chi = 3/2 = 1.5
            constexpr u64 MinWeight      = 12;  // 37.5% minimum weight
            constexpr u64 MaxWeight      = 24;  // 75% maximum weight

            u64 w = clamp((Scale * N * ChiDenominator) / (N * ChiDenominator + ChiNumerator * E_prev),
                          MinWeight, MaxWeight);
            u64 w_mss = w < 16 ? w : 16;
            i64 v2    = i64(value) * std::abs(value);

            if (rm.averageScore == -VALUE_INFINITE)
                rm.averageScore = value;
            else
                rm.averageScore = Value((value * i64(w) + rm.averageScore * i64(Scale - w)) / i64(Scale));

            if (rm.meanSquaredScore == -VALUE_INFINITE * VALUE_INFINITE)
                rm.meanSquaredScore = value * std::abs(value);
            else
                rm.meanSquaredScore = Value((v2 * i64(w_mss) + i64(rm.meanSquaredScore) * i64(Scale - w_mss))
                                            / i64(Scale));

            // PV move or new best move?
            if (moveCount == 1 || value > alpha)
            {
                rm.score = rm.uciScore = value;
                rm.selDepth            = selDepth;
                rm.unset_inexact();

                if (value >= beta)
                {
                    rm.inexactLower = true;
                    rm.uciScore     = beta;
                }
                else if (value <= alpha)
                {
                    rm.inexactUpper = true;
                    rm.uciScore     = alpha;
                }

                rm.pv.resize(1);

                assert((ss + 1)->pv);

                for (Move pvMove : *(ss + 1)->pv)
                    rm.pv.push_back(pvMove);
            }
            else
                // All other moves but the PV are set to the lowest value: this
                // is not a problem when sorting because the sort is stable and the
                // move position in the list is preserved -- just the PV is pushed up.
                rm.score = -VALUE_INFINITE;
        }

        // If we have an alternative move equal in value to the current bestmove,
        // we sometimes promote it to bestmove by pretending it just exceeds
        // alpha (but not beta).
        int inc = (value == bestValue && ss->ply + 2 >= rootDepth && (int(nodes) & 14) == 0
                   && !is_win(std::abs(value) + 1));

        if (value + inc > bestValue)
        {
            bestValue = value;

            if (value + inc > alpha)
            {
                bestMove = move;

                // Update PV even in fail-high case
                if (PvNode && !rootNode)
                    ss->pv->update(move, (ss + 1)->pv);

                if (value >= beta)
                {
                    // (*Scaler) Infrequent and small updates scale well
                    ss->cutoffCnt += (extension < 2) || PvNode;
                    assert(value >= beta);  // Fail high
                    break;
                }

                // Reduce other moves if we have found at least one score improvement
                if (depth > 3 && depth < 12 && !is_decisive(value))
                    depth -= 3;

                assert(depth > 0);
                alpha = value;  // Update alpha! Always alpha < beta
            }
        }

        // If the move is worse than some previously searched move,
        // remember it, to update its stats later.
        if (move != bestMove && moveCount <= SEARCHEDLIST_CAPACITY)
        {
            if (capture)
                capturesSearched.push_back(move);
            else
                quietsSearched.push_back(move);
        }
    }

    // Step 23. Check for mate and stalemate, otherwise update bestmove/countermove stats

    assert(moveCount || !ss->inCheck || excludedMove || !MoveList<ALL>(pos).size());

    // Adjust best value for fail high cases
    if (bestValue >= beta && !is_decisive(bestValue) && !is_decisive(alpha))
        bestValue = (bestValue * depth + beta) / (depth + 1);

    // All legal moves have been searched: if there are no legal moves, it
    // must be a mate or a stalemate (just a fail low score if we are in a
    // singular extension search).
    if (!moveCount)
        bestValue = excludedMove ? alpha : ss->inCheck ? mated_in(ss->ply) : VALUE_DRAW;

    // If there is a move that produces search value greater than alpha,
    // we update the stats of searched moves.
    else if (bestMove)
    {
        update_all_stats(pos, ss, *this, bestMove, quietsSearched, capturesSearched, depth,
                         ttData.move, PvNode);
        if (!PvNode)
            ttMoveHistory << (bestMove == ttData.move ? 918 : -747);
    }

    // Bonus for prior quiet countermove that caused the fail low
    else if (!priorCapture && prevSq != SQ_NONE)
    {
        int bonusScale = -241;
        bonusScale -= (ss - 1)->statScore / 98;
        bonusScale += 59 * depth < 420 ? 59 * depth : 420;
        bonusScale += 186 * ((ss - 1)->moveCount > 9);
        bonusScale += 142 * (!ss->inCheck && bestValue <= ss->staticEval - 106);
        bonusScale += 159 * (!(ss - 1)->inCheck && bestValue <= -(ss - 1)->staticEval - 68);

        bonusScale = bonusScale > 0 ? bonusScale : 0;

        // scaledBonus ranges from 0 to roughly 2.3M, overflows happen for
        // multipliers larger than 900
        const int scaledBonus = (150 * depth - 85 < 1337 ? 150 * depth - 85 : 1337) * bonusScale;

        mainHistory[~us][((ss - 1)->currentMove).from_to()] << scaledBonus * 215 / 32768;
    }

    // Bonus for prior capture countermove that caused the fail low
    else if (prevSq != SQ_NONE)
    {
        assert(priorCapture);

        Piece capturedPiece = pos.captured_piece();
        assert(capturedPiece != NO_PIECE);
        captureHistory[pos.piece_on(prevSq)][prevSq][type_of(capturedPiece)] << 892;
    }

    if (PvNode)
        bestValue = bestValue < maxValue ? bestValue : maxValue;

    // If no good move is found and the previous position was ttPv, then the previous
    // opponent move is probably good and the new position is added to the search tree.
    if (bestValue <= alpha)
        ss->ttPv = ss->ttPv || (ss - 1)->ttPv;

    // Step 24. Write gathered information in transposition table. Note that the
    // static evaluation is saved as it was before correction history.
    if (!excludedMove && !(rootNode && pvIdx))
        ttWriter.write(posKey, value_to_tt(bestValue, ss->ply), ss->ttPv,
                       bestValue >= beta    ? BOUND_LOWER
                       : PvNode && bestMove ? BOUND_EXACT
                                            : BOUND_UPPER,
                       moveCount != 0 ? depth : (depth + 6 < MAX_PLY - 1 ? depth + 6 : MAX_PLY - 1),
                       bestMove, unadjustedStaticEval, TT.generation());

    // Adjust correction history if the best move is not a capture and
    // the error direction matches whether we are above/below bounds.
    if (!ss->inCheck && !(bestMove && pos.capture(bestMove))
        && (bestValue > ss->staticEval) == bool(bestMove))
    {
        auto bonus = clamp(int(bestValue - ss->staticEval) * depth * (bestMove ? 12 : 18) / 128,
                           -CORRECTION_HISTORY_LIMIT / 4, CORRECTION_HISTORY_LIMIT / 4);
        update_correction_history(pos, 1061 * bonus / 1024);
    }

    // The search is now complete
    assert(-VALUE_INFINITE < bestValue && bestValue < VALUE_INFINITE);
    return bestValue;
}


// Quiescence search function, which is called by the main search function with
// depth zero, or recursively with further decreasing depth. With depth <= 0, we
// "should" be using static eval only, but tactical moves may confuse the static eval.
// To fight this horizon effect, we implement this qsearch of tactical moves.
// See https://www.chessprogramming.org/Horizon_Effect
// and https://www.chessprogramming.org/Quiescence_Search
template<NodeType nodeType>
Value Search::Worker::qsearch(Position& pos, Stack* ss, Value alpha, Value beta) {
    SF_PROF(PROF_QSEARCH);

    static_assert(nodeType != Root);
    constexpr bool PvNode = nodeType == PV;

    assert(alpha >= -VALUE_INFINITE && alpha < beta && beta <= VALUE_INFINITE);
    assert(PvNode || (alpha == beta - 1));

    // Check if we have an upcoming move that draws by repetition
    if (alpha < VALUE_DRAW && pos.upcoming_repetition(ss->ply))
    {
        alpha = value_draw(nodes);
        if (alpha >= beta)
            return alpha;
    }

    PVMoves   pv;
    StateInfo st;

    Key   posKey;
    Move  move, bestMove;
    Value bestValue, value, futilityBase;
    bool  pvHit, givesCheck, capture;
    int   moveCount;

    // Step 1. Initialize node
    if (PvNode)
    {
        (ss + 1)->pv = &pv;
        ss->pv->clear();
    }

    bestMove    = Move::none();
    ss->inCheck = pos.checkers();
    moveCount   = 0;

    // Used to track the selective depth (selDepth counts from 1, ply from 0)
    if (PvNode && selDepth < ss->ply + 1)
        selDepth = ss->ply + 1;

    // Step 2. Check for an immediate draw or maximum ply reached
    if (pos.is_draw(ss->ply) || ss->ply >= MAX_PLY)
        return (ss->ply >= MAX_PLY && !ss->inCheck) ? evaluate(pos) : VALUE_DRAW;

    assert(0 <= ss->ply && ss->ply < MAX_PLY);

    // Step 3. Transposition table lookup
    posKey                         = pos.key();
    auto [ttHit, ttData, ttWriter] = TT.probe(posKey);

    ss->ttHit    = ttHit;
    ttData.move  = ttHit ? ttData.move : Move::none();
    ttData.value = ttHit ? value_from_tt(ttData.value, ss->ply, pos.rule50_count()) : VALUE_NONE;
    pvHit        = ttHit && ttData.is_pv;

    // At non-PV nodes we check for an early TT cutoff
    if (!PvNode && ttData.depth >= DEPTH_QS && is_valid(ttData.value)
        && (ttData.bound & (ttData.value >= beta ? BOUND_LOWER : BOUND_UPPER)))
        return ttData.value;

    // Step 4. Static evaluation of the position
    Value unadjustedStaticEval = VALUE_NONE;
    if (ss->inCheck)
        bestValue = futilityBase = -VALUE_INFINITE;
    else
    {
        const auto correctionValue = correction_value(pos);

        if (ss->ttHit)
        {
            // Never assume anything about values stored in TT
            unadjustedStaticEval = ttData.eval;

            if (!is_valid(unadjustedStaticEval))
                unadjustedStaticEval = evaluate(pos);

            ss->staticEval = bestValue =
              to_corrected_static_eval(unadjustedStaticEval, correctionValue);

            // ttValue can be used as a better position evaluation
            if (is_valid(ttData.value) && !is_decisive(ttData.value)
                && (ttData.bound & (ttData.value > bestValue ? BOUND_LOWER : BOUND_UPPER)))
                bestValue = ttData.value;
        }
        else
        {
            unadjustedStaticEval = evaluate(pos);
            ss->staticEval       = bestValue =
              to_corrected_static_eval(unadjustedStaticEval, correctionValue);
        }

        // Stand pat. Return immediately if static value is at least beta
        if (bestValue >= beta)
        {
            assert(!is_decisive(bestValue));
            bestValue = (441 * bestValue + 583 * beta) / 1024;

            if (!ss->ttHit)
                ttWriter.write(posKey, VALUE_NONE, false, BOUND_LOWER, DEPTH_UNSEARCHED,
                               Move::none(), unadjustedStaticEval, TT.generation());
            return bestValue;
        }

        if (bestValue > alpha)
            alpha = bestValue;

        futilityBase = ss->staticEval + 306;
    }

    Square prevSq = ((ss - 1)->currentMove).is_ok() ? ((ss - 1)->currentMove).to_sq() : SQ_NONE;

    // Initialize a MovePicker object for the current position, and prepare
    // to search the moves. We presently use two stages of move generator in
    // quiescence search: captures, or evasions only when in check.
    MovePicker mp(pos, ttData.move, DEPTH_QS, &mainHistory, &captureHistory, nullptr, Move::none());

    // Step 5. Loop through all legal moves until no moves remain
    // or a beta cutoff occurs.
    while ((move = mp.next_move()) != Move::none())
    {
        assert(move.is_ok());

        givesCheck = pos.gives_check(move);
        capture    = pos.capture_stage(move);

        moveCount++;

        // Step 6. Pruning
        if (!is_loss(bestValue))
        {
            // Futility pruning and moveCount pruning
            if (!givesCheck && move.to_sq() != prevSq && !is_loss(futilityBase)
                && move.type_of() != PROMOTION)
            {
                if (moveCount > 2)
                    continue;

                Value futilityValue = futilityBase + PieceValue[pos.piece_on(move.to_sq())];

                // If static eval + value of piece we are going to capture is
                // much lower than alpha, we can prune this move.
                if (futilityValue <= alpha)
                {
                    bestValue = bestValue > futilityValue ? bestValue : futilityValue;
                    continue;
                }

                // If static exchange evaluation is low enough, we can prune
                if (!pos.see_ge(move, alpha - futilityBase))
                {
                    Value cap = alpha < futilityBase ? alpha : futilityBase;
                    bestValue = bestValue > cap ? bestValue : cap;
                    continue;
                }
            }

            // Skip non-captures
            if (!capture)
                continue;

            // Do not search moves with bad enough SEE values
            if (!pos.see_ge(move, -74))
                continue;
        }

        // Step 7. Make and search the move
        do_move(pos, move, st, givesCheck, ss);

        value = -qsearch<nodeType>(pos, ss + 1, -beta, -alpha);
        undo_move(pos, move);

        assert(value > -VALUE_INFINITE && value < VALUE_INFINITE);

        // Step 8. Check for a new best move
        if (value > bestValue)
        {
            bestValue = value;

            if (value > alpha)
            {
                bestMove = move;

                // Update pv even in fail-high case
                if (PvNode)
                    ss->pv->update(move, (ss + 1)->pv);

                if (value < beta)  // Update alpha here!
                    alpha = value;
                else
                    break;  // Fail high
            }
        }
    }

    // Step 9. Check for mate and stalemate
    // All legal moves have been searched. A special case: if we are
    // in check and no legal moves were found, it is checkmate.
    if (!moveCount)
    {
        if (ss->inCheck)  // Checkmate!
        {
            assert(!MoveList<ALL>(pos).size());
            return mated_in(ss->ply);  // Plies to mate from the root
        }

        // Only check for stalemate under specific conditions
        Color us = pos.side_to_move();
        if (!(pawn_single_push_bb(us, pos.pieces(us, PAWN)) & ~pos.pieces())
            && !pos.non_pawn_material(us) && type_of(pos.captured_piece()) >= KNIGHT
            && !MoveList<ALL>(pos).size())
            bestValue = VALUE_DRAW;
    }

    if (!is_decisive(bestValue) && bestValue > beta)
        bestValue = (462 * bestValue + 562 * beta) / 1024;

    // Step 10. Save gathered info in transposition table. The static evaluation
    // is saved as it was before adjustment by correction history.
    ttWriter.write(posKey, value_to_tt(bestValue, ss->ply), pvHit,
                   bestValue >= beta ? BOUND_LOWER : BOUND_UPPER, DEPTH_QS, bestMove,
                   unadjustedStaticEval, TT.generation());

    // The search is now complete
    assert(-VALUE_INFINITE < bestValue && bestValue < VALUE_INFINITE);
    return bestValue;
}

int Search::Worker::reduction(bool i, Depth d, int mn) const {
    int reductionScale = reductions[d] * reductions[mn < MAX_MOVES ? mn : MAX_MOVES - 1];
    return reductionScale + !i * reductionScale * 197 / 512 + 948;
}

// Checks every 512 nodes whether the allotted time or node budget is used up.
// The first iteration is always completed so that there is a move to play.
void Search::Worker::check_time() {

    if (--callsCnt > 0)
        return;

    callsCnt = 512;

#ifdef SF_YIELD_HOOK
    // The application can pause the search here (to run it in time slices) and
    // ask it to stop. Declared in misc.h. A stop waits for the first iteration.
    const bool stopRequested = SF_YIELD_HOOK();
#else
    const bool stopRequested = false;
#endif

    if (rootDepth <= 1)
        return;

    if (stopRequested)
    {
        stop = true;
        return;
    }

    TimePoint elapsed = now() - startTime;

    if ((limits.movetime && elapsed >= limits.movetime) || (limits.nodes && nodes >= limits.nodes))
        stop = true;
}


// Evaluate the current position of the game tree, from the point of view of
// the side to move. As in Stockfish, the evaluation is damped when the 50-move
// counter grows, so that the engine tries to make progress.
Value Search::Worker::evaluate(const Position& pos) {
    Value v = Eval::evaluate(pos);

    v = v * (200 - pos.rule50_count()) / 200;

    return clamp(v, VALUE_TB_LOSS_IN_MAX_PLY + 1, VALUE_TB_WIN_IN_MAX_PLY - 1);
}

namespace {

// Adjusts a mate or TB score from "plies to mate from the root" to
// "plies to mate from the current position". Standard scores are unchanged.
// The function is called before storing a value in the transposition table.
Value value_to_tt(Value v, int ply) { return is_win(v) ? v + ply : is_loss(v) ? v - ply : v; }


// Inverse of value_to_tt(): it adjusts a mate or TB score from the transposition
// table (which refers to the plies to mate/be mated from current position) to
// "plies to mate/be mated (TB win/loss) from the root". However, to avoid
// potentially false mate or TB scores related to the 50 moves rule and the
// graph history interaction, we return the highest non-TB score instead.
Value value_from_tt(Value v, int ply, int r50c) {

    if (!is_valid(v))
        return VALUE_NONE;

    // Handle TB win or better
    if (is_win(v))
    {
        // Downgrade a potentially false mate score
        if (is_mate(v) && VALUE_MATE - v > 100 - r50c)
            return VALUE_TB_WIN_IN_MAX_PLY - 1;

        // Downgrade a potentially false TB score
        if (VALUE_TB - v > 100 - r50c)
            return VALUE_TB_WIN_IN_MAX_PLY - 1;

        return v - ply;
    }

    // Handle TB loss or worse
    if (is_loss(v))
    {
        // Downgrade a potentially false mate score
        if (is_mated(v) && VALUE_MATE + v > 100 - r50c)
            return VALUE_TB_LOSS_IN_MAX_PLY + 1;

        // Downgrade a potentially false TB score
        if (VALUE_TB + v > 100 - r50c)
            return VALUE_TB_LOSS_IN_MAX_PLY + 1;

        return v + ply;
    }

    return v;
}


// Updates stats at the end of search() when a bestMove is found
void update_all_stats(const Position& pos,
                      Stack*          ss,
                      Search::Worker& workerThread,
                      Move            bestMove,
                      SearchedList&   quietsSearched,
                      SearchedList&   capturesSearched,
                      Depth           depth,
                      Move            ttMove,
                      bool            PvNode) {
    SF_PROF(PROF_HISTORY);

    CapturePieceToHistory& captureHistory = workerThread.captureHistory;
    Piece                  movedPiece     = pos.moved_piece(bestMove);
    PieceType              capturedPiece;

    int bonus = (133 * depth - 81 < 1487 ? 133 * depth - 81 : 1487) + 364 * (bestMove == ttMove)
              + (ss - 1)->statScore / 28;
    int malus = 968 * depth - 235 < 2244 ? 968 * depth - 235 : 2244;

    if (!PvNode)
        // Important: don't remove the cast to a 64-bit number else the multiplication
        // can overflow on 32-bit platforms
        bonus += int(bonus * u64(quietsSearched.size() + capturesSearched.size()) / 256);

    if (!pos.capture_stage(bestMove))
    {
        update_quiet_histories(pos, workerThread, bestMove, bonus * 899 / 1024);
        update_refutations(pos, ss, workerThread, bestMove);

        // Decrease stats for all non-best quiet moves
        int actualMalus = malus * 1159 / 1024;
        for (Move move : quietsSearched)
        {
            actualMalus = actualMalus * 921 / 1024;
            update_quiet_histories(pos, workerThread, move, -actualMalus);
        }
    }
    else
    {
        // Increase stats for the best move in case it was a capture move
        capturedPiece = type_of(pos.piece_on(bestMove.to_sq()));
        captureHistory[movedPiece][bestMove.to_sq()][capturedPiece] << bonus * 1427 / 1024;
    }

    // Decrease stats for all non-best capture moves
    for (Move move : capturesSearched)
    {
        movedPiece    = pos.moved_piece(move);
        capturedPiece = type_of(pos.piece_on(move.to_sq()));
        captureHistory[movedPiece][move.to_sq()][capturedPiece] << -malus * 1489 / 1024;
    }
}


// Updates move sorting heuristics
void update_quiet_histories(const Position& pos, Search::Worker& workerThread, Move move, int bonus) {

    Color us = pos.side_to_move();
    workerThread.mainHistory[us][move.from_to()] << bonus;  // Untuned to prevent duplicate effort
}

// Remembers a quiet move that caused a cutoff as killer move of this ply and as
// counter move of the previous move
void update_refutations(const Position& pos, Stack* ss, Search::Worker& workerThread, Move move) {

    if (ss->killers[0] != move)
    {
        ss->killers[1] = ss->killers[0];
        ss->killers[0] = move;
    }

    if (((ss - 1)->currentMove).is_ok())
    {
        Square prevSq                                             = ((ss - 1)->currentMove).to_sq();
        workerThread.counterMoves[pos.piece_on(prevSq)][prevSq] = move;
    }
}

}  // namespace

// When playing with strength handicap, choose the best move among a set of
// RootMoves using a statistical rule dependent on 'level'.
// Idea by Heinz van Saanen.
Move Skill::pick_best(const RootMove* rootMoves, int multiPV) {
    static PRNG rng(u64(now()) * 2654435761ULL + 1);  // PRNG sequence should be non-deterministic

    // Ignore lines that were not searched (search stopped during the iteration)
    while (multiPV > 1 && rootMoves[multiPV - 1].score == -VALUE_INFINITE)
        --multiPV;

    Value topScore = rootMoves[0].score;
    Value minScore = rootMoves[0].score;
    for (int i = 1; i < multiPV; ++i)
    {
        topScore = topScore > rootMoves[i].score ? topScore : rootMoves[i].score;
        minScore = minScore < rootMoves[i].score ? minScore : rootMoves[i].score;
    }
    int    delta    = topScore - minScore < int(PawnValue) ? topScore - minScore : int(PawnValue);
    int    maxScore = -VALUE_INFINITE;
    int    weakness = 120 - 2 * level;

    // Choose best move. For each move score we add two terms dependent on
    // weakness. One is deterministic and bigger for weaker levels, and one
    // is random. Then we choose the move with the resulting highest score.
    for (int i = 0; i < multiPV; ++i)
    {
        // This is our magic formula
        int push = int(weakness * int(topScore - rootMoves[i].score)
                       + delta * (rng.rand<unsigned>() % int(weakness)))
                 / 128;

        if (rootMoves[i].score + push >= maxScore)
        {
            maxScore = rootMoves[i].score + push;
            best     = rootMoves[i].pv[0];
        }
    }

    return best;
}

}  // namespace Stockfish
