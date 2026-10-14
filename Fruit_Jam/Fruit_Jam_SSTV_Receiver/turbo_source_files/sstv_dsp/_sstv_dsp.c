// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Native CircuitPython module wrapping sstv_core.h.
//   process(iq, pcm, state) -> bytes written (2 per 8 I/Q samples)
//   configure(state, offset_hz, squelch_milli=0, flags=0, afc_range_hz=15000)
//   status(state) -> (channel_power_q16, squelch_noise_q16, squelch_open, afc_hz)
//   decode_work_bytes(pcm_bytes) -> bytes of work memory decode() needs
//   decode_begin(work, ring, start, length) -> False if too short to decode
//   decode_step(work, ring, rgb565=None, bgr=None) -> progress 0..100
//   decode_result(work) -> (lines, first_line, vis_found, line_period_us, alignment, syncs)
//       Robot 36 from `length` bytes of PCM at byte `start` of `ring`
//       (wrapping), in steps of tens of milliseconds so USB and the display
//       keep running: call decode_step until it returns 100. rgb565 is 240
//       rows of 320 pixels (any row stride, e.g. a 16-bit displayio.Bitmap);
//       bgr is 320x240x3 bottom-up, BMP order. alignment: 0 none, 1 VIS,
//       2 first sync, 3 last sync. syncs: line syncs found (no image if few).
// The interface is integers only: this firmware is built with the softfp
// ABI, so float arguments and results would not cross the call boundary
// correctly from a hard-float module.
#include "py/dynruntime.h"
#include "sstv_core.h"
#include "sstv_decode.h"

static int bytes_type(int t) { return t == 'B' || t == 'b' || t == BYTEARRAY_TYPECODE; }
static int overlaps(const void *a, size_t al, const void *b, size_t bl) {
    if (!al || !bl) return 0;
    uintptr_t x = (uintptr_t)a, y = (uintptr_t)b;
    return x <= y ? y - x < al : x - y < bl;
}

static sstv_state *get_state(mp_obj_t obj) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(st.typecode) || st.len != SSTV_STATE_BYTES || ((uintptr_t)st.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("state must be an aligned bytearray(4096)"));
    sstv_state *s = st.buf;
    if (s->magic == 0) sstv_reset(s);
    if (s->magic != SSTV_MAGIC || s->h1 >= SSTV_F1_TAPS || s->p1 >= 8 || s->hn >= SSTV_FNFM_TAPS
            || s->win_n >= SSTV_WINDOW)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid DSP state; replace with bytearray(4096)"));
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
    sstv_state *s = get_state(state_obj);
    size_t needed = ((iq.len / 2 + s->p1) / 8) * 2;
    if (pcm.len < needed) mp_raise_ValueError(MP_ERROR_TEXT("PCM buffer too small"));
    return mp_obj_new_int_from_uint(sstv_process(iq.buf, iq.len, pcm.buf, s));
}
static MP_DEFINE_CONST_FUN_OBJ_3(process_obj, process);

static mp_obj_t configure(size_t n_args, const mp_obj_t *args) {
    sstv_state *s = get_state(args[0]);
    mp_int_t offset = mp_obj_get_int(args[1]);
    if (offset <= -128000 || offset >= 128000)
        mp_raise_ValueError(MP_ERROR_TEXT("offset must be within +-128 kHz"));
    mp_int_t squelch = n_args > 2 ? mp_obj_get_int(args[2]) : 0;
    if (squelch < 0 || squelch > 100000)
        mp_raise_ValueError(MP_ERROR_TEXT("squelch must be 0..100000"));
    mp_int_t flags = n_args > 3 ? mp_obj_get_int(args[3]) : 0;
    mp_int_t range = n_args > 4 ? mp_obj_get_int(args[4]) : 15000;
    if (range < 0 || range > 30000)
        mp_raise_ValueError(MP_ERROR_TEXT("afc_range must be 0..30000"));
    sstv_configure(s, (float)offset, (float)squelch * 0.001f, (uint32_t)flags, (float)range);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(configure_obj, 2, 5, configure);

static mp_obj_t q16(float v) {
    if (!(v > 0)) v = 0;
    if (v > 65535.0f) v = 65535.0f;
    return mp_obj_new_int_from_uint((mp_uint_t)(v * 65536.0f));
}

static mp_obj_t status(mp_obj_t state_obj) {
    sstv_state *s = get_state(state_obj);
    mp_obj_t result[4] = {q16(s->power), q16(s->noise), mp_obj_new_bool(s->squelch_open),
                          mp_obj_new_int((mp_int_t)s->afc_hz)};
    return mp_obj_new_tuple(4, result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(status_obj, status);

static mp_obj_t decode_work_bytes(mp_obj_t length_obj) {
    mp_int_t length = mp_obj_get_int(length_obj);
    if (length < 0) mp_raise_ValueError(MP_ERROR_TEXT("length must be >= 0"));
    return mp_obj_new_int_from_uint(sstv_decode_work_bytes((size_t)length / 2));
}
static MP_DEFINE_CONST_FUN_OBJ_1(decode_work_bytes_obj, decode_work_bytes);

static mp_obj_t decode_begin(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t work, ring;
    mp_get_buffer_raise(args[0], &work, MP_BUFFER_WRITE);
    mp_get_buffer_raise(args[1], &ring, MP_BUFFER_READ);
    mp_int_t start = mp_obj_get_int(args[2]);
    mp_int_t length = mp_obj_get_int(args[3]);
    if ((ring.len & 1) || ring.len == 0 || start < 0 || (start & 1) || length < 0 || (length & 1)
            || (size_t)length > ring.len)
        mp_raise_ValueError(MP_ERROR_TEXT("ring, start and length must be even, length <= ring"));
    if (work.len < sstv_decode_work_bytes((size_t)length / 2) || ((uintptr_t)work.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("work buffer too small or unaligned"));
    if (overlaps(work.buf, work.len, ring.buf, ring.len))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    return mp_obj_new_bool(sstv_decode_begin(work.buf, ring.len, (size_t)start, (size_t)length) == 0);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(decode_begin_obj, 4, 4, decode_begin);

static mp_obj_t decode_step(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t work, ring, rgb = {0}, bgr = {0};
    mp_get_buffer_raise(args[0], &work, MP_BUFFER_WRITE);
    mp_get_buffer_raise(args[1], &ring, MP_BUFFER_READ);
    dec_state *st = (dec_state *)work.buf;
    if (work.len < sizeof(dec_state) || ((uintptr_t)work.buf & 3) || st->magic != DEC_MAGIC
            || st->ring_len != ring.len || work.len < sstv_decode_work_bytes(st->length / 2))
        mp_raise_ValueError(MP_ERROR_TEXT("call decode_begin first, with this ring"));
    size_t stride = 0;
    if (n_args > 2 && args[2] != mp_const_none) {
        mp_get_buffer_raise(args[2], &rgb, MP_BUFFER_WRITE);
        stride = rgb.len / DEC_H;
        if (stride < 2 * DEC_W || rgb.len % DEC_H)
            mp_raise_ValueError(MP_ERROR_TEXT("rgb565 must be 240 rows of >= 640 bytes"));
    }
    if (n_args > 3 && args[3] != mp_const_none) {
        mp_get_buffer_raise(args[3], &bgr, MP_BUFFER_WRITE);
        if (bgr.len < DEC_W * DEC_H * 3) mp_raise_ValueError(MP_ERROR_TEXT("bgr must be 230400 bytes"));
    }
    if ((rgb.buf && overlaps(work.buf, work.len, rgb.buf, rgb.len))
            || (bgr.buf && overlaps(work.buf, work.len, bgr.buf, bgr.len)))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    return mp_obj_new_int(sstv_decode_step(work.buf, ring.buf, rgb.buf, stride, bgr.buf));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(decode_step_obj, 2, 4, decode_step);

static mp_obj_t decode_result(mp_obj_t work_obj) {
    mp_buffer_info_t work;
    mp_get_buffer_raise(work_obj, &work, MP_BUFFER_READ);
    if (work.len < sizeof(dec_state) || ((uintptr_t)work.buf & 3) || ((dec_state *)work.buf)->magic != DEC_MAGIC)
        mp_raise_ValueError(MP_ERROR_TEXT("call decode_begin first"));
    sstv_decode_info i = sstv_decode_result(work.buf);
    mp_obj_t result[6] = {mp_obj_new_int(i.lines), mp_obj_new_int(i.first_line), mp_obj_new_bool(i.vis),
                          mp_obj_new_int(i.period_us), mp_obj_new_int(i.align), mp_obj_new_int(i.syncs)};
    return mp_obj_new_tuple(6, result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(decode_result_obj, decode_result);

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY
    mp_store_global(MP_QSTR_process, MP_OBJ_FROM_PTR(&process_obj));
    mp_store_global(MP_QSTR_configure, MP_OBJ_FROM_PTR(&configure_obj));
    mp_store_global(MP_QSTR_status, MP_OBJ_FROM_PTR(&status_obj));
    mp_store_global(MP_QSTR_decode_work_bytes, MP_OBJ_FROM_PTR(&decode_work_bytes_obj));
    mp_store_global(MP_QSTR_decode_begin, MP_OBJ_FROM_PTR(&decode_begin_obj));
    mp_store_global(MP_QSTR_decode_step, MP_OBJ_FROM_PTR(&decode_step_obj));
    mp_store_global(MP_QSTR_decode_result, MP_OBJ_FROM_PTR(&decode_result_obj));
    MP_DYNRUNTIME_INIT_EXIT
}
