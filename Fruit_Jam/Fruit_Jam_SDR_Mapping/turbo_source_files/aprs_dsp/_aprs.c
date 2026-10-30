// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Native CircuitPython module wrapping aprs_core.h.
//   STATE_BYTES                     size of the state bytearray
//   reset(state)
//   feed(pcm, state) -> frames queued (pcm: 32 kHz s16 bytes, as _ham_dsp NFM gives)
//   pop(state, out) -> length of the oldest frame copied to out (no FCS), 0 if none
//   stats(state) -> (frames, dupes, crc_fail, dropped, flags, dcd, level)
//   address(buffer) -> address of the buffer's data (where it is: SRAM or PSRAM)
// The interface is integers only: this firmware is built with the softfp
// ABI, so float arguments and results would not cross the call boundary
// correctly from a hard-float module.
#include "py/dynruntime.h"
#include "aprs_core.h"

static int bytes_type(int t) { return t == 'B' || t == 'b' || t == 'h' || t == BYTEARRAY_TYPECODE; }

static aprs_state *get_state(mp_obj_t obj) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(st.typecode) || st.len != APRS_STATE_BYTES || ((uintptr_t)st.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("state must be an aligned bytearray(STATE_BYTES)"));
    aprs_state *s = st.buf;
    if (s->magic == 0) aprs_reset(s);
    if (s->magic != APRS_MAGIC || s->hd >= APRS_DEC_TAPS || s->cor_taps < 4 || s->cor_taps > APRS_COR_MAX || s->hc >= s->cor_taps
            || s->pre_taps > APRS_PRE_MAX || (s->pre_taps && s->hp >= s->pre_taps) || s->phase > 1
            || s->q_head >= APRS_QUEUE || s->q_count > APRS_QUEUE || s->recent_head >= APRS_RECENT)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid APRS state; reset() it"));
    for (int i = 0; i < APRS_SLICERS; i++)
        if (s->sl[i].len > APRS_MAX_FRAME || s->sl[i].olen > 8)
            mp_raise_ValueError(MP_ERROR_TEXT("invalid APRS state; reset() it"));
    return s;
}

static mp_obj_t reset(mp_obj_t state_obj) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(state_obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(st.typecode) || st.len != APRS_STATE_BYTES || ((uintptr_t)st.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("state must be an aligned bytearray(STATE_BYTES)"));
    aprs_reset(st.buf);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(reset_obj, reset);

static mp_obj_t feed(mp_obj_t pcm_obj, mp_obj_t state_obj) {
    mp_buffer_info_t pcm;
    mp_get_buffer_raise(pcm_obj, &pcm, MP_BUFFER_READ);
    if (!bytes_type(pcm.typecode) || (pcm.len & 1))
        mp_raise_ValueError(MP_ERROR_TEXT("PCM must be 16-bit samples in a byte buffer"));
    aprs_state *s = get_state(state_obj);
    return mp_obj_new_int_from_uint(aprs_feed(s, pcm.buf, pcm.len));
}
static MP_DEFINE_CONST_FUN_OBJ_2(feed_obj, feed);

static mp_obj_t pop(mp_obj_t state_obj, mp_obj_t out_obj) {
    aprs_state *s = get_state(state_obj);
    mp_buffer_info_t out;
    mp_get_buffer_raise(out_obj, &out, MP_BUFFER_WRITE);
    if (!bytes_type(out.typecode) || out.typecode == 'h')
        mp_raise_ValueError(MP_ERROR_TEXT("out must be a bytearray"));
    return mp_obj_new_int_from_uint(aprs_pop(s, out.buf, out.len, NULL));
}
static MP_DEFINE_CONST_FUN_OBJ_2(pop_obj, pop);

static mp_obj_t stats(mp_obj_t state_obj) {
    aprs_state *s = get_state(state_obj);
    mp_obj_t r[7] = {
        mp_obj_new_int_from_uint(s->frames), mp_obj_new_int_from_uint(s->dupes),
        mp_obj_new_int_from_uint(s->crc_fail), mp_obj_new_int_from_uint(s->dropped),
        mp_obj_new_int_from_uint(s->flags), mp_obj_new_int_from_uint(aprs_dcd(s)),
        mp_obj_new_int_from_uint((mp_uint_t)s->level),
    };
    return mp_obj_new_tuple(7, r);
}
static MP_DEFINE_CONST_FUN_OBJ_1(stats_obj, stats);

static mp_obj_t address(mp_obj_t obj) {
    mp_buffer_info_t b;
    mp_get_buffer_raise(obj, &b, MP_BUFFER_READ);
    return mp_obj_new_int_from_uint((uintptr_t)b.buf);
}
static MP_DEFINE_CONST_FUN_OBJ_1(address_obj, address);

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY
    mp_store_global(MP_QSTR_STATE_BYTES, MP_OBJ_NEW_SMALL_INT(APRS_STATE_BYTES));
    mp_store_global(MP_QSTR_reset, MP_OBJ_FROM_PTR(&reset_obj));
    mp_store_global(MP_QSTR_feed, MP_OBJ_FROM_PTR(&feed_obj));
    mp_store_global(MP_QSTR_pop, MP_OBJ_FROM_PTR(&pop_obj));
    mp_store_global(MP_QSTR_stats, MP_OBJ_FROM_PTR(&stats_obj));
    mp_store_global(MP_QSTR_address, MP_OBJ_FROM_PTR(&address_obj));
    MP_DYNRUNTIME_INIT_EXIT
}
