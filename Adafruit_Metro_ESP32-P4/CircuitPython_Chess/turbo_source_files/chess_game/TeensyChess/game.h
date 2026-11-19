// SPDX-FileCopyrightText: 2026 Kris Kasprzak
// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
// SPDX-License-Identifier: GPL-3.0-or-later
// Teensy Chess - the game being played: position, move history, notation and result

#pragma once

#if defined(ARDUINO)
#include <Arduino.h>
#else
#include <cstdint>
#endif

#include "src/engine/position.h"

using Stockfish::Bitboard;
using Stockfish::Color;
using Stockfish::Move;
using Stockfish::Piece;
using Stockfish::PieceType;
using Stockfish::Position;
using Stockfish::Square;

enum class GameResult : uint8_t {
  Ongoing,
  WhiteMates,
  BlackMates,
  Stalemate,
  DrawFiftyMoves,
  DrawRepetition,
  DrawMaterial
};

class ChessGame {
 public:
  // Start a new game from the initial position
  void reset();

  // Start from a FEN position with an empty history. Returns false if the FEN
  // is not valid (the position is then undefined: set another one).
  bool setFen(const char *fen);

  Position &pos() { return position; }
  const Position &pos() const { return position; }

  Color sideToMove() const { return position.side_to_move(); }
  int plyCount() const { return moveCount; }
  Move lastMove() const { return moveCount ? moves[moveCount - 1] : Move::none(); }

  // Plays a legal move. Returns false if the move is not legal.
  bool makeMove(Move m);

  // Takes back the last move. Returns false if there is nothing to take back.
  bool undoMove();

  // Squares the piece on 'from' can legally move to. Castling is shown on the
  // king's destination square (g1/c1), not on the rook.
  Bitboard targets(Square from) const;

  // Finds the legal move from 'from' to the tapped square 'to'. For promotions
  // 'promo' chooses the piece; isPromotion tells the caller a choice is needed.
  Move findMove(Square from, Square to, PieceType promo, bool &isPromotion) const;

  // Standard algebraic notation (e.g. "Nf3", "exd5", "O-O", "e8=Q+") of a legal
  // move in the current position
  void san(Move m, char *out) const;

  GameResult result() const;

  // Material points (pawn 1, knight 3, bishop 3, rook 5, queen 9)
  int materialPoints(Color c) const;

 private:
  static const int MAX_GAME_PLY = 400;

  Position position;
  Move moves[MAX_GAME_PLY];
  int moveCount = 0;
};

// The square the king lands on for a move (castling is encoded as "king takes rook")
Square displayTo(Move m);
