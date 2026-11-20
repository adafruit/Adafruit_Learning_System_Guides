// SPDX-FileCopyrightText: 2026 Kris Kasprzak
// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: GPL-3.0-or-later

/*
  Teensy Chess - Stockfish port for Teensy 4.0
  Copyright (C) 2026 the Teensy Chess authors

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
*/

#include "engine.h"

#include <new>

#include "attacks.h"
#include "evaluate.h"
#include "movegen.h"
#include "tt.h"

namespace Stockfish::Engine {

namespace {

// The worker holds the histories and the root move list (about 64 KB). It lives in
// the second RAM bank so the fast first bank keeps room for the recursive search
// stack (about 3 KB per ply).
#if defined(SF_ARENA_TABLES)
// Memory set by the application (see misc.h), constructed by init()
Search::Worker* worker_ptr;
    #define worker (*worker_ptr)
#elif defined(SF_NO_STATIC_CONSTRUCTORS)
// Environments that run no static constructors: raw storage, constructed by init()
alignas(Search::Worker) unsigned char workerStorage[sizeof(Search::Worker)];
    #define worker (*reinterpret_cast<Search::Worker*>(workerStorage))
#else
Search::Worker worker SF_BIGMEM;
#endif

}

void init() {
#if defined(SF_ARENA_TABLES)
    new (worker_ptr) Search::Worker();
#elif defined(SF_NO_STATIC_CONSTRUCTORS)
    new (workerStorage) Search::Worker();
#endif
    Attacks::init();
    Position::init();
    Eval::init();
    Search::init();
    new_game();
}

void new_game() {
    TT.clear();
    worker.clear();
}

Search::Result think(Position& pos, const Search::LimitsType& limits, int skillLevel) {
    return worker.start_searching(pos, limits, skillLevel);
}

u64 perft(Position& pos, Depth depth) {

    StateInfo st;
    u64       nodes = 0;

    for (const auto& m : MoveList<ALL>(pos))
    {
        if (depth <= 1)
            nodes++;
        else
        {
            pos.do_move(m, st);
            nodes += depth == 2 ? MoveList<ALL>(pos).size() : perft(pos, depth - 1);
            pos.undo_move(m);
        }
    }
    return nodes;
}

void move_to_uci(Move m, char* out) {

    if (m == Move::none())
    {
        out[0] = '\0';
        return;
    }

    Square from = m.from_sq();
    Square to   = m.to_sq();

    // Castling is encoded as "king captures rook"
    if (m.type_of() == CASTLING)
        to = make_square(to > from ? FILE_G : FILE_C, rank_of(from));

    *out++ = char('a' + file_of(from));
    *out++ = char('1' + rank_of(from));
    *out++ = char('a' + file_of(to));
    *out++ = char('1' + rank_of(to));

    if (m.type_of() == PROMOTION)
        *out++ = " pnbrqk"[m.promotion_type()];

    *out = '\0';
}

}  // namespace Stockfish::Engine
