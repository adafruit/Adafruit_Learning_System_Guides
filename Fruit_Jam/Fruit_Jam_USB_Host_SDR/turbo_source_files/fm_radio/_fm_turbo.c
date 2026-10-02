// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "py/dynruntime.h"
#include "fm_core.h"
static int bytes_type(int t) { return t=='B' || t=='b' || t==BYTEARRAY_TYPECODE; }
static int overlaps(const void *a,size_t al,const void *b,size_t bl) {
    if (!al || !bl) return 0;
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x<=y ? y-x<al : x-y<bl;
}
static mp_obj_t process(mp_obj_t iq_obj,mp_obj_t pcm_obj,mp_obj_t state_obj) {
    mp_buffer_info_t iq,pcm,st;
    mp_get_buffer_raise(iq_obj,&iq,MP_BUFFER_READ);
    mp_get_buffer_raise(pcm_obj,&pcm,MP_BUFFER_WRITE);
    mp_get_buffer_raise(state_obj,&st,MP_BUFFER_WRITE);
    if (!bytes_type(iq.typecode) || !bytes_type(pcm.typecode) || !bytes_type(st.typecode))
        mp_raise_ValueError(MP_ERROR_TEXT("byte buffers required"));
    if ((iq.len&1) || iq.len>65536 || st.len!=FM_STATE_BYTES || ((uintptr_t)st.buf&3))
        mp_raise_ValueError(MP_ERROR_TEXT("IQ even <=65536; state aligned 512 bytes"));
    if (overlaps(iq.buf,iq.len,pcm.buf,pcm.len) || overlaps(iq.buf,iq.len,st.buf,st.len) || overlaps(pcm.buf,pcm.len,st.buf,st.len))
        mp_raise_ValueError(MP_ERROR_TEXT("buffers must not overlap"));
    fm_state *s=st.buf;
    if (s->magic==0) fm_reset(s);
    if (s->magic!=FM_MAGIC || s->head>=FM_TAPS || s->phase>=8 || s->have_prev>1)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid DSP state; replace with bytearray(512)"));
    size_t needed=((iq.len/2+s->phase)/8)*2;
    if (pcm.len<needed) mp_raise_ValueError(MP_ERROR_TEXT("PCM buffer too small"));
    return mp_obj_new_int_from_uint(fm_process(iq.buf,iq.len,pcm.buf,s));
}
static MP_DEFINE_CONST_FUN_OBJ_3(process_obj,process);
static mp_obj_t test_counter(mp_obj_t iq_obj,mp_obj_t previous_obj) {
    mp_buffer_info_t iq;
    mp_get_buffer_raise(iq_obj,&iq,MP_BUFFER_READ);
    mp_int_t previous=mp_obj_get_int(previous_obj);
    if (!bytes_type(iq.typecode) || iq.len>65536 || previous< -1 || previous>255)
        mp_raise_ValueError(MP_ERROR_TEXT("bytes <=65536; previous -1 or byte"));
    fm_counter_result r=fm_count(iq.buf,iq.len,previous);
    mp_obj_t result[3]={mp_obj_new_int(r.last),mp_obj_new_int_from_uint(r.discontinuities),mp_obj_new_int_from_uint(r.missing)};
    return mp_obj_new_tuple(3,result);
}
static MP_DEFINE_CONST_FUN_OBJ_2(test_counter_obj,test_counter);
static mp_obj_t signal_stats(mp_obj_t iq_obj) {
    mp_buffer_info_t iq;
    mp_get_buffer_raise(iq_obj,&iq,MP_BUFFER_READ);
    if (!bytes_type(iq.typecode) || (iq.len&1) || iq.len>65536)
        mp_raise_ValueError(MP_ERROR_TEXT("IQ byte buffer even <=65536"));
    fm_stats_result r=fm_stats(iq.buf,iq.len);
    mp_obj_t result[7]={mp_obj_new_int_from_uint(r.samples),
        mp_obj_new_int_from_uint(r.sum_i),mp_obj_new_int_from_uint(r.sum_q),
        mp_obj_new_int_from_uint(r.sumsq),mp_obj_new_int_from_uint(r.minimum),
        mp_obj_new_int_from_uint(r.maximum),mp_obj_new_int_from_uint(r.clipped)};
    return mp_obj_new_tuple(7,result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(signal_stats_obj,signal_stats);
mp_obj_t mpy_init(mp_obj_fun_bc_t *self,size_t n_args,size_t n_kw,mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY
    mp_store_global(MP_QSTR_process,MP_OBJ_FROM_PTR(&process_obj));
    mp_store_global(MP_QSTR_test_counter,MP_OBJ_FROM_PTR(&test_counter_obj));
    mp_store_global(MP_QSTR_signal_stats,MP_OBJ_FROM_PTR(&signal_stats_obj));
    MP_DYNRUNTIME_INIT_EXIT
}
