// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Native CircuitPython module wrapping ft8_core.h: FT8 decoder.
//   FEED_BYTES, SPEC_BYTES, ROWS, SEARCH_ROWS, MAX_RESULTS
//   work_bytes(max_candidates) -> bytes for the decode work memory
//   feed_init(state, step=4)
//       Start a feed over: input at 32 kHz (step 4) or 8 kHz (step 1).
//   slot_reset(state, spec, tag=0)
//       Start filling the waterfall spec: its first row ends 80 ms of
//       audio after this point. tag is kept with it (e.g. slot time).
//   feed(state, pcm, spec, ring=None) -> rows in spec so far (ROWS when full)
//       16-bit PCM through the feed; every 80 ms of audio adds a row. The
//       8 kHz audio also goes into ring (a byte buffer, if given) at
//       ring_pos(state), wrapping.
//   ring_pos(state) -> byte position in the ring of the next 8 kHz sample
//   set_ring_pos(state, pos)
//   work_init(work, max_candidates)
//       Clear the decode work memory (also the callsign hash table).
//   decode_begin(work, spec, min_score=10, ldpc_iterations=25, early_stop=1)
//       early_stop: give up on a candidate whose LDPC decoding stalls
//       (as WSJT-X), which saves about half the time on noise.
//   decode_step(work, spec, units=1) -> units of work left, 0 when done
//       A unit is one row of the sync search (SEARCH_ROWS of them) or one
//       candidate. The spec must not change until decoding is done.
//   result_count(work) -> n
//   result(work, i, text_buf) -> (snr_db, dt_ms, freq_hz, text_len)
//   stats(work) -> (candidates, tried, ldpc_fail, crc_fail, unpack_fail,
//                   duplicates, noise_v, hash_size)
//   spec_info(spec) -> (rows, tag)
// The interface is integers only: this firmware is built with the softfp
// ABI, so float arguments and results would not cross the call boundary
// correctly from a hard-float module.
#define FT8_TARGET
#include "py/dynruntime.h"
#include "ft8_core.h"

static int bytes_type(int t) { return t == 'B' || t == 'b' || t == BYTEARRAY_TYPECODE; }

static void *get_buf(mp_obj_t obj, size_t min_len, const char *what) {
    mp_buffer_info_t b;
    mp_get_buffer_raise(obj, &b, MP_BUFFER_WRITE);
    if (!bytes_type(b.typecode) || b.len < min_len || ((uintptr_t)b.buf & 3))
        mp_raise_ValueError(what);
    return b.buf;
}

static ft8_feed_state *get_feed(mp_obj_t obj) {
    ft8_feed_state *s = get_buf(obj, FT8_FEED_BYTES, MP_ERROR_TEXT("state must be an aligned bytearray(FEED_BYTES)"));
    if (s->magic != FT8_FEED_MAGIC) ft8_feed_init(s, 4);
    if ((s->step != 1 && s->step != 4) || s->acc_n >= s->step || s->fill >= FT8_SUB || s->wpos >= FT8_NFFT)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid feed state; call feed_init"));
    if (!ft8_fft_ready(s)) mp_raise_ValueError(MP_ERROR_TEXT("FFT set-up failed"));
    return s;
}

static uint8_t *get_spec(mp_obj_t obj) {
    uint8_t *spec = get_buf(obj, FT8_SPEC_BYTES, MP_ERROR_TEXT("spec must be an aligned bytearray(SPEC_BYTES)"));
    ft8_spec_header *h = (ft8_spec_header *)spec;
    if (h->magic != FT8_SPEC_MAGIC) ft8_spec_reset(spec, 0);
    if (h->rows > FT8_ROWS) mp_raise_ValueError(MP_ERROR_TEXT("invalid spec; call slot_reset"));
    return spec;
}

static ft8_work *get_work(mp_obj_t obj) {
    mp_buffer_info_t b;
    mp_get_buffer_raise(obj, &b, MP_BUFFER_WRITE);
    ft8_work *w = b.buf;
    if (!bytes_type(b.typecode) || b.len < sizeof(ft8_work) || ((uintptr_t)b.buf & 3) || w->magic != FT8_WORK_MAGIC
            || w->max_cand < 1 || b.len < FT8_WORK_BYTES(w->max_cand) || w->phase > FT8_DONE
            || w->search_row > FT8_SEARCH_ROWS || w->heap_size > w->max_cand || w->next > w->heap_size
            || w->n_results > FT8_MAX_RESULTS || w->hash_size >= FT8_HASH_SIZE)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid work memory; call work_init"));
    return w;
}

static mp_obj_t work_bytes(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    if (n < 1 || n > 1000) mp_raise_ValueError(MP_ERROR_TEXT("max_candidates must be 1..1000"));
    return mp_obj_new_int_from_uint(FT8_WORK_BYTES(n));
}
static MP_DEFINE_CONST_FUN_OBJ_1(work_bytes_obj, work_bytes);

static mp_obj_t feed_init(size_t n_args, const mp_obj_t *args) {
    ft8_feed_state *s = get_buf(args[0], FT8_FEED_BYTES, MP_ERROR_TEXT("state must be an aligned bytearray(FEED_BYTES)"));
    mp_int_t step = n_args > 1 ? mp_obj_get_int(args[1]) : 4;
    if (step != 1 && step != 4) mp_raise_ValueError(MP_ERROR_TEXT("step must be 4 (32 kHz) or 1 (8 kHz)"));
    if (!ft8_feed_init(s, (int)step)) mp_raise_ValueError(MP_ERROR_TEXT("FFT set-up failed"));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(feed_init_obj, 1, 2, feed_init);

static mp_obj_t slot_reset(size_t n_args, const mp_obj_t *args) {
    ft8_feed_state *s = get_feed(args[0]);
    uint8_t *spec = get_buf(args[1], FT8_SPEC_BYTES, MP_ERROR_TEXT("spec must be an aligned bytearray(SPEC_BYTES)"));
    ft8_slot_reset(s, spec, n_args > 2 ? (int32_t)mp_obj_get_int(args[2]) : 0);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(slot_reset_obj, 2, 3, slot_reset);

static int overlaps(const void *a, size_t al, const void *b, size_t bl) {
    if (!al || !bl) return 0;
    uintptr_t x = (uintptr_t)a, y = (uintptr_t)b;
    return x <= y ? y - x < al : x - y < bl;
}

static mp_obj_t feed(size_t n_args, const mp_obj_t *args) {
    ft8_feed_state *s = get_feed(args[0]);
    uint8_t *spec = get_spec(args[2]);
    mp_buffer_info_t pcm, ring = {0};
    mp_get_buffer_raise(args[1], &pcm, MP_BUFFER_READ);
    if (!bytes_type(pcm.typecode) || (pcm.len & 1) || ((uintptr_t)pcm.buf & 1))
        mp_raise_ValueError(MP_ERROR_TEXT("pcm must be 16-bit samples in a byte buffer"));
    if (n_args > 3 && args[3] != mp_const_none) {
        mp_get_buffer_raise(args[3], &ring, MP_BUFFER_WRITE);
        if (!bytes_type(ring.typecode) || (ring.len & 1) || ring.len < 2)
            mp_raise_ValueError(MP_ERROR_TEXT("ring must be a byte buffer of even length"));
        if (overlaps(ring.buf, ring.len, pcm.buf, pcm.len) || overlaps(ring.buf, ring.len, spec, FT8_SPEC_BYTES)
                || overlaps(ring.buf, ring.len, s, sizeof(*s)))
            mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    }
    return mp_obj_new_int_from_uint(ft8_feed(s, pcm.buf, pcm.len / 2, spec, ring.buf, ring.len));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(feed_obj, 3, 4, feed);

static mp_obj_t ring_pos(mp_obj_t state_obj) {
    return mp_obj_new_int_from_uint(get_feed(state_obj)->ring_pos);
}
static MP_DEFINE_CONST_FUN_OBJ_1(ring_pos_obj, ring_pos);

static mp_obj_t set_ring_pos(mp_obj_t state_obj, mp_obj_t pos_obj) {
    mp_int_t pos = mp_obj_get_int(pos_obj);
    if (pos < 0 || (pos & 1)) mp_raise_ValueError(MP_ERROR_TEXT("pos must be even and >= 0"));
    get_feed(state_obj)->ring_pos = (uint32_t)pos;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(set_ring_pos_obj, set_ring_pos);

static mp_obj_t work_init(mp_obj_t work_obj, mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    if (n < 1 || n > 1000) mp_raise_ValueError(MP_ERROR_TEXT("max_candidates must be 1..1000"));
    get_buf(work_obj, FT8_WORK_BYTES(n), MP_ERROR_TEXT("work must be an aligned bytearray(work_bytes(max_candidates))"));
    mp_buffer_info_t b;
    mp_get_buffer_raise(work_obj, &b, MP_BUFFER_WRITE);
    ft8_work_init(b.buf, (uint32_t)n);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(work_init_obj, work_init);

static mp_obj_t decode_begin(size_t n_args, const mp_obj_t *args) {
    ft8_work *w = get_work(args[0]);
    uint8_t *spec = get_spec(args[1]);
    mp_int_t min_score = n_args > 2 ? mp_obj_get_int(args[2]) : 10;
    mp_int_t iters = n_args > 3 ? mp_obj_get_int(args[3]) : 25;
    mp_int_t early = n_args > 4 ? mp_obj_get_int(args[4]) : 1;
    if (min_score < 0 || min_score > 255 || iters < 1 || iters > 100)
        mp_raise_ValueError(MP_ERROR_TEXT("min_score 0..255, ldpc_iterations 1..100"));
    ft8_decode_begin(w, spec, (int)min_score, (int)iters, early ? 1 : 0);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(decode_begin_obj, 2, 5, decode_begin);

static mp_obj_t decode_step(size_t n_args, const mp_obj_t *args) {
    ft8_work *w = get_work(args[0]);
    uint8_t *spec = get_spec(args[1]);
    mp_int_t units = n_args > 2 ? mp_obj_get_int(args[2]) : 1;
    if (units < 1) mp_raise_ValueError(MP_ERROR_TEXT("units must be >= 1"));
    if (w->num_blocks > ((ft8_spec_header *)spec)->rows / FT8_TOSR)
        mp_raise_ValueError(MP_ERROR_TEXT("spec changed during decoding"));
    return mp_obj_new_int_from_uint(ft8_decode_step(w, spec, (uint32_t)units));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(decode_step_obj, 2, 3, decode_step);

static mp_obj_t result_count(mp_obj_t work_obj) {
    return mp_obj_new_int_from_uint(get_work(work_obj)->n_results);
}
static MP_DEFINE_CONST_FUN_OBJ_1(result_count_obj, result_count);

static mp_obj_t result(mp_obj_t work_obj, mp_obj_t i_obj, mp_obj_t text_obj) {
    ft8_work *w = get_work(work_obj);
    mp_int_t i = mp_obj_get_int(i_obj);
    if (i < 0 || (mp_uint_t)i >= w->n_results) mp_raise_ValueError(MP_ERROR_TEXT("no such result"));
    mp_buffer_info_t t;
    mp_get_buffer_raise(text_obj, &t, MP_BUFFER_WRITE);
    if (!bytes_type(t.typecode)) mp_raise_ValueError(MP_ERROR_TEXT("text_buf must be a byte buffer"));
    const ft8_result *r = &w->results[i];
    size_t n = ft8_strlen(r->text);
    if (n > t.len) n = t.len;
    memcpy(t.buf, r->text, n);
    mp_obj_t o[4] = {mp_obj_new_int(r->snr), mp_obj_new_int(r->dt_ms), mp_obj_new_int(r->freq_hz),
                     mp_obj_new_int_from_uint(n)};
    return mp_obj_new_tuple(4, o);
}
static MP_DEFINE_CONST_FUN_OBJ_3(result_obj, result);

static mp_obj_t stats(mp_obj_t work_obj) {
    ft8_work *w = get_work(work_obj);
    mp_obj_t o[8] = {mp_obj_new_int_from_uint(w->heap_size), mp_obj_new_int_from_uint(w->tried),
                     mp_obj_new_int_from_uint(w->ldpc_fail), mp_obj_new_int_from_uint(w->crc_fail),
                     mp_obj_new_int_from_uint(w->unpack_fail), mp_obj_new_int_from_uint(w->dupes),
                     mp_obj_new_int(w->noise_v), mp_obj_new_int_from_uint(w->hash_size)};
    return mp_obj_new_tuple(8, o);
}
static MP_DEFINE_CONST_FUN_OBJ_1(stats_obj, stats);

static mp_obj_t spec_info(mp_obj_t spec_obj) {
    ft8_spec_header *h = (ft8_spec_header *)get_spec(spec_obj);
    mp_obj_t o[2] = {mp_obj_new_int_from_uint(h->rows), mp_obj_new_int(h->tag)};
    return mp_obj_new_tuple(2, o);
}
static MP_DEFINE_CONST_FUN_OBJ_1(spec_info_obj, spec_info);

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY
    mp_store_global(MP_QSTR_FEED_BYTES, MP_OBJ_NEW_SMALL_INT(FT8_FEED_BYTES));
    mp_store_global(MP_QSTR_SPEC_BYTES, MP_OBJ_NEW_SMALL_INT(FT8_SPEC_BYTES));
    mp_store_global(MP_QSTR_ROWS, MP_OBJ_NEW_SMALL_INT(FT8_ROWS));
    mp_store_global(MP_QSTR_SEARCH_ROWS, MP_OBJ_NEW_SMALL_INT(FT8_SEARCH_ROWS));
    mp_store_global(MP_QSTR_MAX_RESULTS, MP_OBJ_NEW_SMALL_INT(FT8_MAX_RESULTS));
    mp_store_global(MP_QSTR_work_bytes, MP_OBJ_FROM_PTR(&work_bytes_obj));
    mp_store_global(MP_QSTR_feed_init, MP_OBJ_FROM_PTR(&feed_init_obj));
    mp_store_global(MP_QSTR_slot_reset, MP_OBJ_FROM_PTR(&slot_reset_obj));
    mp_store_global(MP_QSTR_feed, MP_OBJ_FROM_PTR(&feed_obj));
    mp_store_global(MP_QSTR_ring_pos, MP_OBJ_FROM_PTR(&ring_pos_obj));
    mp_store_global(MP_QSTR_set_ring_pos, MP_OBJ_FROM_PTR(&set_ring_pos_obj));
    mp_store_global(MP_QSTR_work_init, MP_OBJ_FROM_PTR(&work_init_obj));
    mp_store_global(MP_QSTR_decode_begin, MP_OBJ_FROM_PTR(&decode_begin_obj));
    mp_store_global(MP_QSTR_decode_step, MP_OBJ_FROM_PTR(&decode_step_obj));
    mp_store_global(MP_QSTR_result_count, MP_OBJ_FROM_PTR(&result_count_obj));
    mp_store_global(MP_QSTR_result, MP_OBJ_FROM_PTR(&result_obj));
    mp_store_global(MP_QSTR_stats, MP_OBJ_FROM_PTR(&stats_obj));
    mp_store_global(MP_QSTR_spec_info, MP_OBJ_FROM_PTR(&spec_info_obj));
    MP_DYNRUNTIME_INIT_EXIT
}
