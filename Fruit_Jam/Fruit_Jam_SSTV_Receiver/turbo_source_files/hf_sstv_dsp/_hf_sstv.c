// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Native CircuitPython module: HF SSTV detector and decoder.
//   STATE_BYTES, N_MODES
//   feed(state, pcm32, ring, write_pos) -> new write_pos
//       32 kHz int16 PCM (the USB demodulator's output) -> 8 kHz int16 into
//       ring at byte write_pos (wrapping), and through the detector.
//   scan(state, ring, start, length)
//       Run the detector over 8 kHz PCM already in the ring (a WAV file).
//   event(state) -> None or (kind, mode, code, offset_hz, extra, age)
//       kind 1 VIS (extra: margin x100), 2 sync train (extra: lines
//       matched); mode -1 for a VIS code this module does not decode; age:
//       8 kHz samples from the VIS end / earliest matched sync to now.
//   track(state, mode)
//       -1 stops following the current picture (the next sync train can
//       trigger again).
//   status(state) -> (mode, line, lines_seen, last_sync_age, anchor_age, score_x1000)
//       The picture being followed: line `line` started its sync
//       anchor_age samples ago (negative: still to come, as a Scottie
//       picture's line 0 right after its VIS header).
//   mode_info(mode) -> (name, vis, width, height, scan_lines, line_us, seconds_ms, vis_to_sync0_us)
//   decode_work_bytes(mode, length) -> bytes of work memory for `length` bytes of PCM
//   decode_begin(work, ring, start, length, mode, offset_hz=None, vis_pos=None, disp_w=320, disp_h=240) -> False if too short
//       vis_pos: samples from `start` to the end of the VIS stop bit.
//   decode_step(work, ring, rgb565=None, bgr=None) -> progress 0..100
//       rgb565: disp_w x disp_h 16-bit pixels (e.g. a displayio.Bitmap's
//       buffer); the image is fitted into it, centred. bgr: width x height
//       x 3 bottom-up (BMP order).
//   decode_result(work) -> (mode, lines, first_line, vis, period_us, align, syncs, offset_hz)
//       align: 0 none, 1 VIS, 2 first sync, 3 last sync.
//   preview_work_bytes(mode)
//   preview_begin(work, ring, sync_pos, mode, line, offset_hz, disp_w=320, disp_h=240)
//   preview_step(work, ring, rgb565) -> True when the line is drawn
//       Live picture: scan line `line`, whose sync starts at byte sync_pos
//       of the ring, at the nominal line rate; one channel per step.
// The interface is integers only: this firmware is built with the softfp
// ABI, so float arguments and results would not cross the call boundary
// correctly from a hard-float module.
#include "py/dynruntime.h"
#include "hf_detect.h"
#include "hf_decode.h"

static int bytes_type(int t) { return t == 'B' || t == 'b' || t == BYTEARRAY_TYPECODE; }
static int overlaps(const void *a, size_t al, const void *b, size_t bl) {
    if (!al || !bl) return 0;
    uintptr_t x = (uintptr_t)a, y = (uintptr_t)b;
    return x <= y ? y - x < al : x - y < bl;
}

static hf_det *get_state(mp_obj_t obj) {
    mp_buffer_info_t st;
    mp_get_buffer_raise(obj, &st, MP_BUFFER_WRITE);
    if (!bytes_type(st.typecode) || st.len != HF_DET_BYTES || ((uintptr_t)st.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("state must be an aligned bytearray(STATE_BYTES)"));
    hf_det *d = st.buf;
    if (d->magic == 0) hf_det_reset(d);
    if (d->magic != DET_MAGIC || d->dpos >= HF_DECIM_TAPS || d->dphase >= 4 || d->fe.h >= HF_LP_TAPS
            || d->fe.ph >= 80 || d->ncand < 0 || d->ncand > DET_CANDS || d->ev_n < 0 || d->ev_n > DET_EVENTS
            || d->ev_head < 0 || d->ev_head >= DET_EVENTS || d->track_mode < -1 || d->track_mode >= HF_NMODES)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid detector state; replace with bytearray(STATE_BYTES)"));
    for (int g = 0; g < DET_NGRID; g++)
        if (d->gi[g] >= 160) mp_raise_ValueError(MP_ERROR_TEXT("invalid detector state"));
    return d;
}

static void get_ring(mp_obj_t obj, mp_buffer_info_t *ring, int flags) {
    mp_get_buffer_raise(obj, ring, flags);
    if (!bytes_type(ring->typecode) || (ring->len & 1) || ring->len == 0)
        mp_raise_ValueError(MP_ERROR_TEXT("ring must be a non-empty byte buffer of even length"));
}

static mp_obj_t feed(size_t n_args, const mp_obj_t *args) {
    hf_det *d = get_state(args[0]);
    mp_buffer_info_t pcm, ring;
    mp_get_buffer_raise(args[1], &pcm, MP_BUFFER_READ);
    get_ring(args[2], &ring, MP_BUFFER_WRITE);
    mp_int_t wp = mp_obj_get_int(args[3]);
    if (!bytes_type(pcm.typecode) || (pcm.len & 1) || pcm.len > 65536)
        mp_raise_ValueError(MP_ERROR_TEXT("pcm must be bytes, even length <= 65536"));
    if (wp < 0 || (wp & 1) || (size_t)wp >= ring.len)
        mp_raise_ValueError(MP_ERROR_TEXT("write_pos must be even and inside the ring"));
    if (overlaps(pcm.buf, pcm.len, ring.buf, ring.len) || overlaps(d, sizeof(hf_det), ring.buf, ring.len))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    return mp_obj_new_int_from_uint(hf_det_feed(d, pcm.buf, pcm.len, ring.buf, ring.len, (size_t)wp));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(feed_obj, 4, 4, feed);

static mp_obj_t scan(size_t n_args, const mp_obj_t *args) {
    hf_det *d = get_state(args[0]);
    mp_buffer_info_t ring;
    get_ring(args[1], &ring, MP_BUFFER_READ);
    mp_int_t start = mp_obj_get_int(args[2]), length = mp_obj_get_int(args[3]);
    if (start < 0 || (start & 1) || (size_t)start >= ring.len || length < 0 || (size_t)length > ring.len || length > 65536)
        mp_raise_ValueError(MP_ERROR_TEXT("start inside the ring and even, length <= ring and <= 65536"));
    if (overlaps(d, sizeof(hf_det), ring.buf, ring.len))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    hf_det_scan(d, ring.buf, ring.len, (size_t)start, (size_t)length);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(scan_obj, 4, 4, scan);

static mp_obj_t event(mp_obj_t state_obj) {
    hf_det *d = get_state(state_obj);
    hf_event e;
    if (!hf_det_event(d, &e)) return mp_const_none;
    mp_obj_t r[6] = {mp_obj_new_int(e.kind), mp_obj_new_int(e.mode), mp_obj_new_int(e.code), mp_obj_new_int(e.offset),
                     mp_obj_new_int(e.extra), mp_obj_new_int_from_uint(d->n - e.t)};
    return mp_obj_new_tuple(6, r);
}
static MP_DEFINE_CONST_FUN_OBJ_1(event_obj, event);

static mp_obj_t track(mp_obj_t state_obj, mp_obj_t mode_obj) {
    hf_det *d = get_state(state_obj);
    mp_int_t mode = mp_obj_get_int(mode_obj);
    if (mode != -1) mp_raise_ValueError(MP_ERROR_TEXT("only track(state, -1) is supported"));
    d->track_mode = -1;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(track_obj, track);

static mp_obj_t status(mp_obj_t state_obj) {
    hf_det *d = get_state(state_obj);
    uint32_t last = d->track_last * 4 - 16, anchor = d->track_anchor * 4 - 16;
    mp_obj_t r[6] = {mp_obj_new_int(d->track_mode), mp_obj_new_int(d->track_line), mp_obj_new_int(d->track_lines),
                     mp_obj_new_int((int32_t)(d->n - last)), mp_obj_new_int((int32_t)(d->n - anchor)),
                     mp_obj_new_int(hf_round(d->score * 1000))};
    return mp_obj_new_tuple(6, r);
}
static MP_DEFINE_CONST_FUN_OBJ_1(status_obj, status);

static int get_mode(mp_obj_t obj) {
    mp_int_t mode = mp_obj_get_int(obj);
    if (mode < 0 || mode >= HF_NMODES) mp_raise_ValueError(MP_ERROR_TEXT("mode out of range"));
    return (int)mode;
}

static mp_obj_t mode_info(mp_obj_t mode_obj) {
    const hf_mode *m = &hf_modes[get_mode(mode_obj)];
    size_t len = 0;
    while (m->name[len]) len++;
    mp_obj_t r[8] = {mp_obj_new_str(m->name, len), mp_obj_new_int(m->vis), mp_obj_new_int(m->width),
                     mp_obj_new_int(m->height), mp_obj_new_int(m->lines), mp_obj_new_int(hf_round(m->line_ms * 1000)),
                     mp_obj_new_int(hf_round(hf_mode_seconds(m) * 1000)), mp_obj_new_int(hf_round(m->vis_to_sync0 * 1000))};
    return mp_obj_new_tuple(8, r);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mode_info_obj, mode_info);

static mp_obj_t decode_work_bytes(mp_obj_t mode_obj, mp_obj_t length_obj) {
    int mode = get_mode(mode_obj);
    mp_int_t length = mp_obj_get_int(length_obj);
    if (length < 0) mp_raise_ValueError(MP_ERROR_TEXT("length must be >= 0"));
    return mp_obj_new_int_from_uint(hf_decode_work_bytes(mode, (size_t)length / 2));
}
static MP_DEFINE_CONST_FUN_OBJ_2(decode_work_bytes_obj, decode_work_bytes);

static mp_obj_t decode_begin(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t work, ring;
    mp_get_buffer_raise(args[0], &work, MP_BUFFER_WRITE);
    get_ring(args[1], &ring, MP_BUFFER_READ);
    mp_int_t start = mp_obj_get_int(args[2]), length = mp_obj_get_int(args[3]);
    int mode = get_mode(args[4]);
    int off_known = n_args > 5 && args[5] != mp_const_none;
    mp_int_t offset = off_known ? mp_obj_get_int(args[5]) : 0;
    mp_int_t vis_pos = n_args > 6 && args[6] != mp_const_none ? mp_obj_get_int(args[6]) : -1;
    mp_int_t dw = n_args > 7 ? mp_obj_get_int(args[7]) : 320, dh = n_args > 8 ? mp_obj_get_int(args[8]) : 240;
    if (start < 0 || (start & 1) || (size_t)start >= ring.len || length < 0 || (length & 1) || (size_t)length > ring.len)
        mp_raise_ValueError(MP_ERROR_TEXT("start and length must be even, inside the ring"));
    if (offset < -400 || offset > 400) mp_raise_ValueError(MP_ERROR_TEXT("offset must be within +-400 Hz"));
    if (vis_pos < -1 || vis_pos > length / 2) mp_raise_ValueError(MP_ERROR_TEXT("vis_pos outside the recording"));
    if (dw < 0 || dw > 4096 || dh < 0 || dh > 4096) mp_raise_ValueError(MP_ERROR_TEXT("bad display size"));
    if (work.len < hf_decode_work_bytes(mode, (size_t)length / 2) || ((uintptr_t)work.buf & 3))
        mp_raise_ValueError(MP_ERROR_TEXT("work buffer too small or unaligned"));
    if (overlaps(work.buf, work.len, ring.buf, ring.len))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    return mp_obj_new_bool(hf_decode_begin(work.buf, ring.len, (size_t)start, (size_t)length, mode, off_known,
                                           (int)offset, (long)vis_pos, (int)dw, (int)dh) == 0);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(decode_begin_obj, 5, 9, decode_begin);

static mp_obj_t decode_step(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t work, ring, rgb = {0}, bgr = {0};
    mp_get_buffer_raise(args[0], &work, MP_BUFFER_WRITE);
    get_ring(args[1], &ring, MP_BUFFER_READ);
    hf_dec *st = (hf_dec *)work.buf;
    if (work.len < sizeof(hf_dec) || ((uintptr_t)work.buf & 3) || st->magic != DEC_MAGIC || st->ring_len != ring.len
            || st->mode < 0 || st->mode >= HF_NMODES || work.len < hf_decode_work_bytes(st->mode, st->length / 2))
        mp_raise_ValueError(MP_ERROR_TEXT("call decode_begin first, with this ring"));
    const hf_mode *m = &hf_modes[st->mode];
    if (n_args > 2 && args[2] != mp_const_none) {
        mp_get_buffer_raise(args[2], &rgb, MP_BUFFER_WRITE);
        if (rgb.len < (size_t)st->disp_w * st->disp_h * 2)
            mp_raise_ValueError(MP_ERROR_TEXT("rgb565 smaller than disp_w x disp_h x 2"));
    }
    if (n_args > 3 && args[3] != mp_const_none) {
        mp_get_buffer_raise(args[3], &bgr, MP_BUFFER_WRITE);
        if (bgr.len < (size_t)m->width * m->height * 3) mp_raise_ValueError(MP_ERROR_TEXT("bgr smaller than width x height x 3"));
    }
    if ((rgb.buf && (overlaps(work.buf, work.len, rgb.buf, rgb.len) || overlaps(ring.buf, ring.len, rgb.buf, rgb.len)))
            || (bgr.buf && (overlaps(work.buf, work.len, bgr.buf, bgr.len) || overlaps(ring.buf, ring.len, bgr.buf, bgr.len))))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    return mp_obj_new_int(hf_decode_step(work.buf, ring.buf, rgb.buf, bgr.buf));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(decode_step_obj, 2, 4, decode_step);

static mp_obj_t decode_result(mp_obj_t work_obj) {
    mp_buffer_info_t work;
    mp_get_buffer_raise(work_obj, &work, MP_BUFFER_READ);
    if (work.len < sizeof(hf_dec) || ((uintptr_t)work.buf & 3) || ((hf_dec *)work.buf)->magic != DEC_MAGIC)
        mp_raise_ValueError(MP_ERROR_TEXT("call decode_begin first"));
    hf_decode_info i = hf_decode_result(work.buf);
    mp_obj_t r[8] = {mp_obj_new_int(i.mode), mp_obj_new_int(i.lines), mp_obj_new_int(i.first_line), mp_obj_new_bool(i.vis),
                     mp_obj_new_int(i.period_us), mp_obj_new_int(i.align), mp_obj_new_int(i.syncs), mp_obj_new_int(i.offset_hz)};
    return mp_obj_new_tuple(8, r);
}
static MP_DEFINE_CONST_FUN_OBJ_1(decode_result_obj, decode_result);

static mp_obj_t preview_begin(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t work, ring;
    mp_get_buffer_raise(args[0], &work, MP_BUFFER_WRITE);
    get_ring(args[1], &ring, MP_BUFFER_READ);
    mp_int_t pos = mp_obj_get_int(args[2]);
    int mode = get_mode(args[3]);
    mp_int_t line = mp_obj_get_int(args[4]), offset = mp_obj_get_int(args[5]);
    mp_int_t dw = n_args > 6 ? mp_obj_get_int(args[6]) : 320, dh = n_args > 7 ? mp_obj_get_int(args[7]) : 240;
    if (pos < 0 || (size_t)pos >= ring.len || line < 0 || line >= hf_modes[mode].lines || offset < -400 || offset > 400
            || dw < 1 || dw > 4096 || dh < 1 || dh > 4096)
        mp_raise_ValueError(MP_ERROR_TEXT("bad preview arguments"));
    if (work.len < hf_preview_work_bytes(mode) || ((uintptr_t)work.buf & 3) || overlaps(work.buf, work.len, ring.buf, ring.len))
        mp_raise_ValueError(MP_ERROR_TEXT("preview work buffer too small, unaligned or overlapping"));
    hf_preview_begin(work.buf, ring.len, (size_t)pos, mode, (int)line, (int)offset, (int)dw, (int)dh);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(preview_begin_obj, 6, 8, preview_begin);

static mp_obj_t preview_step(mp_obj_t work_obj, mp_obj_t ring_obj, mp_obj_t rgb_obj) {
    mp_buffer_info_t work, ring, rgb;
    mp_get_buffer_raise(work_obj, &work, MP_BUFFER_WRITE);
    get_ring(ring_obj, &ring, MP_BUFFER_READ);
    mp_get_buffer_raise(rgb_obj, &rgb, MP_BUFFER_WRITE);
    hf_dec *st = (hf_dec *)work.buf;
    if (work.len < sizeof(hf_dec) || ((uintptr_t)work.buf & 3) || st->magic != DEC_MAGIC || st->ring_len != ring.len
            || st->mode < 0 || st->mode >= HF_NMODES || work.len < hf_preview_work_bytes(st->mode))
        mp_raise_ValueError(MP_ERROR_TEXT("call preview_begin first, with this ring"));
    if (rgb.len < (size_t)st->disp_w * st->disp_h * 2) mp_raise_ValueError(MP_ERROR_TEXT("rgb565 too small"));
    if (overlaps(work.buf, work.len, rgb.buf, rgb.len) || overlaps(ring.buf, ring.len, rgb.buf, rgb.len))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    return mp_obj_new_bool(hf_preview_step(work.buf, ring.buf, rgb.buf));
}
static MP_DEFINE_CONST_FUN_OBJ_3(preview_step_obj, preview_step);

static mp_obj_t preview_work_bytes(mp_obj_t mode_obj) {
    return mp_obj_new_int_from_uint(hf_preview_work_bytes(get_mode(mode_obj)));
}
static MP_DEFINE_CONST_FUN_OBJ_1(preview_work_bytes_obj, preview_work_bytes);

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY
    mp_store_global(MP_QSTR_STATE_BYTES, MP_OBJ_NEW_SMALL_INT(HF_DET_BYTES));
    mp_store_global(MP_QSTR_N_MODES, MP_OBJ_NEW_SMALL_INT(HF_NMODES));
    mp_store_global(MP_QSTR_feed, MP_OBJ_FROM_PTR(&feed_obj));
    mp_store_global(MP_QSTR_scan, MP_OBJ_FROM_PTR(&scan_obj));
    mp_store_global(MP_QSTR_event, MP_OBJ_FROM_PTR(&event_obj));
    mp_store_global(MP_QSTR_track, MP_OBJ_FROM_PTR(&track_obj));
    mp_store_global(MP_QSTR_status, MP_OBJ_FROM_PTR(&status_obj));
    mp_store_global(MP_QSTR_mode_info, MP_OBJ_FROM_PTR(&mode_info_obj));
    mp_store_global(MP_QSTR_decode_work_bytes, MP_OBJ_FROM_PTR(&decode_work_bytes_obj));
    mp_store_global(MP_QSTR_decode_begin, MP_OBJ_FROM_PTR(&decode_begin_obj));
    mp_store_global(MP_QSTR_decode_step, MP_OBJ_FROM_PTR(&decode_step_obj));
    mp_store_global(MP_QSTR_decode_result, MP_OBJ_FROM_PTR(&decode_result_obj));
    mp_store_global(MP_QSTR_preview_work_bytes, MP_OBJ_FROM_PTR(&preview_work_bytes_obj));
    mp_store_global(MP_QSTR_preview_begin, MP_OBJ_FROM_PTR(&preview_begin_obj));
    mp_store_global(MP_QSTR_preview_step, MP_OBJ_FROM_PTR(&preview_step_obj));
    MP_DYNRUNTIME_INIT_EXIT
}
