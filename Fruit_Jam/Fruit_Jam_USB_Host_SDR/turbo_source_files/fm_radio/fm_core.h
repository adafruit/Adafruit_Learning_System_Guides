// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
#ifndef FM_CORE_H
#define FM_CORE_H
#include <stdint.h>
#include <stddef.h>
#ifndef FM_TAPS
#define FM_TAPS 95
#endif
#define FM_STATE_BYTES 512
#define FM_MAGIC 0x464d3236u
typedef struct {
    uint32_t magic, head, phase, have_prev;
    float old_i, old_q, dc_i, dc_q, deemph, audio_dc;
    float history[FM_TAPS];
} fm_state;
typedef char fm_state_size_check[(sizeof(fm_state) <= FM_STATE_BYTES) ? 1 : -1];
typedef struct { int32_t last; uint32_t discontinuities, missing; } fm_counter_result;
typedef struct {
    uint32_t samples, sum_i, sum_q, sumsq, minimum, maximum, clipped;
} fm_stats_result;
static fm_stats_result fm_stats(const uint8_t *data,size_t len) {
    fm_stats_result r={(uint32_t)(len/2),0,0,0,len?255u:0u,0,0};
    for (size_t j=0;j<len;j+=2) {
        uint32_t i=data[j],q=data[j+1];
        r.sum_i+=i; r.sum_q+=q; r.sumsq+=i*i+q*q;
        if(i<r.minimum) r.minimum=i;
        if(q<r.minimum) r.minimum=q;
        if(i>r.maximum) r.maximum=i;
        if(q>r.maximum) r.maximum=q;
        r.clipped+=(i==0 || i==255)+(q==0 || q==255);
    }
    return r;
}
static fm_counter_result fm_count(const uint8_t *data,size_t len,int32_t previous) {
    fm_counter_result r={previous,0,0};
    for (size_t j=0;j<len;j++) {
        if (r.last>=0) {
            uint8_t skipped=(uint8_t)(data[j]-r.last-1);
            if (skipped) { r.discontinuities++; r.missing+=skipped; }
        }
        r.last=data[j];
    }
    return r;
}
#include "coefficients.h"

static float fm_abs(float x) { return __builtin_fabsf(x); }
// atan on [0,1], max error approximately 1.2e-5 radians.
static float fm_atan(float z) {
    float z2 = z*z;
    return z*(0.9998660f + z2*(-0.3302995f + z2*(0.1801410f + z2*(-0.0851330f + z2*0.0208351f))));
}
static float fm_angle(float y, float x) {
    float ax=fm_abs(x), ay=fm_abs(y), angle;
    if (ax == 0 && ay == 0) return 0;
    if (ax >= ay) angle=fm_atan(ay/ax);
    else angle=1.57079632679f-fm_atan(ax/ay);
    if (x < 0) angle=3.14159265359f-angle;
    return y < 0 ? -angle : angle;
}
static void fm_reset(fm_state *s) {
    s->magic=FM_MAGIC; s->head=0; s->phase=0; s->have_prev=0;
    s->old_i=0; s->old_q=0; s->dc_i=0; s->dc_q=0; s->deemph=0; s->audio_dc=0;
    for (unsigned j=0;j<FM_TAPS;j++) s->history[j]=0;
}
// Caller validates state, buffer sizes, non-overlap, and even input length.
static size_t fm_process(const uint8_t *restrict iq, size_t n, uint8_t *restrict pcm, fm_state *restrict s) {
    size_t written=0;
    unsigned head=s->head, phase=s->phase, have_prev=s->have_prev;
    float dc_i=s->dc_i, dc_q=s->dc_q, old_i=s->old_i, old_q=s->old_q;
    float audio_dc=s->audio_dc, deemph=s->deemph;
    for (size_t p=0;p<n;p+=2) {
        float i=(float)iq[p]-127.5f, q=(float)iq[p+1]-127.5f;
        dc_i += 0.0001f*(i-dc_i);
        dc_q += 0.0001f*(q-dc_q);
        i-=dc_i; q-=dc_q;
        float discr=0;
        if (have_prev) discr=fm_angle(q*old_i-i*old_q, i*old_i+q*old_q);
        old_i=i; old_q=q; have_prev=1;
        s->history[head]=discr;
        if (++head==FM_TAPS) head=0;
        if (++phase==8) {
            phase=0;
            float filtered=0;
            unsigned j=0;
            // Two linear spans retain the baseline sum order and remove
            // the per-tap circular-buffer wrap test.
            for (unsigned h=head;h>0;) filtered+=fm_coeff[j++]*s->history[--h];
            for (unsigned h=FM_TAPS;j<FM_TAPS;) filtered+=fm_coeff[j++]*s->history[--h];
            audio_dc += 0.003919300f*(filtered-audio_dc);
            filtered-=audio_dc;
            deemph += 0.340759370f*(filtered-deemph);
            float v=deemph*6518.98647f;
            // A user-corrupted floating state cannot trigger float-to-int UB.
            if (v!=v) v=0;
            if (v>32767) v=32767;
            if (v< -32768) v=-32768;
            int32_t sample=(int32_t)v;
            pcm[written++]=(uint8_t)sample;
            pcm[written++]=(uint8_t)((uint32_t)sample>>8);
        }
    }
    s->head=head; s->phase=phase; s->have_prev=have_prev;
    s->dc_i=dc_i; s->dc_q=dc_q; s->old_i=old_i; s->old_q=old_q;
    s->audio_dc=audio_dc; s->deemph=deemph;
    return written;
}
#endif
