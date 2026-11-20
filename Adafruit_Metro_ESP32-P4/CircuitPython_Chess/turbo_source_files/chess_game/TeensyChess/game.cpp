// SPDX-FileCopyrightText: 2026 Kris Kasprzak
// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
// SPDX-License-Identifier: GPL-3.0-or-later
// Teensy Chess - the game being played: position, move history, notation and result

#include "game.h"

#include "src/engine/movegen.h"

using namespace Stockfish;

namespace {

const char *START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

// One StateInfo per played move, plus one for the start position. They hold the
// history needed for repetition detection, and live in the second RAM bank.
const int STATE_COUNT = 401;
#ifdef SF_ARENA_TABLES
StateInfo (*gameStates_ptr)[STATE_COUNT];  // set by the application, see misc.h
  #define gameStates (*gameStates_ptr)
#else
StateInfo gameStates[STATE_COUNT] SF_BIGMEM;
#endif

}  // namespace

Square displayTo(Move m) {
  Square from = m.from_sq(), to = m.to_sq();
  if (m.type_of() == CASTLING) return make_square(to > from ? FILE_G : FILE_C, rank_of(from));
  return to;
}

void ChessGame::reset() {
  moveCount = 0;
  position.set(START_FEN, &gameStates[0]);
}

bool ChessGame::setFen(const char *fen) {
  moveCount = 0;
  return position.set(fen, &gameStates[0]);
}

bool ChessGame::makeMove(Move m) {
  if (m == Move::none() || !MoveList<ALL>(position).contains(m)) return false;

  // When the history is full, restart it from the current position. Only the
  // ability to take back moves and to detect repetitions further back is lost.
  if (moveCount >= MAX_GAME_PLY) {
    char fen[100];
    position.fen(fen);
    moveCount = 0;
    position.set(fen, &gameStates[0]);
  }

  position.do_move(m, gameStates[moveCount + 1]);
  moves[moveCount++] = m;
  return true;
}

bool ChessGame::undoMove() {
  if (!moveCount) return false;
  position.undo_move(moves[--moveCount]);
  return true;
}

Bitboard ChessGame::targets(Square from) const {
  Bitboard b = 0;
  for (const Move &m : MoveList<ALL>(position))
    if (m.from_sq() == from) b |= displayTo(m);
  return b;
}

Move ChessGame::findMove(Square from, Square to, PieceType promo, bool &isPromotion) const {
  isPromotion = false;
  for (const Move &m : MoveList<ALL>(position)) {
    if (m.from_sq() != from || displayTo(m) != to) continue;
    if (m.type_of() == PROMOTION) {
      isPromotion = true;
      if (m.promotion_type() != promo) continue;
    }
    return m;
  }
  return Move::none();
}

void ChessGame::san(Move m, char *out) const {
  Position &p = const_cast<Position &>(position);  // do_move/undo_move restore it
  Square from = m.from_sq(), to = m.to_sq();
  PieceType pt = type_of(p.piece_on(from));
  char *s = out;

  if (m.type_of() == CASTLING) {
    const char *c = to > from ? "O-O" : "O-O-O";
    while (*c) *s++ = *c++;
  } else {
    bool capture = p.capture(m);

    if (pt != PAWN) {
      *s++ = " PNBRQK"[pt];

      // Disambiguate when another piece of the same type can go to the same square
      bool ambiguous = false, sameFile = false, sameRank = false;
      for (const Move &o : MoveList<ALL>(p)) {
        if (o == m || o.to_sq() != to || o.type_of() == CASTLING) continue;
        if (type_of(p.piece_on(o.from_sq())) != pt) continue;
        ambiguous = true;
        sameFile |= file_of(o.from_sq()) == file_of(from);
        sameRank |= rank_of(o.from_sq()) == rank_of(from);
      }
      if (ambiguous) {
        if (!sameFile)
          *s++ = char('a' + file_of(from));
        else if (!sameRank)
          *s++ = char('1' + rank_of(from));
        else {
          *s++ = char('a' + file_of(from));
          *s++ = char('1' + rank_of(from));
        }
      }
    } else if (capture)
      *s++ = char('a' + file_of(from));

    if (capture) *s++ = 'x';

    *s++ = char('a' + file_of(to));
    *s++ = char('1' + rank_of(to));

    if (m.type_of() == PROMOTION) {
      *s++ = '=';
      *s++ = " PNBRQK"[m.promotion_type()];
    }
  }

  // Check or mate
  StateInfo st;
  p.do_move(m, st);
  if (p.checkers()) *s++ = MoveList<ALL>(p).size() ? '+' : '#';
  p.undo_move(m);

  *s = '\0';
}

GameResult ChessGame::result() const {
  if (!MoveList<ALL>(position).size()) {
    if (!position.checkers()) return GameResult::Stalemate;
    return position.side_to_move() == WHITE ? GameResult::BlackMates : GameResult::WhiteMates;
  }

  if (position.rule50_count() >= 100) return GameResult::DrawFiftyMoves;

  // The same position for the third time (Stockfish marks it with a negative distance)
  if (position.state()->repetition < 0) return GameResult::DrawRepetition;

  // Not enough material to mate: no pawns, rooks or queens, and at most one minor
  // piece, or only bishops that all stand on squares of the same color
  if (!position.pieces(PAWN, ROOK, QUEEN)) {
    Bitboard minors = position.pieces(KNIGHT, BISHOP);
    const Bitboard dark = 0xAA55AA55AA55AA55ULL;
    Bitboard bishops = position.pieces(BISHOP);
    if (popcount(minors) <= 1) return GameResult::DrawMaterial;
    if (!position.pieces(KNIGHT) && (!(bishops & dark) || !(bishops & ~dark))) return GameResult::DrawMaterial;
  }

  return GameResult::Ongoing;
}

int ChessGame::materialPoints(Color c) const {
  return position.count<PAWN>(c) + 3 * position.count<KNIGHT>(c) + 3 * position.count<BISHOP>(c) +
         5 * position.count<ROOK>(c) + 9 * position.count<QUEEN>(c);
}
