// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// Native CircuitPython module wrapping ham_core.h.
//   process(iq, pcm, state) -> bytes written (2 per 8 I/Q samples)
//   configure(state, mode, offset_hz, squelch_milli=0, flags=0)
//   status(state) -> (channel_power_q16, squelch_noise_q16, squelch_open)
// The interface is integers only: this firmware is built with the softfp
// ABI, so float arguments and results would not cross the call boundary
// correctly from a hard-float module.
#include "py/dynruntime.h"
#include "ham_core.h"

static int bytes_type(int t) { return t == 'B' || t == 'b' || t == BYTEARRAY_TYPECODE; }
static int overlaps(const void *a, size_t al, const void *b, size_t bl) {
    if (!al || !bl) return 0;
    uintptr_t x = (uintptr_t)a, y = (uintptr_t)b;
    return x <= y ? y - x < al : x - y < bl;
}

static ham_state *get_state(mp_obj_t obj) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(st.typecode) || st.len != HAM_STATE_BYTES || ((uintptr_t)st.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("state must be an aligned bytearray(8192)"));
    ham_state *s = st.buf;
    if (s->magic == 0) ham_reset(s, HAM_NFM);
    if (s->magic != HAM_MAGIC || s->mode >= HAM_MODES || s->h1 >= HAM_F1_TAPS || s->p1 >= 8
            || s->hn >= HAM_FNFM_TAPS || s->h2 >= HAM_F2_TAPS || s->p2 >= 4
            || s->hc >= HAM_FSSB_TAPS || s->ha >= HAM_AGC_DELAY || s->hint >= HAM_FINT_TAPS / 4)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid DSP state; replace with bytearray(8192)"));
    return s;
}

static mp_obj_t process(mp_obj_t iq_obj, mp_obj_t pcm_obj, mp_obj_t state_obj) {
    mp_buffer_info_t iq, pcm, st;
    mp_get_buffer_raise(iq_obj, &iq, MP_BUFFER_READ);
    mp_get_buffer_raise(pcm_obj, &pcm, MP_BUFFER_WRITE);
    mp_get_buffer_raise(state_obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(iq.typecode) || !bytes_type(pcm.typecode))
        mp_raise_ValueError(MP_ERROR_TEXT("byte buffers required"));
    if ((iq.len & 1) || iq.len > 65536)
        mp_raise_ValueError(MP_ERROR_TEXT("IQ length must be even and <= 65536"));
    if (overlaps(iq.buf, iq.len, pcm.buf, pcm.len) || overlaps(iq.buf, iq.len, st.buf, st.len)
            || overlaps(pcm.buf, pcm.len, st.buf, st.len))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    ham_state *s = get_state(state_obj);
    size_t needed = ((iq.len / 2 + s->p1) / 8) * 2;
    if (pcm.len < needed) mp_raise_ValueError(MP_ERROR_TEXT("PCM buffer too small"));
    return mp_obj_new_int_from_uint(ham_process(iq.buf, iq.len, pcm.buf, s));
}
static MP_DEFINE_CONST_FUN_OBJ_3(process_obj, process);

static mp_obj_t configure(size_t n_args, const mp_obj_t *args) {
    ham_state *s = get_state(args[0]);
    mp_int_t mode = mp_obj_get_int(args[1]);
    if (mode < 0 || mode >= HAM_MODES) mp_raise_ValueError(MP_ERROR_TEXT("mode must be 0..4"));
    mp_int_t offset = mp_obj_get_int(args[2]);
    if (offset <= -128000 || offset >= 128000)
        mp_raise_ValueError(MP_ERROR_TEXT("offset must be within +-128 kHz"));
    mp_int_t squelch = n_args > 3 ? mp_obj_get_int(args[3]) : 0;
    if (squelch < 0 || squelch > 100000)
        mp_raise_ValueError(MP_ERROR_TEXT("squelch must be 0..100000"));
    mp_int_t flags = n_args > 4 ? mp_obj_get_int(args[4]) : 0;
    ham_configure(s, (uint32_t)mode, (float)offset, (float)squelch * 0.001f, (uint32_t)flags);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(configure_obj, 3, 5, configure);

static mp_obj_t q16(float v) {
    if (!(v > 0)) v = 0;
    if (v > 65535.0f) v = 65535.0f;
    return mp_obj_new_int_from_uint((mp_uint_t)(v * 65536.0f));
}

static mp_obj_t status(mp_obj_t state_obj) {
    ham_state *s = get_state(state_obj);
    mp_obj_t result[3] = {q16(s->power), q16(s->noise), mp_obj_new_bool(s->squelch_open)};
    return mp_obj_new_tuple(3, result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(status_obj, status);

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY
    mp_store_global(MP_QSTR_process, MP_OBJ_FROM_PTR(&process_obj));
    mp_store_global(MP_QSTR_configure, MP_OBJ_FROM_PTR(&configure_obj));
    mp_store_global(MP_QSTR_status, MP_OBJ_FROM_PTR(&status_obj));
    MP_DYNRUNTIME_INIT_EXIT
}
