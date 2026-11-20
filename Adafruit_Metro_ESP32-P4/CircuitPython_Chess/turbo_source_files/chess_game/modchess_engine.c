// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
// SPDX-License-Identifier: GPL-3.0-or-later
// _chess_engine: CircuitPython native module around the chess engine C API (tf_api.h).
// Used by chess_ctrl.py in the app folder (chess_game/). Squares are 0..63
// (a1 = 0, h8 = 63), moves are UCI.

#include "py/dynruntime.h"

#include "tf_api.h"

#define PROMOTION_NEEDED 1

static void check(int err) {
    if (err >= 0) {
        return;
    }
    if (err == TF_ERR_BUSY) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("engine is thinking"));
    }
    if (err == TF_ERR_INIT) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("call init() first"));
    }
    if (err == TF_ERR_ILLEGAL) {
        mp_raise_ValueError(MP_ERROR_TEXT("illegal move"));
    }
    mp_raise_ValueError(MP_ERROR_TEXT("bad argument"));
}

static mp_obj_t new_str(const char *s) {
    size_t n = 0;
    while (s[n]) {
        n++;
    }
    return mp_obj_new_str(s, n);
}

// tables_size() -> bytes of init()'s memory used by tables other than the TT
static mp_obj_t tables_size_(void) {
    return mp_obj_new_int_from_uint(tf_tables_bytes());
}
static MP_DEFINE_CONST_FUN_OBJ_0(tables_size_obj, tables_size_);

// init(mem: bytearray, cpu_hz: int, tt_max_bytes=0) -> TT clusters
// mem holds the engine's tables (tables_size()) and the TT (the rest).
static mp_obj_t tf_init_(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t mem;
    mp_get_buffer_raise(args[0], &mem, MP_BUFFER_RW);
    uint32_t hz = (uint32_t)mp_obj_get_int_truncated(args[1]);
    uint32_t tt_max = n_args > 2 ? (uint32_t)mp_obj_get_int_truncated(args[2]) : 0;
    int r = tf_init(mem.buf, (uint32_t)mem.len, hz / 1000, tt_max);
    check(r);
    // Keep the memory alive for as long as the module is
    mp_store_global(MP_QSTR__mem, args[0]);
    return mp_obj_new_int(r);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(init_obj, 2, 3, tf_init_);

static mp_obj_t new_game_(void) {
    check(tf_thinking() ? TF_ERR_BUSY : 0);
    tf_new_game();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(new_game_obj, new_game_);

static mp_obj_t reset_(void) {
    check(tf_reset());
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(reset_obj, reset_);

static mp_obj_t set_fen_(mp_obj_t fen_obj) {
    check(tf_set_fen(mp_obj_str_get_str(fen_obj)));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(set_fen_obj, set_fen_);

static mp_obj_t fen_(void) {
    char buf[128];
    check(tf_fen(buf, sizeof(buf)));
    return new_str(buf);
}
static MP_DEFINE_CONST_FUN_OBJ_0(fen_obj, fen_);

// board(buf: bytearray of 64): piece code per square
static mp_obj_t board_(mp_obj_t buf_obj) {
    mp_buffer_info_t b;
    mp_get_buffer_raise(buf_obj, &b, MP_BUFFER_WRITE);
    if (b.len < 64) {
        check(TF_ERR_ARG);
    }
    check(tf_board((uint8_t *)b.buf));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(board_obj, board_);

static mp_obj_t side_to_move_(void) {
    int r = tf_side_to_move();
    check(r);
    return mp_obj_new_int(r);
}
static MP_DEFINE_CONST_FUN_OBJ_0(side_to_move_obj, side_to_move_);

static mp_obj_t ply_(void) {
    int r = tf_ply();
    check(r);
    return mp_obj_new_int(r);
}
static MP_DEFINE_CONST_FUN_OBJ_0(ply_obj, ply_);

static mp_obj_t push_(mp_obj_t uci_obj) {
    check(tf_push(mp_obj_str_get_str(uci_obj)));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(push_obj, push_);

// pop() -> bool (False when there is nothing to take back)
static mp_obj_t pop_(void) {
    int r = tf_pop();
    if (r == TF_ERR_ILLEGAL) {
        return mp_const_false;
    }
    check(r);
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_0(pop_obj, pop_);

static mp_obj_t last_move_(void) {
    char buf[8];
    check(tf_last_move(buf, sizeof(buf)));
    return new_str(buf);
}
static MP_DEFINE_CONST_FUN_OBJ_0(last_move_obj, last_move_);

// targets(square) -> tuple of destination squares
static mp_obj_t targets_(mp_obj_t sq_obj) {
    uint32_t half[2];
    check(tf_targets(mp_obj_get_int(sq_obj), &half[0], &half[1]));
    mp_obj_t items[64];
    size_t n = 0;
    for (int s = 0; s < 64; s++) {
        if (half[s >> 5] & (1u << (s & 31))) {
            items[n++] = mp_obj_new_int(s);
        }
    }
    return mp_obj_new_tuple(n, items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(targets_obj, targets_);

// find_move(from, to, promo="") -> uci str, None if illegal, 1 if a promotion
// piece must be chosen first ("q", "r", "b" or "n")
static mp_obj_t find_move_(size_t n_args, const mp_obj_t *args) {
    char promo = 0;
    if (n_args > 2) {
        const char *p = mp_obj_str_get_str(args[2]);
        promo = p[0];
    }
    char buf[8];
    int r = tf_find_move(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), promo, buf, sizeof(buf));
    if (r == TF_ERR_ILLEGAL) {
        return mp_const_none;
    }
    check(r);
    if (r == PROMOTION_NEEDED) {
        return mp_obj_new_int(PROMOTION_NEEDED);
    }
    return new_str(buf);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(find_move_obj, 2, 3, find_move_);

static mp_obj_t san_(mp_obj_t uci_obj) {
    char buf[16];
    check(tf_san(mp_obj_str_get_str(uci_obj), buf, sizeof(buf)));
    return new_str(buf);
}
static MP_DEFINE_CONST_FUN_OBJ_1(san_obj, san_);

static mp_obj_t result_(void) {
    int r = tf_result();
    check(r);
    return mp_obj_new_int(r);
}
static MP_DEFINE_CONST_FUN_OBJ_0(result_obj, result_);

static mp_obj_t material_(mp_obj_t color_obj) {
    int r = tf_material(mp_obj_get_int(color_obj));
    check(r);
    return mp_obj_new_int(r);
}
static MP_DEFINE_CONST_FUN_OBJ_1(material_obj, material_);

static mp_obj_t check_square_(void) {
    check(tf_thinking() ? TF_ERR_BUSY : 0);
    return mp_obj_new_int(tf_check_square());
}
static MP_DEFINE_CONST_FUN_OBJ_0(check_square_obj, check_square_);

static mp_obj_t perft_(mp_obj_t depth_obj) {
    check(tf_thinking() ? TF_ERR_BUSY : 0);
    return mp_obj_new_int_from_uint(tf_perft(mp_obj_get_int(depth_obj)));
}
static MP_DEFINE_CONST_FUN_OBJ_1(perft_obj, perft_);

// think_start(stack: bytearray, level, movetime_ms, depth=0, nodes=0)
static mp_obj_t think_start_(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(args[0], &st, MP_BUFFER_RW);
    int depth = n_args > 3 ? mp_obj_get_int(args[3]) : 0;
    uint32_t nodes = n_args > 4 ? (uint32_t)mp_obj_get_int_truncated(args[4]) : 0;
    check(tf_think_start(st.buf, (uint32_t)st.len, mp_obj_get_int(args[1]), mp_obj_get_int(args[2]),
        depth, nodes));
    // The search runs on this buffer: keep it alive until the next search
    mp_store_global(MP_QSTR__stack, args[0]);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(think_start_obj, 3, 5, think_start_);

// think_step(budget_ms) -> None while thinking, else (best, ponder, score, depth, nodes, ms)
static mp_obj_t think_step_(mp_obj_t budget_obj) {
    int r = tf_think_step(mp_obj_get_int(budget_obj));
    check(r);
    if (r == 0) {
        return mp_const_none;
    }
    tf_result_t res;
    check(tf_think_result(&res));
    mp_obj_t items[6] = {
        new_str(res.best),
        new_str(res.ponder),
        mp_obj_new_int(res.score),
        mp_obj_new_int(res.depth),
        mp_obj_new_int_from_uint(res.nodes),
        mp_obj_new_int_from_uint(res.time_ms),
    };
    return mp_obj_new_tuple(6, items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(think_step_obj, think_step_);

static mp_obj_t think_stop_(void) {
    tf_think_stop();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(think_stop_obj, think_stop_);

static mp_obj_t thinking_(void) {
    return tf_thinking() ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_0(thinking_obj, thinking_);

static mp_obj_t stack_peak_(void) {
    return mp_obj_new_int_from_uint(tf_stack_peak());
}
static MP_DEFINE_CONST_FUN_OBJ_0(stack_peak_obj, stack_peak_);

#ifdef TF_DEBUG_STEPS
int tf_debug_step(int step, void *mem, uint32_t mem_bytes);
static mp_obj_t debug_step_(mp_obj_t step_obj, mp_obj_t mem_obj) {
    mp_buffer_info_t mem;
    mp_get_buffer_raise(mem_obj, &mem, MP_BUFFER_RW);
    return mp_obj_new_int(tf_debug_step(mp_obj_get_int(step_obj), mem.buf, (uint32_t)mem.len));
}
static MP_DEFINE_CONST_FUN_OBJ_2(debug_step_obj, debug_step_);
#endif

#ifdef TF_PROFILE
int tf_prof_read(uint64_t *out, int reset);
// _prof(buf, reset): fills buf with uint64s, see tf_prof_read()
static mp_obj_t prof_(mp_obj_t buf_obj, mp_obj_t reset_obj) {
    mp_buffer_info_t buf;
    mp_get_buffer_raise(buf_obj, &buf, MP_BUFFER_RW);
    uint64_t tmp[3 * 32 + 2];
    int n = tf_prof_read(tmp, mp_obj_is_true(reset_obj));
    size_t bytes = ((size_t)n * 3 + 2) * 8;
    if (buf.len < bytes) {
        mp_raise_ValueError(MP_ERROR_TEXT("buffer too small"));
    }
    uint8_t *dst = buf.buf;
    const uint8_t *src = (const uint8_t *)tmp;
    for (size_t i = 0; i < bytes; i++) {
        dst[i] = src[i];
    }
    return mp_obj_new_int(n);
}
static MP_DEFINE_CONST_FUN_OBJ_2(prof_obj, prof_);
#endif

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY

    mp_store_global(MP_QSTR_tables_size, MP_OBJ_FROM_PTR(&tables_size_obj));
    mp_store_global(MP_QSTR_init, MP_OBJ_FROM_PTR(&init_obj));
    mp_store_global(MP_QSTR_new_game, MP_OBJ_FROM_PTR(&new_game_obj));
    mp_store_global(MP_QSTR_reset, MP_OBJ_FROM_PTR(&reset_obj));
    mp_store_global(MP_QSTR_set_fen, MP_OBJ_FROM_PTR(&set_fen_obj));
    mp_store_global(MP_QSTR_fen, MP_OBJ_FROM_PTR(&fen_obj));
    mp_store_global(MP_QSTR_board, MP_OBJ_FROM_PTR(&board_obj));
    mp_store_global(MP_QSTR_side_to_move, MP_OBJ_FROM_PTR(&side_to_move_obj));
    mp_store_global(MP_QSTR_ply, MP_OBJ_FROM_PTR(&ply_obj));
    mp_store_global(MP_QSTR_push, MP_OBJ_FROM_PTR(&push_obj));
    mp_store_global(MP_QSTR_pop, MP_OBJ_FROM_PTR(&pop_obj));
    mp_store_global(MP_QSTR_last_move, MP_OBJ_FROM_PTR(&last_move_obj));
    mp_store_global(MP_QSTR_targets, MP_OBJ_FROM_PTR(&targets_obj));
    mp_store_global(MP_QSTR_find_move, MP_OBJ_FROM_PTR(&find_move_obj));
    mp_store_global(MP_QSTR_san, MP_OBJ_FROM_PTR(&san_obj));
    mp_store_global(MP_QSTR_result, MP_OBJ_FROM_PTR(&result_obj));
    mp_store_global(MP_QSTR_material, MP_OBJ_FROM_PTR(&material_obj));
    mp_store_global(MP_QSTR_check_square, MP_OBJ_FROM_PTR(&check_square_obj));
    mp_store_global(MP_QSTR_perft, MP_OBJ_FROM_PTR(&perft_obj));
    mp_store_global(MP_QSTR_think_start, MP_OBJ_FROM_PTR(&think_start_obj));
    mp_store_global(MP_QSTR_think_step, MP_OBJ_FROM_PTR(&think_step_obj));
    mp_store_global(MP_QSTR_think_stop, MP_OBJ_FROM_PTR(&think_stop_obj));
    mp_store_global(MP_QSTR_thinking, MP_OBJ_FROM_PTR(&thinking_obj));
    mp_store_global(MP_QSTR_stack_peak, MP_OBJ_FROM_PTR(&stack_peak_obj));
    #ifdef TF_PROFILE
    mp_store_global(MP_QSTR__prof, MP_OBJ_FROM_PTR(&prof_obj));
    #endif
    #ifdef TF_DEBUG_STEPS
    mp_store_global(MP_QSTR__debug_step, MP_OBJ_FROM_PTR(&debug_step_obj));
    #endif

    MP_DYNRUNTIME_INIT_EXIT
}
