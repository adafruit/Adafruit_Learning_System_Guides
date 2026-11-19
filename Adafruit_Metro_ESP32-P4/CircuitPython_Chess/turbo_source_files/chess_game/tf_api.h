// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
// SPDX-License-Identifier: GPL-3.0-or-later
// Chess engine C API (tf = TeensyFish, the engine it wraps): the game and the engine behind a plain C interface, used by the
// CircuitPython native module (modchess_engine.c) and by the host ctypes library.
//
// Squares are 0..63 (a1 = 0, b1 = 1, ..., h8 = 63). Moves are UCI strings
// ("e2e4", "e1g1" for castling, "e7e8q" for a promotion).
//
// The search runs as a coroutine on a caller-supplied stack: tf_think_start()
// prepares it and each tf_think_step() runs it for a time slice. While a search
// is in progress (tf_thinking() != 0) the game must not be read or changed: the
// search works on the game's position in place. The game functions return
// TF_ERR_BUSY (or do nothing) in that state.

#ifndef TF_API_H
#define TF_API_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TF_OK          0
#define TF_ERR_BUSY   -1   // a search is in progress
#define TF_ERR_ARG    -2   // bad argument (square, FEN, buffer too small)
#define TF_ERR_INIT   -3   // tf_init() not called or failed
#define TF_ERR_ILLEGAL -4  // not a legal move

// Results of tf_result()
#define TF_ONGOING          0
#define TF_WHITE_MATES      1
#define TF_BLACK_MATES      2
#define TF_STALEMATE        3
#define TF_DRAW_FIFTY       4
#define TF_DRAW_REPETITION  5
#define TF_DRAW_MATERIAL    6

// tf_board() piece codes: 0 empty, 1..6 white P N B R Q K, 9..14 black P N B R Q K
// (Stockfish's Piece values)

// Bytes of the tables carved from the start of tf_init()'s memory (about 340 KB)
uint32_t tf_tables_bytes(void);

// Sets up the engine in mem: its large tables (tf_tables_bytes()) and, in the
// rest, the transposition table (at least 32 KB). Starts a new game.
// cycles_per_ms is the rate of the CPU cycle counter (CPU MHz x 1000) on the
// board; ignored on the host. Returns the number of TT clusters (32 bytes each)
// or a negative error. Calling it again must pass the same memory.
// tt_max_bytes > 0 limits the table (e.g. 196608 for the Teensy's 6144 clusters).
int tf_init(void *mem, uint32_t mem_bytes, uint32_t cycles_per_ms, uint32_t tt_max_bytes);

// Clears the hash table and the search histories (call for a new game)
void tf_new_game(void);

// Game. All return TF_OK or a negative error unless stated.
int tf_reset(void);                     // start position, empty history
int tf_set_fen(const char *fen);        // position from FEN, empty history
int tf_fen(char *out, int len);         // current position as FEN
int tf_board(uint8_t *out64);           // piece code per square
int tf_side_to_move(void);              // 0 white, 1 black
int tf_ply(void);                       // moves played since reset/set_fen
int tf_push(const char *uci);           // play a move
int tf_pop(void);                       // take back the last move
int tf_last_move(char *out, int len);   // UCI of the last move ("" if none)
// Legal destinations of the piece on 'from' as a 64-bit mask (castling on the
// king's destination square), split in two halves.
int tf_targets(int from, uint32_t *lo, uint32_t *hi);
// The move from 'from' to 'to' as UCI in out. promo: 0 or one of "nbrq".
// Returns TF_OK, TF_ERR_ILLEGAL, or 1 when it is a promotion and promo is 0.
int tf_find_move(int from, int to, char promo, char *out, int len);
int tf_san(const char *uci, char *out, int len);  // SAN of a legal move ("Nf3", "O-O", "e8=Q#")
int tf_result(void);                    // TF_ONGOING or one of the results above
int tf_material(int color);             // pawn 1, knight 3, bishop 3, rook 5, queen 9
int tf_check_square(void);              // square of the king in check, or -1
uint32_t tf_perft(int depth);           // leaf nodes from the current position

// Search. level 0..20 (20 = full strength); movetime_ms, depth and nodes are
// limits (0 = none). stack_mem must stay valid until the search has finished.
int tf_think_start(void *stack_mem, uint32_t stack_bytes, int level, int movetime_ms, int depth,
                   uint32_t nodes);
// Runs the search for about budget_ms. Returns 0 while it is still running, 1 when
// it has finished (then call tf_think_result), or a negative error.
int tf_think_step(int budget_ms);
// Asks the search to finish with the best move so far (after its first iteration)
void tf_think_stop(void);
int tf_thinking(void);
typedef struct {
    char     best[6];
    char     ponder[6];
    int32_t  score;     // centipawn-like units from the side to move's view; mates near +-32000
    int32_t  depth;
    uint32_t nodes;
    uint32_t time_ms;
} tf_result_t;
int tf_think_result(tf_result_t *r);
// Bytes of the search stack touched by the last finished search
uint32_t tf_stack_peak(void);

#ifdef __cplusplus
}
#endif

#endif  // TF_API_H
