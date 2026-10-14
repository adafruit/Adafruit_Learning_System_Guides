// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// Robot 36 SSTV decoder for recordings made by the receiver: 32 kHz signed
// 16-bit mono PCM (possibly wrapping around a ring buffer) in, a 320x240
// image out.
//
//   1. Tone frequency: mix 1700 Hz to 0, 128-tap low-pass, /4, FM
//      discriminator -> an 8 kHz track of the tone frequency in Hz.
//   2. Sync score at 2 kHz: fraction of the last 9 ms near 1200 Hz.
//   3. Line period and phase: fold the score at periods within +-1.5 % of
//      150 ms; the best fold is the receiver's actual line rate, which
//      removes slant from sample-rate error.
//   4. Line 0: from the VIS header if found (tone energies, below) and it
//      agrees with the sync phase, else the first real sync (a run of
//      them), else the last sync when the end of the image was received
//      (it is line 239).
//   5. Each line on its own sync (+-3 ms), median-smoothed over 7 lines, so
//      lost samples move the following lines with them.
//   6. Pixels: Y and the line's chroma (R-Y on even lines, B-Y on odd ones,
//      told apart by the separator tone), shared with the neighbour line,
//      converted with ITU-R BT.601.
//
// Work memory is supplied by the caller (see sstv_decode_work_bytes).
#ifndef SSTV_DECODE_H
#define SSTV_DECODE_H
#include <stdint.h>
#include <stddef.h>
#include "sstv_coeffs.h"

#define DEC_W 320
#define DEC_H 240
#define DEC_LINE_MS 150.0f
#define DEC_SYNC_MS 9.0f
#define DEC_Y_START_MS 12.0f
#define DEC_Y_MS 88.0f
#define DEC_SEP_START_MS 100.0f
#define DEC_SEP_MS 4.5f
#define DEC_C_START_MS 106.0f
#define DEC_C_MS 44.0f
#define DEC_VIS_CODE 8
#define DEC_MAX_SLOTS 400
// VIS search: 10 ms tone energies kept for the last DEC_VIS_HIST ms, up to
// DEC_VIS_CANDS candidate headers. The tone track lags the input by the
// low-pass delay, DEC_VIS_DELAY_MS.
#define DEC_VIS_HIST 640
#define DEC_VIS_CANDS 8
#define DEC_VIS_DELAY_MS ((SSTV_DEC_LP_TAPS - 1) / 2.0f / 32.0f)

typedef struct {
    int lines, first_line, vis, period_us, align;   // align: 0 phase, 1 vis, 2 first sync, 3 last sync
    int syncs;                                      // line syncs found (an image has up to 240)
} sstv_decode_info;

// Work memory: a state header, the 8 kHz track, the 2 kHz sync score,
// then float scratch (slots, line starts, residuals and jumps,
// the 1700 Hz table and the filter history).
#define DEC_FLOATS (DEC_MAX_SLOTS + 3 * DEC_H + 2 * 320 + 4 * SSTV_DEC_LP_TAPS)
#define DEC_MAGIC 0x52333644u   // "R36D"

typedef struct {
    uint32_t magic, stage;
    size_t ring_len, start, length;
    int n8, n2;
    // stage 0: tone track
    size_t pos;
    unsigned h, ph;
    int k;
    float pi_, pq;
    // stage 0: VIS tone energies (1100, 1200, 1300, 1900 Hz; see dec_vis_ms)
    unsigned vis_ph[4];                  // VIS tone phasor positions, 0..79
    float vis_p[4][2], vis_part[10][4][2], vis_n[4];
    float vis_hist[DEC_VIS_HIST][4];
    int vis_count, vis_last;
    int vis_end[DEC_VIS_CANDS];          // ms where the stop bit ends (track time)
    float vis_margin[DEC_VIS_CANDS];     // mean |log2| 1100/1300 Hz ratio of the bits
    // stage 2: period search
    float p, period, phase;
    int32_t best;
    // stage 3/4: lines
    float first;
    int skipped, nl, shift, row;
    sstv_decode_info info;
} dec_state;

typedef struct {
    int16_t *f;
    uint8_t *score;
    float *slot_v, *starts, *resid, *adjs, *cos_t, *sin_t, *hi, *hq;
} dec_arrays;

static size_t dec_align4(size_t x) { return (x + 3) & ~(size_t)3; }

// Work bytes for `samples` input samples (PCM bytes / 2).
static size_t sstv_decode_work_bytes(size_t samples) {
    size_t n8 = samples / 4, n2 = n8 / 4;
    return dec_align4(sizeof(dec_state)) + dec_align4(n8 * 2) + dec_align4(n2) + 4 * DEC_FLOATS + 16;
}

static dec_arrays dec_layout(uint8_t *work, const dec_state *st) {
    dec_arrays a;
    uint8_t *p = work + dec_align4(sizeof(dec_state));
    a.f = (int16_t *)p; p += dec_align4((size_t)st->n8 * 2);
    a.score = p; p += dec_align4((size_t)st->n2);
    float *fl = (float *)p;
    a.slot_v = fl; a.starts = a.slot_v + DEC_MAX_SLOTS; a.resid = a.starts + DEC_H; a.adjs = a.resid + DEC_H;
    a.cos_t = a.adjs + DEC_H; a.sin_t = a.cos_t + 320;
    a.hi = a.sin_t + 320; a.hq = a.hi + 2 * SSTV_DEC_LP_TAPS;
    return a;
}

static float dec_angle(float y, float x) {
    float ax = y < 0 ? -y : y, bx = x < 0 ? -x : x, a;
    if (ax == 0 && bx == 0) return 0;
    if (bx >= ax) { float z = ax / bx, z2 = z * z; a = z * (0.9998660f + z2 * (-0.3302995f + z2 * (0.1801410f + z2 * (-0.0851330f + z2 * 0.0208351f)))); }
    else { float z = bx / ax, z2 = z * z; a = 1.57079632679f - z * (0.9998660f + z2 * (-0.3302995f + z2 * (0.1801410f + z2 * (-0.0851330f + z2 * 0.0208351f)))); }
    if (x < 0) a = 3.14159265359f - a;
    return y < 0 ? -a : a;
}

// Median of up to 8 values (insertion sort of a copy).
static float dec_median(const float *v, int n) {
    float t[8];
    for (int i = 0; i < n; i++) {
        float x = v[i];
        int j = i;
        while (j > 0 && t[j - 1] > x) { t[j] = t[j - 1]; j--; }
        t[j] = x;
    }
    return n & 1 ? t[n / 2] : 0.5f * (t[n / 2 - 1] + t[n / 2]);
}

// Median of the int16 track over [a, b) by histogram (values 1000..2500 Hz
// in 10 Hz bins); returns 0 for an empty range.
static float dec_track_median(const int16_t *f, int a, int b) {
    uint16_t hist[152];
    for (int i = 0; i < 152; i++) hist[i] = 0;
    int n = 0;
    for (int i = a; i < b; i++) {
        int k = (f[i] - 1000) / 10;
        if (k < 0) k = 0;
        if (k > 151) k = 151;
        hist[k]++; n++;
    }
    if (!n) return 0;
    int half = (n + 1) / 2, acc = 0;
    for (int k = 0; k < 152; k++) {
        acc += hist[k];
        if (acc >= half) return 1000 + 10 * k + 5;
    }
    return 2500;
}

// Pixel value 0..255 from the 8 kHz track at time t (seconds), linear
// interpolation.
static float dec_value(const int16_t *f, int n8, float t) {
    float x = t * 8000.0f - 0.5f;
    int i = (int)x;
    if (x < 0 || i + 1 >= n8) return 0;
    float fr = x - i;
    float hz = f[i] + fr * (f[i + 1] - f[i]);
    return (hz - 1500.0f) * (255.0f / 800.0f);
}

static uint8_t dec_clip(float v) {
    if (!(v > 0)) return 0;
    if (v > 255) return 255;
    return (uint8_t)(v + 0.5f);
}

// log2 for positive x, piecewise linear between powers of two (error
// < 0.09), without libm.
static float dec_log2(float x) {
    union { float f; uint32_t u; } v = { x };
    return (float)((int)((v.u >> 23) & 255) - 127) + (float)(v.u & 0x7fffff) / 8388608.0f;
}

// VIS header: 300 ms leader at 1900 Hz, start bit (1200), 7 data bits LSB
// first and even parity (1100 = 1, 1300 = 0), stop bit (1200), 30 ms each.
// Weak signals make the tone track too noisy for this (FM clicks, and noise
// that is far from flat after de-emphasis), so it is found from tone
// energies instead: every ms, the 10 ms DFT power at each of the four tones
// (orthogonal over 10 ms, being 100 Hz apart), divided by that tone's
// running mean power so the noise floor tilt cancels. A 30 ms bit is the sum
// of three 10 ms windows. Called once per ms of track (`ms`), it tests the
// header that ends there: start and stop bits must be strongest at 1200 Hz,
// the bits must give code 8 with even parity, and at least 19 of the 29 10 ms
// windows of the leader must be strongest at 1900 Hz. Candidates within 40
// ms of each other keep the one with the clearest bits; dec_lines() takes
// the best one that agrees with the line sync phase.
static void dec_vis_ms(dec_state *st, int ms) {
    int slot = ms % 10, h = ms % DEC_VIS_HIST;
    float alpha = ms < 2000 ? 1.0f / (ms + 1) : 1.0f / 2000;
    for (int t = 0; t < 4; t++) {
        st->vis_part[slot][t][0] = st->vis_p[t][0];
        st->vis_part[slot][t][1] = st->vis_p[t][1];
        st->vis_p[t][0] = st->vis_p[t][1] = 0;
        float si = 0, sq = 0;
        for (int q = 0; q < 10 && q <= ms; q++) { si += st->vis_part[q][t][0]; sq += st->vis_part[q][t][1]; }
        float e = si * si + sq * sq;
        st->vis_n[t] += (e - st->vis_n[t]) * alpha;
        st->vis_hist[h][t] = st->vis_n[t] > 0 ? e / st->vis_n[t] : 0;
    }
    int j = ms - 299;                    // start bit begins
    if (j < 300) return;
    float (*e)[4] = st->vis_hist;
    #define VIS_BLOCK(v, s0) for (int t = 0; t < 4; t++) \
        v[t] = e[((s0) + 9) % DEC_VIS_HIST][t] + e[((s0) + 19) % DEC_VIS_HIST][t] + e[((s0) + 29) % DEC_VIS_HIST][t]
    float v[4];
    VIS_BLOCK(v, j);
    if (!(v[1] > v[0] && v[1] > v[2] && v[1] > v[3])) return;
    VIS_BLOCK(v, j + 270);
    if (!(v[1] > v[0] && v[1] > v[2] && v[1] > v[3])) return;
    int code = 0, ones = 0;
    float margin = 0;
    for (int b = 0; b < 8; b++) {
        VIS_BLOCK(v, j + 30 + 30 * b);
        int bit = v[0] > v[2];
        float r = dec_log2((v[0] + 1e-12f) / (v[2] + 1e-12f));
        margin += r < 0 ? -r : r;
        ones += bit;
        if (b < 7) code |= bit << b;
    }
    #undef VIS_BLOCK
    if (code != DEC_VIS_CODE || (ones & 1)) return;
    int lead = 0;
    for (int w = 0; w < 29; w++) {
        const float *x = e[(j - 291 + 10 * w) % DEC_VIS_HIST];
        lead += x[3] > x[0] && x[3] > x[1] && x[3] > x[2];
    }
    if (lead < 19) return;
    margin /= 8;
    int end = ms + 1;
    if (st->vis_count && end - st->vis_end[st->vis_last] < 40) {
        if (margin > st->vis_margin[st->vis_last]) { st->vis_end[st->vis_last] = end; st->vis_margin[st->vis_last] = margin; }
        return;
    }
    int k = st->vis_count;
    if (k == DEC_VIS_CANDS) {
        k = 0;
        for (int q = 1; q < DEC_VIS_CANDS; q++) if (st->vis_margin[q] < st->vis_margin[k]) k = q;
        if (st->vis_margin[k] >= margin) return;
    } else st->vis_count++;
    st->vis_end[k] = end;
    st->vis_margin[k] = margin;
    st->vis_last = k;
}

// Line 0 from the VIS candidates: the clearest one whose end is within 10 ms
// of a line sync on the fitted grid, moved onto that sync; -1 if none.
static float dec_pick_vis(const dec_state *st, float phase_s, float period_s) {
    float best = -1, best_m = -1;
    for (int k = 0; k < st->vis_count; k++) {
        float t = st->vis_end[k] / 1000.0f - DEC_VIS_DELAY_MS / 1000.0f;
        float x = (t - phase_s) / period_s;
        int n = (int)(x < 0 ? x - 0.5f : x + 0.5f);
        float d = t - (phase_s + n * period_s);
        if (d > -0.010f && d < 0.010f && st->vis_margin[k] > best_m) { best_m = st->vis_margin[k]; best = t - d; }
    }
    return best;
}

// Incremental decoding, so the caller can keep USB and the display serviced:
// sstv_decode_begin() once, then sstv_decode_step() until it returns 100.
// Each step does a bounded amount of work (tens of milliseconds on the
// RP2350). `work` must hold sstv_decode_work_bytes(length / 2) bytes,
// 4-byte aligned, and stay untouched between calls; ring, rgb565 and bgr
// must be the same buffers every call.

// Returns 0, or -1 if the recording is too short to decode.
static int sstv_decode_begin(uint8_t *work, size_t ring_len, size_t start, size_t length) {
    dec_state *st = (dec_state *)work;
    uint8_t *p = (uint8_t *)st;
    for (size_t j = 0; j < sizeof(dec_state); j++) p[j] = 0;
    st->ring_len = ring_len;
    st->start = start % ring_len;
    st->length = length;
    st->n8 = (int)(length / 2 / 4);
    st->n2 = st->n8 / 4;
    st->pos = st->start;
    st->p = DEC_LINE_MS * 2 * 0.985f;
    st->period = DEC_LINE_MS * 2;
    st->best = -1;
    st->magic = DEC_MAGIC;
    if (st->n8 < 8000) { st->stage = 5; return -1; }
    dec_arrays a = dec_layout(work, st);
    for (int k = 0; k < 320; k++) {
        float x = 6.28318530718f * k / 320.0f;
        if (x > 3.14159265359f) x -= 6.28318530718f;
        float sc = 1.0f, xx = x;
        if (xx > 1.57079632679f) { xx = 3.14159265359f - xx; sc = -1.0f; }
        else if (xx < -1.57079632679f) { xx = -3.14159265359f - xx; sc = -1.0f; }
        float x2 = xx * xx;
        a.sin_t[k] = xx * (1.0f + x2 * (-1.0f / 6 + x2 * (1.0f / 120 + x2 * (-1.0f / 5040 + x2 * (1.0f / 362880 + x2 * (-1.0f / 39916800))))));
        a.cos_t[k] = sc * (1.0f + x2 * (-0.5f + x2 * (1.0f / 24 + x2 * (-1.0f / 720 + x2 * (1.0f / 40320 + x2 * (-1.0f / 3628800))))));
    }
    for (int k = 0; k < 2 * SSTV_DEC_LP_TAPS; k++) a.hi[k] = a.hq[k] = 0;
    return 0;
}

// Stage 0: tone frequency track at 8 kHz, `outputs` samples per call. 1700
// Hz at 32 kHz repeats every 320 samples (17 turns), so the mixer is a table.
// The VIS tones are -600, -500, -400 and +200 Hz from 1700: at 8 kHz, -6,
// -5, -4 and +2 turns per 80 samples, so their DFT phasors are every 4th
// entry of the same table (positions in vis_ph, 0..79).
static void dec_track(dec_state *st, dec_arrays *a, const uint8_t *ring, int outputs) {
    const unsigned taps = SSTV_DEC_LP_TAPS;
    unsigned h = st->h, ph = st->ph;
    size_t pos = st->pos, ring_len = st->ring_len;
    float pi_ = st->pi_, pq = st->pq;
    int k = st->k, stop = k + outputs < st->n8 ? k + outputs : st->n8;
    const float *cs = a->cos_t, *sn = a->sin_t;
    float *hi = a->hi, *hq = a->hq;
    static const unsigned vis_step[4] = {74, 75, 76, 2};
    while (k < stop) {
        for (int r = 0; r < 4; r++) {
            float x = (float)(int16_t)(ring[pos] | (ring[pos + 1] << 8));
            pos += 2;
            if (pos >= ring_len) pos = 0;
            float i = x * cs[ph], q = -x * sn[ph];
            ph += 17;
            if (ph >= 320) ph -= 320;
            hi[h] = i; hi[h + taps] = i;
            hq[h] = q; hq[h + taps] = q;
            if (++h == taps) h = 0;
        }
        const float *wi = hi + h, *wq = hq + h;
        float ai = 0, aq = 0;
        for (unsigned t = 0; t < taps / 2; t++) {
            float c = sstv_dec_lp[t];
            ai += c * (wi[t] + wi[taps - 1 - t]);
            aq += c * (wq[t] + wq[taps - 1 - t]);
        }
        float d = dec_angle(aq * pi_ - ai * pq, ai * pi_ + aq * pq);
        pi_ = ai; pq = aq;
        float hz = 1700.0f + d * (8000.0f / 6.28318530718f);
        if (hz < 0) hz = 0;
        if (hz > 4000) hz = 4000;
        a->f[k++] = (int16_t)hz;
        // (ai + j aq) * exp(-j 2 pi pos / 80) for each VIS tone
        for (int t = 0; t < 4; t++) {
            unsigned q = st->vis_ph[t];
            float c = cs[4 * q], s = sn[4 * q];
            st->vis_p[t][0] += ai * c + aq * s;
            st->vis_p[t][1] += aq * c - ai * s;
            q += vis_step[t];
            st->vis_ph[t] = q >= 80 ? q - 80 : q;
        }
        if (!(k & 7)) dec_vis_ms(st, k / 8 - 1);
    }
    st->h = h; st->ph = ph; st->pos = pos; st->pi_ = pi_; st->pq = pq; st->k = k;
}

// Stage 1: undo the filter delay, then the 2 kHz sync score
// (fraction of the next 9 ms within 100 Hz of 1200 Hz).
static void dec_scores(dec_state *st, dec_arrays *a) {
    int n8 = st->n8, n2 = st->n2;
    int16_t *f = a->f;
    int delay = (int)((SSTV_DEC_LP_TAPS - 1) / 2 / 4);
    for (int j = 0; j + delay < n8; j++) f[j] = f[j + delay];
    for (int j = n8 - delay; j < n8; j++) f[j] = f[n8 - delay - 1];
    f[0] = f[1];
    int run = 0;
    uint8_t hist[18] = {0};
    for (int k = 0; k < n2; k++) {
        int acc = f[4 * k] + f[4 * k + 1] + f[4 * k + 2] + f[4 * k + 3];
        int near = acc > 4 * 1100 && acc < 4 * 1300;
        run += near - hist[k % 18];
        hist[k % 18] = (uint8_t)near;
        if (k >= 17) a->score[k - 17] = (uint8_t)(run * 255 / 18);
    }
    for (int k = n2 - 17 > 0 ? n2 - 17 : 0; k < n2; k++) a->score[k] = 0;
}

// Stage 2: one candidate period (0.5 ms units) per call: fold the score and
// keep the best period and phase. Returns 1 when all periods are done.
static int dec_period(dec_state *st, dec_arrays *a) {
    float p = st->p;
    int n2 = st->n2;
    int lines = (int)(n2 / p);
    if (p >= DEC_LINE_MS * 2 * 1.015f || lines < 3) return 1;
    int width = (int)p, bestj = 0;
    int32_t bestv = -1;
    for (int j = 0; j < width; j++) {
        int32_t acc = 0;
        for (int l = 0; l < lines; l++) {
            int idx = (int)(l * p) + j;
            if (idx < n2) acc += a->score[idx];
        }
        if (acc > bestv) { bestv = acc; bestj = j; }
    }
    if (bestv > st->best) { st->best = bestv; st->period = p; st->phase = (float)bestj; }
    st->p = p + 0.04f;
    return 0;
}

// Stage 3: VIS, line 0, every line's start and the chroma parity.
static void dec_lines(dec_state *st, dec_arrays *a) {
    int n8 = st->n8, n2 = st->n2;
    const int16_t *f = a->f;
    const uint8_t *score = a->score;
    float period_s = st->period / 2000.0f, phase_s = st->phase / 2000.0f;
    st->info.period_us = (int)(st->period * 500.0f + 0.5f);
    float vis = dec_pick_vis(st, phase_s, period_s);
    int nslots = 0;
    for (float t = phase_s; t * 2000 + 40 < n2 && nslots < DEC_MAX_SLOTS; t += period_s) {
        int lo = (int)((t - 0.003f) * 2000), hi = (int)((t + 0.003f) * 2000);
        if (lo < 0) lo = 0;
        int k = lo;
        for (int q = lo; q <= hi && q < n2; q++) if (score[q] > score[k]) k = q;
        // A line sync is followed by the 1500 Hz porch and picture; the VIS
        // stop bit (30 ms at 1200 Hz) is not.
        float after = dec_track_median(f, 4 * (k + 24), 4 * (k + 40) < n8 ? 4 * (k + 40) : n8);
        a->slot_v[nslots++] = after > 1400 ? score[k] / 255.0f : 0;
    }
    int k0 = -1, k1 = -1;
    for (int i = 0; i < nslots; i++) st->info.syncs += a->slot_v[i] > 0.5f;
    for (int i = 0; i < nslots; i++) {
        int on = 0;
        for (int q = i - 2; q <= i + 2; q++) if (q >= 0 && q < nslots && a->slot_v[q] > 0.5f) on++;
        if (on >= 3) { if (k0 < 0) k0 = i; k1 = i; }
    }
    float first;
    if (vis >= 0) { first = vis; st->info.vis = 1; st->info.align = 1; }
    else if (k0 >= 0) {
        first = phase_s + k0 * period_s; st->info.align = 2;
        if (k1 - k0 + 1 < DEC_H - 2 && k1 + 2 < nslots) {
            // The start is missing but the end was received: the last sync
            // is line 239.
            first = phase_s + (k1 - (DEC_H - 1)) * period_s; st->info.align = 3;
        }
    } else first = phase_s;

    // Each line's sync is looked for within +-3 ms of where the fitted
    // period puts it; if it is not there, within +-75 ms, and a sync found
    // there (lost samples, a jump) moves this and all later lines. The fine
    // part is median-smoothed over 7 lines.
    int skipped = 0, nl = 0;
    float adj = 0, total_s = n8 / 8000.0f;
    while (first + skipped * period_s < 0 && skipped < DEC_H) skipped++;
    while (skipped + nl < DEC_H) {
        float pred = first + period_s * (skipped + nl) + adj;
        if (pred + DEC_LINE_MS / 1000.0f > total_s + 1e-6f) break;
        int lo = (int)((pred - 0.003f) * 2000), hi = (int)((pred + 0.003f) * 2000);
        float fine = 0;
        if (lo >= 0 && hi < n2) {
            int k = lo;
            for (int q = lo; q <= hi; q++) if (score[q] > score[k]) k = q;
            if (score[k] > 153) {
                fine = k / 2000.0f - pred;
            } else {
                int wa = (int)((pred - 0.075f) * 2000), wb = (int)((pred + 0.075f) * 2000);
                if (wa < 0) wa = 0;
                if (wb > n2 - 41) wb = n2 - 41;
                int best = -1;
                for (int q = wa; q <= wb; q++)
                    if (score[q] > 153 && (best < 0 || score[q] > score[best])
                            && dec_track_median(f, 4 * (q + 24), 4 * (q + 40)) > 1400)
                        best = q;
                if (best >= 0) adj += best / 2000.0f - pred;
            }
        }
        a->resid[nl] = fine;
        a->adjs[nl] = adj;
        nl++;
    }
    for (int i = 0; i < nl; i++) {
        int lo = i - 3 < 0 ? 0 : i - 3, hi = i + 4 > nl ? nl : i + 4;
        a->starts[i] = first + period_s * (skipped + i) + a->adjs[i]
                       + (nl > 4 ? dec_median(a->resid + lo, hi - lo) : a->resid[i]);
    }
    // Parity from the separator tones (1500 Hz before R-Y, 2300 before B-Y).
    int agree = 0, count = 0;
    for (int i = 0; i < nl; i++) {
        int lo = (int)((a->starts[i] + (DEC_SEP_START_MS + 0.5f) / 1000.0f) * 8000);
        int hi = (int)((a->starts[i] + (DEC_SEP_START_MS + DEC_SEP_MS - 0.5f) / 1000.0f) * 8000);
        if (hi > n8 || lo < 0) continue;
        int odd = dec_track_median(f, lo, hi) > 1900;
        agree += odd == ((skipped + i) & 1);
        count++;
    }
    st->shift = count && agree * 2 < count;
    st->first = first;
    st->skipped = skipped;
    st->nl = nl;
    st->info.lines = nl;
    st->info.first_line = skipped;
}

// Stage 4: `rows` image rows per call. The even line of a pair carries R-Y,
// the odd one B-Y; both rows use both.
static void dec_pixels(dec_state *st, dec_arrays *a, int rows, uint8_t *rgb565, size_t stride, uint8_t *bgr) {
    int n8 = st->n8, skipped = st->skipped, nl = st->nl;
    const int16_t *f = a->f;
    int stop = st->row + rows < DEC_H ? st->row + rows : DEC_H;
    for (int row = st->row; row < stop; row++) {
        int i = row - skipped;
        uint8_t *o565 = rgb565 ? rgb565 + row * stride : NULL;
        uint8_t *obgr = bgr ? bgr + (DEC_H - 1 - row) * DEC_W * 3 : NULL;
        if (i < 0 || i >= nl) {
            for (int x = 0; x < DEC_W; x++) {
                if (o565) { o565[2 * x] = 0; o565[2 * x + 1] = 0; }
                if (obgr) { obgr[3 * x] = obgr[3 * x + 1] = obgr[3 * x + 2] = 0; }
            }
            continue;
        }
        int is_odd = (row + st->shift) & 1;
        int j = is_odd ? i - 1 : i + 1;
        int has_partner = j >= 0 && j < nl;
        for (int x = 0; x < DEC_W; x++) {
            float px = (x + 0.5f) / DEC_W;
            float y = dec_value(f, n8, a->starts[i] + (DEC_Y_START_MS + px * DEC_Y_MS) / 1000.0f);
            float own = dec_value(f, n8, a->starts[i] + (DEC_C_START_MS + px * DEC_C_MS) / 1000.0f);
            float other = has_partner ? dec_value(f, n8, a->starts[j] + (DEC_C_START_MS + px * DEC_C_MS) / 1000.0f) : 128;
            float cr = is_odd ? other : own, cb = is_odd ? own : other;
            if (y < 0) y = 0;
            if (y > 255) y = 255;
            if (cr < 0) cr = 0;
            if (cr > 255) cr = 255;
            if (cb < 0) cb = 0;
            if (cb > 255) cb = 255;
            float yy = 1.164f * (y - 16), r_ = cr - 128, b_ = cb - 128;
            uint8_t R = dec_clip(yy + 1.596f * r_);
            uint8_t G = dec_clip(yy - 0.813f * r_ - 0.392f * b_);
            uint8_t B = dec_clip(yy + 2.017f * b_);
            if (o565) {
                uint16_t v = (uint16_t)(((R & 0xf8) << 8) | ((G & 0xfc) << 3) | (B >> 3));
                o565[2 * x] = (uint8_t)v;
                o565[2 * x + 1] = (uint8_t)(v >> 8);
            }
            if (obgr) { obgr[3 * x] = B; obgr[3 * x + 1] = G; obgr[3 * x + 2] = R; }
        }
    }
    st->row = stop;
}

// One step. Returns progress 0..99, or 100 when the image is complete (then
// sstv_decode_result() has the details), or -1 if work is not a begun
// decode.
static int sstv_decode_step(uint8_t *work, const uint8_t *ring, uint8_t *rgb565, size_t stride, uint8_t *bgr) {
    dec_state *st = (dec_state *)work;
    if (st->magic != DEC_MAGIC) return -1;
    dec_arrays a = dec_layout(work, st);
    switch (st->stage) {
    case 0:   // ~1/16 of a 37 s recording per call
        dec_track(st, &a, ring, 4096);
        if (st->k >= st->n8) st->stage = 1;
        return 40 * st->k / st->n8;
    case 1:
        dec_scores(st, &a);
        st->stage = 2;
        return 45;
    case 2:
        for (int i = 0; i < 8; i++) {
            if (dec_period(st, &a)) { st->stage = 3; break; }
        }
        return 45 + (int)(35 * (st->p - DEC_LINE_MS * 2 * 0.985f) / (DEC_LINE_MS * 2 * 0.03f));
    case 3:
        dec_lines(st, &a);
        st->stage = (rgb565 || bgr) ? 4 : 5;
        return 85;
    case 4:
        dec_pixels(st, &a, 16, rgb565, stride, bgr);
        if (st->row >= DEC_H) st->stage = 5;
        return 85 + 14 * st->row / DEC_H;
    default:
        return 100;
    }
}

static sstv_decode_info sstv_decode_result(const uint8_t *work) {
    return ((const dec_state *)work)->info;
}

#endif
