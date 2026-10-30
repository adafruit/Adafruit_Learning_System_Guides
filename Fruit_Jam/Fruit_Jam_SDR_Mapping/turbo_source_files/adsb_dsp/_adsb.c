// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Native CircuitPython module wrapping modes_core.h.
//   STATE_BYTES, RECORD             sizes of the state bytearray and of an output record
//   reset(state)
//   decode(iq, state, out, now) -> records written to out (iq: one 2 MS/s
//                                  snapshot of 8-bit I/Q; now: seconds, for
//                                  the known-aircraft table)
//   settings(state, pulse_x16, quiet_x16)   detection thresholds (see modes_core.h)
//   stats(state) -> (snapshots, samples, candidates, demods, accepted, df17,
//                    df11, ap, fixed, crc_fail, ap_unknown, fixed2, noise_x16)
//   address(buffer) -> address of the buffer's data (where it is: SRAM or PSRAM)
// The interface is integers only: this firmware is built with the softfp
// ABI, so float arguments and results would not cross the call boundary
// correctly from a hard-float module.
#include "py/dynruntime.h"
#include "modes_core.h"

static int bytes_type(int t) { return t == 'B' || t == 'b' || t == BYTEARRAY_TYPECODE; }

static modes_state *get_state(mp_obj_t obj) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(st.typecode) || st.len != MODES_STATE_BYTES || ((uintptr_t)st.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("state must be an aligned bytearray(STATE_BYTES)"));
    modes_state *s = st.buf;
    if (s->magic == 0) modes_reset(s);
    if (s->magic != MODES_MAGIC)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid ADS-B state; reset() it"));
    return s;
}

static mp_obj_t reset(mp_obj_t state_obj) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(state_obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(st.typecode) || st.len != MODES_STATE_BYTES || ((uintptr_t)st.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("state must be an aligned bytearray(STATE_BYTES)"));
    modes_reset(st.buf);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(reset_obj, reset);

static mp_obj_t decode(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t iq, out;
    mp_get_buffer_raise(args[0], &iq, MP_BUFFER_READ);
    if (!bytes_type(iq.typecode))
        mp_raise_ValueError(MP_ERROR_TEXT("I/Q must be bytes"));
    modes_state *s = get_state(args[1]);
    mp_get_buffer_raise(args[2], &out, MP_BUFFER_WRITE);
    if (!bytes_type(out.typecode))
        mp_raise_ValueError(MP_ERROR_TEXT("out must be a bytearray"));
    uint32_t now = mp_obj_get_int_truncated(args[3]);
    return MP_OBJ_NEW_SMALL_INT(modes_decode(s, iq.buf, iq.len, out.buf, out.len, now));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(decode_obj, 4, 4, decode);

static mp_obj_t settings(mp_obj_t state_obj, mp_obj_t pulse_obj, mp_obj_t quiet_obj) {
    modes_state *s = get_state(state_obj);
    mp_int_t p = mp_obj_get_int(pulse_obj), q = mp_obj_get_int(quiet_obj);
    if (p < 16 || p > 1600 || q < 1 || q > 16)
        mp_raise_ValueError(MP_ERROR_TEXT("pulse_x16 16..1600, quiet_x16 1..16"));
    s->pulse_ratio_x16 = p;
    s->quiet_ratio_x16 = q;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(settings_obj, settings);

static mp_obj_t stats(mp_obj_t state_obj) {
    modes_state *s = get_state(state_obj);
    const uint32_t v[13] = {s->snapshots, s->samples, s->candidates, s->demods, s->accepted, s->df17,
                            s->df11, s->ap, s->fixed, s->crc_fail, s->ap_unknown, s->fixed2, s->noise_x16};
    mp_obj_t r[13];
    for (int i = 0; i < 13; i++)
        r[i] = mp_obj_new_int_from_uint(v[i]);
    return mp_obj_new_tuple(13, r);
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
    mp_store_global(MP_QSTR_STATE_BYTES, MP_OBJ_NEW_SMALL_INT(MODES_STATE_BYTES));
    mp_store_global(MP_QSTR_RECORD, MP_OBJ_NEW_SMALL_INT(MODES_RECORD));
    mp_store_global(MP_QSTR_reset, MP_OBJ_FROM_PTR(&reset_obj));
    mp_store_global(MP_QSTR_decode, MP_OBJ_FROM_PTR(&decode_obj));
    mp_store_global(MP_QSTR_settings, MP_OBJ_FROM_PTR(&settings_obj));
    mp_store_global(MP_QSTR_stats, MP_OBJ_FROM_PTR(&stats_obj));
    mp_store_global(MP_QSTR_address, MP_OBJ_FROM_PTR(&address_obj));
    MP_DYNRUNTIME_INIT_EXIT
}
