// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// HF SSTV decoder for recordings in the receiver's ring: 8 kHz signed 16-bit
// mono PCM (possibly wrapping around the ring), a known mode, and if known
// the VIS position and the tuning offset (from the live detector):
//
//   0. Sync score at 2 kHz: share of the power that is the sync tone over
//      the mode's sync length (coherent 3 ms sub-blocks; tone 1200 + offset,
//      or the best of 1100..1300 Hz if the offset is unknown).
//   1. Candidate syncs: local maxima of the score.
//   2. Line period and phase: circular histogram of the candidates' times
//      over periods within +-1.5 % of nominal (coarse, then fine).
//   3. Line 0 from the VIS (snapped onto the grid), the first sync of a run
//      or the last one (when the end was received); each line on its own
//      sync near the grid (median-smoothed residuals; jumps from lost
//      samples followed). Tuning offset: from the VIS leader if there was
//      one, else from the line syncs' tone. Robot 36 parity from its
//      separator tones.
//   4. Pixels, one scan line per step: the tone track is recomputed from the
//      ring around the line, and each pixel is the power-weighted mean
//      frequency over its duration (angle of sum z[n] conj(z[n-1])) minus
//      the offset. Colour per mode family (GBR, PD YCrCb pairs, Robot 36).
//
// Two passes over the ring instead of keeping the tone track: work memory
// is the score (1 byte per 0.5 ms) plus about 100 KB.
#ifndef HF_DECODE_H
#define HF_DECODE_H
#include "hf_common.h"

#define DEC_MAGIC 0x48464443u      // "HFDC"
#define DEC_CANDS 4096
#define DEC_CELLS 2200             // > longest period (Scottie DX, 2100 bins) * 1.015
#define DEC_SLOTS 4096
#define DEC_LINES 256              // most scan lines of any mode
#define DEC_NHYP 5
#define DEC_WMAX 40
#define DEC_OFF_N 61               // sync tone offsets -150..150 Hz, 5 Hz apart
#define DEC_LEAD_N 41              // leader offsets -40..40 Hz, 2 Hz apart
#define DEC_PERIODS_PER_STEP 24

typedef struct {
    int mode, lines, first_line, vis, period_us, align, syncs, offset_hz;   // align: 0 phase, 1 vis, 2 first sync, 3 last sync
} hf_decode_info;

typedef struct {
    uint32_t magic, stage;
    size_t ring_len, start, length;
    int mode, K, n8, n2, span;
    int off_known, vis_known;
    long vis_pos;                  // samples from the start
    float offset;
    int disp_w, disp_h, ow, oh, ox, oy;
    // stage 0
    long pos;
    hf_front fe;
    int nhyp;
    uint32_t gi[DEC_NHYP], gk[DEC_NHYP];
    float ph[2], step[2];          // rotating phasor (known offset)
    float acc[DEC_NHYP][2], pacc;
    float part[HF_SUB][DEC_NHYP][2], ppart[HF_SUB];
    float sub_e[DEC_WMAX][DEC_NHYP], sub_p[DEC_WMAX];
    int bin;
    // stage 1
    int thr, ncand, scan;
    // stage 2
    int n_lines, fine, pi, pcount;
    float lo, hi, step_c, step_f, pbase;
    float best_v, best_p, best_ph, period, phase;
    // stage 3
    float first, scale;
    int skipped, nl, shift, oline;
    // stage 4
    int row, sub, agree, count;
    hf_decode_info info;
} hf_dec;

typedef struct {
    uint8_t *score, *on;
    int32_t *cand_t;
    uint8_t *cand_w;
    int32_t *hist;
    float *starts, *resid, *adjs, *sep, *off_acc;
    float *pre;                    // complex prefix sums of the line's z[n] conj(z[n-1])
    float *chan;                   // 4 x 640 channel values, then 640 for a partner line
} hf_dec_arrays;

static size_t hf_align4(size_t x) { return (x + 3) & ~(size_t)3; }

// Samples of track needed around one scan line (all channels, Robot 36's
// separator, the filter warm-up and margins), at up to +1.5 % clock error.
static int hf_dec_span(const hf_mode *m) {
    float lo = 0, hi = 0;
    for (int c = 0; c < m->nchan; c++) {
        if (m->ch[c].start < lo) lo = m->ch[c].start;
        if (m->ch[c].start + m->ch[c].dur > hi) hi = m->ch[c].start + m->ch[c].dur;
    }
    return (int)((hi - lo) * 1.016f * 8) + 80;
}

static size_t hf_decode_work_bytes(int mode, size_t samples) {
    size_t n2 = samples / HF_BIN;
    const hf_mode *m = &hf_modes[mode];
    return hf_align4(sizeof(hf_dec)) + hf_align4(n2) + DEC_SLOTS + DEC_CANDS * 5 + DEC_CELLS * 4
           + 4 * (4 * DEC_LINES + DEC_OFF_N) + 8 * ((size_t)hf_dec_span(m) + 2) + 4 * 5 * 640 + 16;
}

static hf_dec_arrays hf_dec_layout(uint8_t *work, const hf_dec *st) {
    hf_dec_arrays a;
    uint8_t *p = work + hf_align4(sizeof(hf_dec));
    a.score = p; p += hf_align4((size_t)st->n2);
    a.on = p; p += DEC_SLOTS;
    a.cand_t = (int32_t *)p; p += DEC_CANDS * 4;
    a.cand_w = p; p += DEC_CANDS;
    a.hist = (int32_t *)p; p += DEC_CELLS * 4;
    float *f = (float *)p;
    a.starts = f; a.resid = f + DEC_LINES; a.adjs = f + 2 * DEC_LINES; a.sep = f + 3 * DEC_LINES;
    a.off_acc = f + 4 * DEC_LINES;
    a.pre = a.off_acc + DEC_OFF_N;
    a.chan = a.pre + 2 * ((size_t)st->span + 2);
    return a;
}

// Returns 0, or -1 if the recording is too short.
static int hf_decode_begin(uint8_t *work, size_t ring_len, size_t start, size_t length, int mode,
                           int off_known, int offset, long vis_pos, int disp_w, int disp_h) {
    hf_dec *st = (hf_dec *)work;
    uint8_t *p = (uint8_t *)st;
    for (size_t j = 0; j < sizeof(hf_dec); j++) p[j] = 0;
    const hf_mode *m = &hf_modes[mode];
    st->ring_len = ring_len;
    st->start = start % ring_len;
    st->length = length;
    st->mode = mode;
    st->K = hf_sync_bins(m);
    st->n8 = (int)(length / 2);
    st->n2 = st->n8 / HF_BIN;
    st->span = hf_dec_span(m);
    st->off_known = off_known;
    st->offset = off_known ? (float)offset : 0;
    st->vis_known = vis_pos >= 0;
    st->vis_pos = vis_pos;
    st->info.mode = mode;
    st->disp_w = disp_w; st->disp_h = disp_h;
    // Fit the image into the display area, keeping its shape.
    if (disp_w > 0 && disp_h > 0) {
        if ((long)disp_w * m->height <= (long)disp_h * m->width) {
            st->ow = disp_w; st->oh = (int)((long)disp_w * m->height / m->width);
        } else {
            st->oh = disp_h; st->ow = (int)((long)disp_h * m->width / m->height);
        }
        st->ox = (disp_w - st->ow) / 2;
        st->oy = (disp_h - st->oh) / 2;
    }
    hf_front_reset(&st->fe);
    st->nhyp = off_known ? 1 : DEC_NHYP;
    for (int h = 0; h < DEC_NHYP; h++) st->gk[h] = hf_grid_k(1100 + 50 * h);
    st->ph[0] = 1; st->ph[1] = 0;
    hf_sincos(-HF_TWO_PI * (1200 + offset - HF_MIX) / HF_RATE, &st->step[0], &st->step[1]);
    st->magic = DEC_MAGIC;
    if (st->n2 < 4 * st->K + 2000) { st->stage = 9; return -1; }
    hf_dec_arrays a = hf_dec_layout(work, st);
    for (int k = 0; k < st->n2; k++) a.score[k] = 0;
    return 0;
}

// ------------------------------------------------------------- stage 0

static void hf_dec_bin(hf_dec *st, hf_dec_arrays *a) {
    int b = st->bin++, K = st->K, w = K - HF_SUB + 1, nh = st->nhyp;
    unsigned slot = (unsigned)b % HF_SUB;
    for (int h = 0; h < nh; h++) {
        st->part[slot][h][0] = st->acc[h][0]; st->part[slot][h][1] = st->acc[h][1];
        st->acc[h][0] = st->acc[h][1] = 0;
    }
    st->ppart[slot] = st->pacc;
    st->pacc = 0;
    if (b < HF_SUB - 1) return;
    int s = b - (HF_SUB - 1);
    unsigned ws = (unsigned)s % (unsigned)w;
    float pw = 0;
    for (int q = 0; q < HF_SUB; q++) pw += st->ppart[q];
    st->sub_p[ws] = pw;
    for (int h = 0; h < nh; h++) {
        float re = 0, im = 0;
        for (int q = 0; q < HF_SUB; q++) { re += st->part[q][h][0]; im += st->part[q][h][1]; }
        st->sub_e[ws][h] = (re * re + im * im) / (HF_SUB * HF_ZPB);
    }
    if (s < w - 1) return;
    int bs = s - (w - 1);
    float den = 0, num = 0;
    for (int q = 0; q < w; q++) den += st->sub_p[q];
    for (int h = 0; h < nh; h++) {
        float acc = 0;
        for (int q = 0; q < w; q++) acc += st->sub_e[q][h];
        if (acc > num) num = acc;
    }
    float sc = num / (den > 1e-9f ? den : 1e-9f);
    if (sc > 1) sc = 1;
    if (bs < st->n2) a->score[bs] = (uint8_t)(sc * 255 + 0.5f);
}

static void hf_dec_scores(hf_dec *st, hf_dec_arrays *a, const uint8_t *ring, int samples) {
    long stop = st->pos + samples < st->n2 * HF_BIN ? st->pos + samples : (long)st->n2 * HF_BIN;
    int nh = st->nhyp, known = st->off_known;
    // Work on stack copies: the decoder state is in PSRAM.
    hf_front fe = st->fe;
    float acc[DEC_NHYP][2], ph0 = st->ph[0], ph1 = st->ph[1], s0 = st->step[0], s1 = st->step[1], pacc = st->pacc;
    uint32_t gi[DEC_NHYP], gk[DEC_NHYP];
    for (int h = 0; h < DEC_NHYP; h++) { acc[h][0] = st->acc[h][0]; acc[h][1] = st->acc[h][1]; gi[h] = st->gi[h]; gk[h] = st->gk[h]; }
    long pos = st->pos;
    while (pos < stop) {
        hf_front_push(&fe, hf_ring_sample(ring, st->ring_len, st->start, st->length, pos));
        // Odd-numbered samples only (as the detector): z needs no more than 4 kHz.
        float zr = 0, zi = 0;
        int use = (int)(pos & 1);
        if (use) {
            hf_front_out(&fe, &zr, &zi);
            pacc += zr * zr + zi * zi;
        }
        if (known) {
            if (use) {
                acc[0][0] += zr * ph0 - zi * ph1;
                acc[0][1] += zr * ph1 + zi * ph0;
            }
            float t = ph0 * s0 - ph1 * s1;
            ph1 = ph0 * s1 + ph1 * s0;
            ph0 = t;
        } else {
            for (int h = 0; h < nh; h++) {
                if (use) {
                    const float *r = hf_rot160[gi[h]];
                    acc[h][0] += zr * r[0] - zi * r[1];
                    acc[h][1] += zr * r[1] + zi * r[0];
                }
                unsigned q = gi[h] + gk[h];
                gi[h] = q >= 160 ? q - 160 : q;
            }
        }
        pos++;
        if (!(pos & 3)) {
            if (known) {
                float n = ph0 * ph0 + ph1 * ph1;
                n = 1.5f - 0.5f * n;         // one Newton step towards |ph| = 1
                ph0 *= n; ph1 *= n;
            }
            for (int h = 0; h < nh; h++) { st->acc[h][0] = acc[h][0]; st->acc[h][1] = acc[h][1]; acc[h][0] = acc[h][1] = 0; }
            st->pacc = pacc;
            pacc = 0;
            hf_dec_bin(st, a);
        }
    }
    st->fe = fe;
    st->ph[0] = ph0; st->ph[1] = ph1; st->pacc = pacc; st->pos = pos;
    for (int h = 0; h < DEC_NHYP; h++) { st->acc[h][0] = acc[h][0]; st->acc[h][1] = acc[h][1]; st->gi[h] = gi[h]; }
}

// ------------------------------------------------------------- stage 1

// Local maxima of the score >= thr (largest within +-K/2, first of equals),
// from bin st->scan, up to `count` bins. Returns 1 when done, -1 on overflow.
static int hf_dec_candidates(hf_dec *st, hf_dec_arrays *a, int count) {
    int n = st->n2, r = st->K / 2 > 1 ? st->K / 2 : 1;
    int stop = st->scan + count < n ? st->scan + count : n;
    const uint8_t *sc = a->score;
    for (int b = st->scan; b < stop; b++) {
        int v = sc[b];
        if (v < st->thr) continue;
        int lo = b - r < 0 ? 0 : b - r, hi = b + r + 1 > n ? n : b + r + 1, ok = 1;
        for (int q = lo; q < hi && ok; q++) {
            if (sc[q] > v || (q < b && sc[q] == v)) ok = 0;
        }
        if (!ok) continue;
        if (st->ncand == DEC_CANDS) return -1;
        a->cand_t[st->ncand] = b;
        a->cand_w[st->ncand] = (uint8_t)v;
        st->ncand++;
    }
    st->scan = stop;
    return stop >= n;
}

// ------------------------------------------------------------- stage 2

// Fold the candidates at period p with histogram cells `cell` bins wide;
// keep it if better.
static void hf_dec_fold(hf_dec *st, hf_dec_arrays *a, float p, float cell) {
    int ncell = (int)(p / cell);
    if (ncell > DEC_CELLS) ncell = DEC_CELLS;
    if (ncell < 2) return;
    int32_t *h = a->hist;
    for (int i = 0; i < ncell; i++) h[i] = 0;
    for (int c = 0; c < st->ncand; c++) {
        float t = (float)a->cand_t[c];
        float ph = t - (float)hf_floor(t / p) * p;
        int idx = (int)(ph / cell);
        if (idx >= ncell) idx = ncell - 1;
        if (idx < 0) idx = 0;
        h[idx] += a->cand_w[c];
    }
    int bi = 0;
    int32_t bv = -1;
    for (int i = 0; i < ncell; i++) {
        int32_t v = h[i] + h[i + 1 < ncell ? i + 1 : 0];
        if (v > bv) { bv = v; bi = i; }
    }
    if ((float)bv <= st->best_v) return;
    // Phase: weighted circular mean of the two cells' members.
    int i2 = bi + 1 < ncell ? bi + 1 : 0;
    float base = bi * cell, sw = 0, sd = 0;
    for (int c = 0; c < st->ncand; c++) {
        float t = (float)a->cand_t[c];
        float ph = t - (float)hf_floor(t / p) * p;
        int idx = (int)(ph / cell);
        if (idx >= ncell) idx = ncell - 1;
        if (idx < 0) idx = 0;
        if (idx != bi && idx != i2) continue;
        float d = ph - base + p / 2;
        d = d - (float)hf_floor(d / p) * p - p / 2;
        sw += a->cand_w[c];
        sd += a->cand_w[c] * d;
    }
    float phase = base + (sw > 0 ? sd / sw : 0);
    phase -= (float)hf_floor(phase / p) * p;
    st->best_v = (float)bv; st->best_p = p; st->best_ph = phase;
}

// ------------------------------------------------------------- stage 3

// Maximum of score[a..b] (first of equals) and a parabola's sub-bin offset;
// returns -1 if the range is empty.
static int hf_dec_peak(const uint8_t *score, int n, int a, int b, float *frac) {
    if (a < 0) a = 0;
    if (b > n - 1) b = n - 1;
    *frac = 0;
    if (b < a) return -1;
    int k = a;
    for (int q = a + 1; q <= b; q++) if (score[q] > score[k]) k = q;
    if (k > 0 && k < n - 1) {
        float y0 = score[k - 1], y1 = score[k], y2 = score[k + 1], den = y0 - 2 * y1 + y2;
        if (den < 0) {
            float f = 0.5f * (y0 - y2) / den;
            *frac = f > 0.5f ? 0.5f : f < -0.5f ? -0.5f : f;
        }
    }
    return k;
}

static float hf_dec_median(const float *v, int n) {
    float t[8];
    for (int i = 0; i < n; i++) {
        float x = v[i];
        int j = i;
        while (j > 0 && t[j - 1] > x) { t[j] = t[j - 1]; j--; }
        t[j] = x;
    }
    return n & 1 ? t[n / 2] : 0.5f * (t[n / 2 - 1] + t[n / 2]);
}

static void hf_dec_lines(hf_dec *st, hf_dec_arrays *a) {
    const hf_mode *m = &hf_modes[st->mode];
    const uint8_t *score = a->score;
    int n2 = st->n2, K = st->K, lines = m->lines;
    float period = st->period, phase = st->phase;
    float dz = HF_LP_DELAY / HF_BIN;
    st->scale = period / (m->line_ms * 2);
    st->info.period_us = hf_round(period * 500.0f);
    // Slots on the grid that hold a sync.
    int nslots = 0;
    for (float t = phase; t + K < n2 && nslots < DEC_SLOTS; t += period) {
        float fr;
        int c = hf_round(t);
        int k = hf_dec_peak(score, n2, c - 6, c + 6, &fr);
        a->on[nslots++] = k >= 0 && score[k] > 128;
    }
    int k0 = -1, k1 = -1;
    for (int i = 0; i < nslots; i++) st->info.syncs += a->on[i];
    for (int i = 0; i < nslots; i++) {
        int on = 0;
        for (int q = i - 2; q <= i + 2; q++) if (q >= 0 && q < nslots) on += a->on[q];
        if (on >= 3) { if (k0 < 0) k0 = i; k1 = i; }
    }
    float first;
    if (st->vis_known) {
        float v = st->vis_pos / 4.0f + dz + m->vis_to_sync0 * 2 * st->scale;
        float x = (v - phase) / period;
        int n = hf_round(x);
        float d = v - (phase + n * period);
        first = d < 20 && d > -20 ? v - d : v;
        st->info.vis = 1; st->info.align = 1;
    } else if (k0 >= 0) {
        first = phase + k0 * period; st->info.align = 2;
        if (k1 - k0 + 1 < lines - 2 && k1 + 2 < nslots) {
            first = phase + (k1 - (lines - 1)) * period; st->info.align = 3;
        }
    } else first = phase;
    int skipped = 0, nl = 0;
    float adj = 0;
    while (first + skipped * period < 0 && skipped < lines) skipped++;
    while (skipped + nl < lines) {
        float pred = first + period * (skipped + nl) + adj;
        if (pred + K > n2) break;
        int c = hf_round(pred);
        float d = 0, fr;
        if (c - 6 >= 0 && c + 6 < n2) {
            int k = hf_dec_peak(score, n2, c - 6, c + 6, &fr);
            if (score[k] > 153) {
                d = k + fr - pred;
            } else {
                int k2 = hf_dec_peak(score, n2, hf_round(pred - 150), hf_round(pred + 150), &fr);
                if (k2 >= 0 && score[k2] > 191) adj += k2 + fr - pred;
            }
        }
        a->resid[nl] = d;
        a->adjs[nl] = adj;
        nl++;
    }
    for (int i = 0; i < nl; i++) {
        int lo = i - 3 < 0 ? 0 : i - 3, hi = i + 4 > nl ? nl : i + 4;
        // In input bins (the score lags by the filter delay).
        a->starts[i] = first + period * (skipped + i) + a->adjs[i]
                       + (nl > 4 ? hf_dec_median(a->resid + lo, hi - lo) : a->resid[i]) - dz - m->sync_bias;
    }
    st->first = first - dz;
    st->skipped = skipped;
    st->nl = nl;
    st->info.lines = nl;
    st->info.first_line = skipped;
}

// z for input samples [a0, a0 + n) into pre as the complex prefix sums of
// r[k] = z[k] conj(z[k-1]) (r[0] = 0): pre[2i..] = sum of r[0..i-1].
// Samples outside the recording are 0.
static void hf_dec_track(hf_dec *st, hf_dec_arrays *a, const uint8_t *ring, long a0, int n) {
    hf_front fe;
    hf_front_reset(&fe);
    float *pre = a->pre, pr = 0, pi_ = 0, sr = 0, si = 0;
    pre[0] = pre[1] = 0;
    for (int i = 0; i < n; i++) {
        float zr, zi;
        hf_front_step(&fe, hf_ring_sample(ring, st->ring_len, st->start, st->length, a0 + i), &zr, &zi);
        float rr = 0, ri = 0;
        if (i) { rr = zr * pr + zi * pi_; ri = zi * pr - zr * pi_; }
        sr += rr; si += ri;
        pre[2 * (i + 1)] = sr; pre[2 * (i + 1) + 1] = si;
        pr = zr; pi_ = zi;
    }
}

// The prefix sum at position pos (z samples, fractional) of a track of n.
static inline void hf_dec_prefix(const float *pre, int n, float pos, float *re, float *im) {
    if (pos < 0) pos = 0;
    if (pos > n) pos = (float)n;
    int i = (int)pos;
    if (i > n - 1) i = n - 1;
    float f = pos - i;
    // r[i] = pre[i+1] - pre[i]
    float rr = pre[2 * i + 2] - pre[2 * i], ri = pre[2 * i + 3] - pre[2 * i + 1];
    *re = pre[2 * i] + f * rr;
    *im = pre[2 * i + 1] + f * ri;
}

// Tone (Hz, offset removed) over [t0, t0 + dur) seconds-in-samples, of the
// track that starts at input sample a0.
static float hf_dec_hz(hf_dec *st, const float *pre, int n, long a0, float s0, float s1) {
    float ar, ai, br, bi;
    hf_dec_prefix(pre, n, s0 - a0 + HF_LP_DELAY, &ar, &ai);
    hf_dec_prefix(pre, n, s1 - a0 + HF_LP_DELAY, &br, &bi);
    return HF_MIX + hf_angle(bi - ai, br - ar) * (HF_RATE / HF_TWO_PI) - st->offset;
}

// Track span for a line whose sync starts at input sample `sync`, covering
// channels lo..hi ms; returns a0 and sets *n.
static long hf_dec_line_track(hf_dec *st, hf_dec_arrays *a, const uint8_t *ring, float sync, float lo_ms, float hi_ms, int *n) {
    long aa = (long)hf_floor(sync + lo_ms * st->scale * 8) - 2;
    float bf = sync + hi_ms * st->scale * 8;
    long b = (long)hf_floor(bf);
    if ((float)b < bf) b++;
    b += 2;
    long a0 = aa - 40 < 0 ? 0 : aa - 40;
    int len = (int)(b + 16 - a0);
    if (len > st->span) len = st->span;
    if (len < 2) len = 2;
    hf_dec_track(st, a, ring, a0, len);
    *n = len;
    return a0;
}

// Tuning offset: DFT power of z at (base + d) Hz, d = d0 + i * dstep for
// i < nd (nd <= DEC_OFF_N), over input samples [aa, bb) of the recording,
// added to acc. The front end starts 40 samples early and
// the first 40 + 15 outputs are dropped.
static void hf_dec_tone_power(hf_dec *st, const uint8_t *ring, long aa, long bb, float base, float d0, float dstep,
                              int nd, float *acc) {
    if (aa < 40 || bb - aa < 4) return;
    hf_front fe;
    hf_front_reset(&fe);
    float ph[DEC_OFF_N][2], stp[DEC_OFF_N][2], sum[DEC_OFF_N][2];
    for (int k = 0; k < nd; k++) {
        hf_sincos(-HF_TWO_PI * (base + d0 + k * dstep - HF_MIX) / HF_RATE, &stp[k][0], &stp[k][1]);
        ph[k][0] = 1; ph[k][1] = 0; sum[k][0] = sum[k][1] = 0;
    }
    long a0 = aa - 40;
    int skip = 40 + (int)HF_LP_DELAY, n = (int)(bb - aa);
    for (int i = 0; i < skip + n; i++) {
        float zr, zi;
        hf_front_step(&fe, hf_ring_sample(ring, st->ring_len, st->start, st->length, a0 + i), &zr, &zi);
        if (i < skip) continue;
        for (int k = 0; k < nd; k++) {
            float pr = ph[k][0], pi_ = ph[k][1];
            sum[k][0] += zr * pr - zi * pi_;
            sum[k][1] += zr * pi_ + zi * pr;
            ph[k][0] = pr * stp[k][0] - pi_ * stp[k][1];
            ph[k][1] = pr * stp[k][1] + pi_ * stp[k][0];
        }
    }
    for (int k = 0; k < nd; k++) acc[k] += sum[k][0] * sum[k][0] + sum[k][1] * sum[k][1];
}

static float hf_dec_parabola_peak(const float *acc, int n, float d0, float dstep) {
    int i = 0;
    for (int k = 1; k < n; k++) if (acc[k] > acc[i]) i = k;
    float frac = 0;
    if (i > 0 && i < n - 1) {
        float den = acc[i - 1] - 2 * acc[i] + acc[i + 1];
        if (den < 0) frac = 0.5f * (acc[i - 1] - acc[i + 1]) / den;
    }
    return d0 + dstep * (i + frac);
}

// ------------------------------------------------------------- stage 4

static uint8_t hf_clip(float v) {
    if (!(v > 0)) return 0;
    if (v > 255) return 255;
    return (uint8_t)(v + 0.5f);
}

// Values (0..255, unclipped) of channel c of one scan line into out[x]. The
// track is computed around that channel only: the front end is a FIR, so
// with 40+ samples of warm-up the result is the same as for the whole line.
static void hf_dec_channel(hf_dec *st, hf_dec_arrays *a, const uint8_t *ring, int line, int c, float *out) {
    const hf_mode *m = &hf_modes[st->mode];
    const hf_chan *ch = &m->ch[c];
    float sync = a->starts[line - st->skipped] * HF_BIN;
    int n;
    long a0 = hf_dec_line_track(st, a, ring, sync, ch->start, ch->start + ch->dur, &n);
    float t0 = sync + ch->start * st->scale * 8, w = m->width;
    float px = ch->dur * st->scale * 8 / w;
    float pr, pim;
    hf_dec_prefix(a->pre, n, t0 - a0 + HF_LP_DELAY, &pr, &pim);
    for (int x = 0; x < m->width; x++) {
        float qr, qi;
        hf_dec_prefix(a->pre, n, t0 + (x + 1) * px - a0 + HF_LP_DELAY, &qr, &qi);
        float hz = HF_MIX + hf_angle(qi - pim, qr - pr) * (HF_RATE / HF_TWO_PI) - st->offset;
        out[x] = (hz - 1500.0f) * (255.0f / 800.0f);
        pr = qr; pim = qi;
    }
}

// Display rows d whose source row is r: d in [d0, d1).
static void hf_dec_disp_rows(hf_dec *st, int r, int *d0, int *d1) {
    const hf_mode *m = &hf_modes[st->mode];
    int H = m->height, oh = st->oh;
    // source row of display row d: ((2d+1) H) / (2 oh)
    int lo = (int)((long)r * oh / H) - 1, hi = (int)((long)(r + 1) * oh / H) + 1;
    if (lo < 0) lo = 0;
    if (hi > oh) hi = oh;
    *d0 = -1; *d1 = -1;
    for (int d = lo; d < hi; d++) {
        if ((int)((2L * d + 1) * H / (2L * oh)) == r) { if (*d0 < 0) *d0 = d; *d1 = d + 1; }
    }
}

// Writes image row r (R, G, B arrays of width) to bgr and the display.
static void hf_dec_row(hf_dec *st, int r, const uint8_t *rgb, uint8_t *bgr, uint8_t *rgb565) {
    const hf_mode *m = &hf_modes[st->mode];
    int W = m->width;
    if (bgr) {
        uint8_t *o = bgr + (size_t)(m->height - 1 - r) * W * 3;
        for (int x = 0; x < W; x++) { o[3 * x] = rgb[3 * x + 2]; o[3 * x + 1] = rgb[3 * x + 1]; o[3 * x + 2] = rgb[3 * x]; }
    }
    if (rgb565 && st->oh > 0) {
        int d0, d1;
        hf_dec_disp_rows(st, r, &d0, &d1);
        for (int d = d0; d >= 0 && d < d1; d++) {
            uint8_t *o = rgb565 + ((size_t)(st->oy + d) * st->disp_w + st->ox) * 2;
            for (int x = 0; x < st->ow; x++) {
                int xi = (int)((2L * x + 1) * W / (2L * st->ow));
                const uint8_t *c = rgb + 3 * xi;
                uint16_t v = (uint16_t)(((c[0] & 0xf8) << 8) | ((c[1] & 0xfc) << 3) | (c[2] >> 3));
                o[2 * x] = (uint8_t)v; o[2 * x + 1] = (uint8_t)(v >> 8);
            }
        }
    }
}

static void hf_ycc(float y, float cb, float cr, uint8_t *o) {
    if (y < 0) y = 0;
    if (y > 255) y = 255;
    if (cb < 0) cb = 0;
    if (cb > 255) cb = 255;
    if (cr < 0) cr = 0;
    if (cr > 255) cr = 255;
    float yy = 1.164f * (y - 16), r_ = cr - 128, b_ = cb - 128;
    o[0] = hf_clip(yy + 1.596f * r_);
    o[1] = hf_clip(yy - 0.813f * r_ - 0.392f * b_);
    o[2] = hf_clip(yy + 2.017f * b_);
}

// One channel of one scan line per call; the last one also writes the
// line's image rows (1, or 2 for PD). Robot 36 takes three: Y, its chroma
// and the partner line's chroma. Advances st->row when the line is done.
static void hf_dec_pixels(hf_dec *st, hf_dec_arrays *a, const uint8_t *ring, uint8_t *rgb565, uint8_t *bgr) {
    const hf_mode *m = &hf_modes[st->mode];
    int L = st->row, W = m->width;
    uint8_t rgb[640 * 3];
    float *ch = a->chan;
    if (W < 1 || W > 640) return;
    int have = L >= st->skipped && L < st->skipped + st->nl;
    if (!have) {
        for (int x = 0; x < 3 * W; x++) rgb[x] = 0;
        for (int r = 0; r < m->rows; r++) hf_dec_row(st, L * m->rows + r, rgb, bgr, rgb565);
        st->row++;
        return;
    }
    int is_odd = (L + st->shift) & 1, partner = is_odd ? L - 1 : L + 1;
    int steps = m->family == HF_R36 ? 3 : m->nchan;
    if (st->sub < steps) {
        if (m->family == HF_R36 && st->sub == 2) {
            // The partner line's chroma (channel 1) into ch[4 * 640].
            if (partner >= st->skipped && partner < st->skipped + st->nl) hf_dec_channel(st, a, ring, partner, 1, ch + 4 * 640);
            else for (int x = 0; x < W; x++) ch[4 * 640 + x] = 128;
        } else {
            hf_dec_channel(st, a, ring, L, st->sub, ch + st->sub * 640);
        }
        st->sub++;
        if (st->sub < steps) return;
    }
    st->sub = 0;
    if (m->family == HF_GBR) {
        // channel order in the table: G, B, R
        for (int x = 0; x < W; x++) {
            rgb[3 * x] = hf_clip(ch[2 * 640 + x]);
            rgb[3 * x + 1] = hf_clip(ch[x]);
            rgb[3 * x + 2] = hf_clip(ch[640 + x]);
        }
        hf_dec_row(st, L, rgb, bgr, rgb565);
    } else if (m->family == HF_PD) {
        // Y0, V (R-Y), U (B-Y), Y1
        for (int x = 0; x < W; x++) hf_ycc(ch[x], ch[2 * 640 + x], ch[640 + x], rgb + 3 * x);
        hf_dec_row(st, 2 * L, rgb, bgr, rgb565);
        for (int x = 0; x < W; x++) hf_ycc(ch[3 * 640 + x], ch[2 * 640 + x], ch[640 + x], rgb + 3 * x);
        hf_dec_row(st, 2 * L + 1, rgb, bgr, rgb565);
    } else {
        // Robot 36: R-Y on even lines, B-Y on odd ones, shared by the pair.
        for (int x = 0; x < W; x++) {
            float own = ch[640 + x], oth = ch[4 * 640 + x];
            float cr = is_odd ? oth : own, cb = is_odd ? own : oth;
            hf_ycc(ch[x], cb, cr, rgb + 3 * x);
        }
        hf_dec_row(st, L, rgb, bgr, rgb565);
    }
    st->row++;
}

// ------------------------------------------------------------- steps

// One step of tens of ms at most on the RP2350. Returns progress 0..99,
// 100 when done (hf_decode_result() has the details), -1 if not begun.
static int hf_decode_step(uint8_t *work, const uint8_t *ring, uint8_t *rgb565, uint8_t *bgr) {
    hf_dec *st = (hf_dec *)work;
    if (st->magic != DEC_MAGIC) return -1;
    hf_dec_arrays a = hf_dec_layout(work, st);
    const hf_mode *m = &hf_modes[st->mode];
    switch (st->stage) {
    case 0:
        hf_dec_scores(st, &a, ring, 4096);
        if (st->pos >= (long)st->n2 * HF_BIN) { st->stage = 1; st->thr = 115; }
        return (int)(50 * st->pos / ((long)st->n2 * HF_BIN + 1));
    case 1: {
        int r = hf_dec_candidates(st, &a, 65536);
        if (r < 0) { st->thr += 13; st->ncand = 0; st->scan = 0; return 50; }
        if (r) {
            float tb = m->line_ms * 2;
            int nl = (int)(st->n2 / tb);
            if (nl < 3) nl = 3;
            if (nl > m->lines) nl = m->lines;
            st->n_lines = nl;
            st->lo = tb * 0.985f; st->hi = tb * 1.015f;
            st->step_c = 8.0f / nl; st->step_f = 1.0f / nl;
            st->pbase = st->lo;
            st->pcount = (int)((st->hi - st->lo) / st->step_c);
            if (st->lo + st->pcount * st->step_c < st->hi) st->pcount++;
            st->pi = 0; st->fine = 0; st->best_v = -1;
            st->stage = st->ncand >= 3 ? 2 : 3;
            if (st->stage == 3) { st->period = tb; st->phase = 0; }
        }
        return 50;
    }
    case 2:
        for (int k = 0; k < DEC_PERIODS_PER_STEP && st->pi < st->pcount; k++, st->pi++)
            hf_dec_fold(st, &a, st->pbase + st->pi * (st->fine ? st->step_f : st->step_c), st->fine ? 1.0f : 4.0f);
        if (st->pi >= st->pcount) {
            if (!st->fine) {
                float pc = st->best_p;
                float lo = pc - st->step_c > st->lo ? pc - st->step_c : st->lo;
                float hi = pc + st->step_c < st->hi ? pc + st->step_c : st->hi;
                st->pbase = lo;
                st->pcount = (int)((hi + 1e-6f - lo) / st->step_f) + 1;
                st->pi = 0; st->fine = 1; st->best_v = -1;
            } else {
                st->period = st->best_p; st->phase = st->best_ph;
                st->stage = 3;
            }
        }
        return 52 + 8 * st->fine;
    case 3:
        hf_dec_lines(st, &a);
        st->oline = 0;
        for (int k = 0; k < DEC_OFF_N; k++) a.off_acc[k] = 0;
        st->stage = 4;
        return 62;
    case 4: {
        // Tuning offset, 8 lines per step.
        if (st->off_known && !st->vis_known) { st->stage = 5; st->oline = 0; return 63; }
        if (st->off_known) {
            // Refine from the VIS leader's middle 280 ms.
            long vp = st->vis_pos;
            if (vp - 4720 >= 40) {
                for (int k = 0; k < DEC_LEAD_N; k++) a.off_acc[k] = 0;
                hf_dec_tone_power(st, ring, vp - 4720, vp - 2480, 1900 + st->offset, -40, 2, DEC_LEAD_N, a.off_acc);
                st->offset += hf_dec_parabola_peak(a.off_acc, DEC_LEAD_N, -40, 2);
            }
            st->stage = 5;
            st->oline = 0;
            return 63;
        }
        int nl = st->nl, stride = nl / 64 > 1 ? nl / 64 : 1, done = 0;
        int K = st->K;
        while (st->oline < nl && done < 8) {
            float s = a.starts[st->oline] * HF_BIN;
            long aa = hf_round(s) + 4;
            long bb = aa + K * HF_BIN - 8;
            if (aa >= 40 && bb <= st->n8)
                hf_dec_tone_power(st, ring, aa, bb, 1200, -150, 5, DEC_OFF_N, a.off_acc);
            st->oline += stride;
            done++;
        }
        if (st->oline >= nl) {
            st->offset = nl ? hf_dec_parabola_peak(a.off_acc, DEC_OFF_N, -150, 5) : 0;
            st->stage = 5;
            st->oline = 0;
        }
        return 63;
    }
    case 5:
        if (m->family == HF_R36) {
            // Parity from the separators (1500 Hz before R-Y, 2300 before
            // B-Y), 32 lines per step.
            int stop = st->oline + 32 < st->nl ? st->oline + 32 : st->nl;
            const hf_chan *c = &m->ch[2];
            for (; st->oline < stop; st->oline++) {
                float sync = a.starts[st->oline] * HF_BIN;
                int n;
                long a0 = hf_dec_line_track(st, &a, ring, sync, c->start, c->start + c->dur, &n);
                float t0 = sync + c->start * st->scale * 8 + 4;
                float hz = hf_dec_hz(st, a.pre, n, a0, t0, t0 + c->dur * st->scale * 8 - 8);
                st->agree += (hz > 1900) == ((st->skipped + st->oline) & 1);
                st->count++;
            }
            if (st->oline < st->nl) return 64;
            st->shift = st->count && st->agree * 2 < st->count;
        }
        st->info.offset_hz = hf_round(st->offset);
        st->row = 0;
        st->sub = 0;
        st->stage = (rgb565 || bgr) ? 6 : 9;
        return 65;
    case 6:
        hf_dec_pixels(st, &a, ring, rgb565, bgr);
        if (st->row >= m->lines) st->stage = 9;
        return 65 + 34 * st->row / m->lines;
    default:
        return 100;
    }
}

// Live preview: one scan line straight from the ring, at the nominal line
// rate, before the whole picture is in. sync_pos: byte position in the ring
// of the line's sync start. Robot 36 lines leave the colour difference
// their partner line carries neutral (that line is not decoded).
static size_t hf_preview_work_bytes(int mode) { return hf_decode_work_bytes(mode, 0); }

static void hf_preview_begin(uint8_t *work, size_t ring_len, size_t sync_pos, int mode, int line, int offset,
                             int disp_w, int disp_h) {
    const hf_mode *m = &hf_modes[mode];
    float lo = 0, hi = 0;
    for (int c = 0; c < m->nchan; c++) {
        if (m->ch[c].start < lo) lo = m->ch[c].start;
        if (m->ch[c].start + m->ch[c].dur > hi) hi = m->ch[c].start + m->ch[c].dur;
    }
    // The track covers [sync + lo - margin, sync + hi + margin].
    size_t before = (size_t)(-lo * 8) + 64, after = (size_t)(hi * 8) + 64;
    size_t start = (sync_pos + ring_len - (2 * before) % ring_len) % ring_len;
    hf_decode_begin(work, ring_len, start & ~(size_t)1, 2 * (before + after), mode, 1, offset, -1, disp_w, disp_h);
    hf_dec *st = (hf_dec *)work;
    st->n2 = 0;                               // no score array: the work buffer is sized for none
    hf_dec_arrays a = hf_dec_layout(work, st);
    st->scale = 1;
    st->skipped = line;
    st->nl = 1;
    st->row = line;
    st->sub = 0;
    st->shift = 0;
    a.starts[0] = (float)before / HF_BIN;     // input bins from the track start
    st->stage = 6;
}

// One channel; returns 1 when the line's image rows are written.
static int hf_preview_step(uint8_t *work, const uint8_t *ring, uint8_t *rgb565) {
    hf_dec *st = (hf_dec *)work;
    if (st->magic != DEC_MAGIC || st->stage != 6) return 1;
    hf_dec_arrays a = hf_dec_layout(work, st);
    int row = st->row;
    hf_dec_pixels(st, &a, ring, rgb565, NULL);
    if (st->row != row) { st->stage = 9; return 1; }
    return 0;
}

static hf_decode_info hf_decode_result(const uint8_t *work) {
    return ((const hf_dec *)work)->info;
}

#endif
