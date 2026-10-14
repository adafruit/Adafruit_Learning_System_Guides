// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// Live HF SSTV detector: 32 kHz -> 8 kHz decimator (into the recording
// ring) and the two triggers that run on the 8 kHz stream.
//
//  VIS   every ms, 10 ms DFT energies of z on a 50 Hz grid (900..1500 and
//        1700..2100 Hz). For each tuning
//        offset o (-200..+200 Hz, 50 Hz steps) the header ending here is
//        tested on the tones 1100+o, 1200+o, 1300+o and 1900+o (start and
//        stop bits must also hold 40 % of the power and win in each of
//        their 10 ms windows). Headers
//        within 40 ms keep the clearest; an event follows 40 ms after it.
//  sync  every 0.5 ms, the share of z's power that is a 1200+o Hz tone over
//        4 ms (coherent 3 ms sub-blocks, best o of -100..+100 Hz). A run of
//        bins above 0.55 is a sync candidate (start, length). A candidate
//        with at least 4 of the 8 line slots before it holding candidates of
//        the same length is a picture in that mode: a SYNC event.
//  track after an event, candidates on the mode's line grid move an anchor
//        (line number and time), for the live picture and for ending it.
//
// Times: the detector counts 8 kHz input samples (uint32, wrapping); events
// and status report ages (samples before the newest one).
#ifndef HF_DETECT_H
#define HF_DETECT_H
#include "hf_common.h"

#define DET_MAGIC 0x48464454u          // "HFDT"
#define DET_NGRID 22                    // 900..1500 and 1700..2100 Hz, 50 Hz apart
#define DET_NSYNC 5                     // 1100..1300 Hz (grid entries 4..8)
#define DET_K 8                         // sync window, bins (4 ms)
#define DET_W (DET_K - HF_SUB + 1)      // sub-blocks per window
#define DET_THRESHOLD 0.55f
#define DET_HIST 640                    // ms of VIS energies kept
#define DET_CANDS 48
#define DET_MATCH 4
#define DET_TOL 3.0f                    // bins, plus 0.5 % of the distance
#define DET_EVENTS 8
#define DET_VIS_PURITY 0.4f            // start/stop bits: share of the power in 1200+o

enum { HF_EV_VIS = 1, HF_EV_SYNC = 2 };

typedef struct { int32_t kind, mode, code, offset, extra; uint32_t t; } hf_event;

typedef struct {
    uint32_t magic;
    // decimator
    float dh[2 * HF_DECIM_TAPS];
    uint32_t dpos, dphase;
    hf_front fe;
    uint32_t n;                          // 8 kHz samples processed
    uint32_t gi[DET_NGRID];              // phasor positions, 0..159
    float acc[DET_NGRID][2], pacc;       // current bin
    uint32_t bin;                        // bins completed
    float part[20][DET_NGRID][2], ppart[20];
    // VIS
    float hist[DET_HIST][DET_NGRID + 1];  // energies, then window power x samples
    uint32_t ms;                         // energy rows completed
    int32_t vc_open, vc_code, vc_off;
    uint32_t vc_end;                     // ms (z time) where the stop bit ends
    float vc_margin;
    // sync score
    float sub_e[DET_W][DET_NSYNC], sub_p[DET_W];
    float score;                         // last score (for status)
    int32_t pl_on, pl_len;
    uint32_t pl_start;
    float pl_peak;
    uint32_t cand_t[DET_CANDS];          // oldest first
    int16_t cand_est[DET_CANDS];
    int32_t ncand;
    // tracking (bins, z time)
    int32_t track_mode, track_line, track_lines, track_predicted;
    uint32_t track_anchor, track_last;
    // events
    hf_event ev[DET_EVENTS];
    int32_t ev_head, ev_n;
} hf_det;

#define HF_DET_BYTES ((sizeof(hf_det) + 255) & ~(size_t)255)

static const int16_t det_grid_hz[DET_NGRID] = {
    900, 950, 1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400, 1450, 1500,
    1700, 1750, 1800, 1850, 1900, 1950, 2000, 2050, 2100};

// hf_grid_k() of each grid tone: (hz - 1700) / 50, mod 160.
static const uint8_t det_grid_k[DET_NGRID] = {
    144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 0, 1, 2, 3, 4, 5, 6, 7, 8};

static int det_gidx(int hz) { return hz <= 1500 ? (hz - 900) / 50 : 13 + (hz - 1700) / 50; }

static void hf_det_reset(hf_det *d) {
    uint8_t *p = (uint8_t *)d;
    for (size_t i = 0; i < sizeof(hf_det); i++) p[i] = 0;
    hf_front_reset(&d->fe);
    d->track_mode = -1;
    d->magic = DET_MAGIC;
}

static void det_event(hf_det *d, int kind, int mode, int code, int offset, int extra, uint32_t t) {
    int k;
    if (d->ev_n == DET_EVENTS) { d->ev_head = (d->ev_head + 1) % DET_EVENTS; d->ev_n--; }
    k = (d->ev_head + d->ev_n) % DET_EVENTS;
    hf_event *e = &d->ev[k];
    e->kind = kind; e->mode = mode; e->code = code; e->offset = offset; e->extra = extra; e->t = t;
    d->ev_n++;
}

static int det_length_ok(float est, const hf_mode *m) {
    float k = m->sync_ms * 2, tol = 0.4f * k;
    if (tol < 4) tol = 4;
    float e = est - k;
    return e <= tol && e >= -tol;
}

// The VIS cluster is final: report it and track its picture.
static void det_vis_emit(hf_det *d) {
    d->vc_open = 0;
    int mode = hf_mode_by_vis(d->vc_code);
    // Input time of the stop bit's end: z time minus the filter delay.
    uint32_t t = d->vc_end * 8 - 16;
    det_event(d, HF_EV_VIS, mode, d->vc_code, d->vc_off, (int)(d->vc_margin * 100), t);
    if (mode >= 0) {
        d->track_mode = mode;
        d->track_line = 0;
        d->track_lines = 0;
        d->track_predicted = 1;
        d->track_anchor = d->vc_end * 2 + (uint32_t)hf_round(hf_modes[mode].vis_to_sync0 * 2);
        d->track_last = d->track_anchor;
    }
}

// Test the VIS header whose stop bit ends at the end of energy row m.
static void det_vis_test(hf_det *d, uint32_t m) {
    if (d->vc_open && m + 1 - d->vc_end >= 40) det_vis_emit(d);
    if (m < 599) return;
    uint32_t j = m - 299;                       // start bit begins
    float (*e)[DET_NGRID + 1] = d->hist;
    float best_m = -1;
    int best_code = 0, best_off = 0;
    for (int o = -200; o <= 200; o += 50) {
        int ti[4] = {det_gidx(1100 + o), det_gidx(1200 + o), det_gidx(1300 + o), det_gidx(1900 + o)};
        float v[4];
        #define VIS_BLOCK(s0) for (int t = 0; t < 4; t++) \
            v[t] = e[((s0) + 9) % DET_HIST][ti[t]] + e[((s0) + 19) % DET_HIST][ti[t]] + e[((s0) + 29) % DET_HIST][ti[t]]
        #define VIS_POWER(s0) (e[((s0) + 9) % DET_HIST][DET_NGRID] + e[((s0) + 19) % DET_HIST][DET_NGRID] \
            + e[((s0) + 29) % DET_HIST][DET_NGRID])
        VIS_BLOCK(j);
        if (!(v[1] > v[0] && v[1] > v[2] && v[1] > v[3]) || !(v[1] >= DET_VIS_PURITY * VIS_POWER(j))) continue;
        VIS_BLOCK(j + 270);
        if (!(v[1] > v[0] && v[1] > v[2] && v[1] > v[3]) || !(v[1] >= DET_VIS_PURITY * VIS_POWER(j + 270))) continue;
        // ...and in each of their three 10 ms windows (a PD line's 20 ms
        // sync fills two of them; it is not a 30 ms bit).
        int each = 1;
        for (int w = 9; w <= 29 && each; w += 10) {
            const float *x = e[(j + w) % DET_HIST], *y = e[(j + 270 + w) % DET_HIST];
            each = x[ti[1]] > x[ti[0]] && x[ti[1]] > x[ti[2]] && x[ti[1]] > x[ti[3]]
                && y[ti[1]] > y[ti[0]] && y[ti[1]] > y[ti[2]] && y[ti[1]] > y[ti[3]];
        }
        if (!each) continue;
        int code = 0, ones = 0;
        float margin = 0;
        for (int b = 0; b < 8; b++) {
            VIS_BLOCK(j + 30 + 30 * b);
            int bit = v[0] > v[2];
            float r = hf_log2((v[0] + 1e-12f) / (v[2] + 1e-12f));
            margin += r < 0 ? -r : r;
            ones += bit;
            if (b < 7) code |= bit << b;
        }
        #undef VIS_BLOCK
        #undef VIS_POWER
        if (ones & 1) continue;
        int lead = 0;
        for (int w = 0; w < 29; w++) {
            const float *x = e[(j - 291 + 10 * w) % DET_HIST];
            float t3 = x[ti[3]];
            lead += t3 > x[ti[0]] && t3 > x[ti[1]] && t3 > x[ti[2]];
        }
        if (lead < 19) continue;
        margin /= 8;
        if (!(margin > best_m)) continue;
        best_m = margin;
        best_code = code;
        // Offset: the grid's, refined by a parabola through the leader's
        // energy at 1900+o-50, 1900+o and 1900+o+50.
        int g = ti[3];
        float a = 0, bb = 0, c = 0;
        for (int w = 0; w < 29; w++) {
            const float *x = e[(j - 291 + 10 * w) % DET_HIST];
            if (g - 1 >= 13) a += x[g - 1];
            bb += x[g];
            if (g + 1 < DET_NGRID) c += x[g + 1];
        }
        float den = a - 2 * bb + c, frac = den < 0 ? 0.5f * (a - c) / den : 0;
        if (frac > 0.5f) frac = 0.5f;
        if (frac < -0.5f) frac = -0.5f;
        best_off = (int)(o + 50 * frac);
    }
    if (best_m < 0) return;
    uint32_t end = j + 300;
    if (d->vc_open && end - d->vc_end < 40) {
        if (best_m > d->vc_margin) { d->vc_end = end; d->vc_code = best_code; d->vc_off = best_off; d->vc_margin = best_m; }
        return;
    }
    if (d->vc_open) det_vis_emit(d);
    d->vc_open = 1; d->vc_end = end; d->vc_code = best_code; d->vc_off = best_off; d->vc_margin = best_m;
}

// A sync candidate: plateau of the score starting at bin t, about est bins
// long.
static void det_candidate(hf_det *d, uint32_t t, float est) {
    // Line-period match against earlier candidates.
    int best_mode = -1, best_count = 0;
    uint32_t best_first = t;
    for (int mi = 0; mi < HF_NMODES; mi++) {
        const hf_mode *m = &hf_modes[mi];
        if (!det_length_ok(est, m)) continue;
        float tb = m->line_ms * 2;
        int count = 0;
        uint32_t first = t;
        for (int k = 1; k <= 8; k++) {
            float tol = DET_TOL + 0.005f * k * tb;
            for (int h = 0; h < d->ncand; h++) {
                if (!det_length_ok(d->cand_est[h], m)) continue;
                float dd = (float)(int32_t)(t - d->cand_t[h]) - k * tb;
                if (dd <= tol && dd >= -tol) {
                    count++;
                    if ((int32_t)(d->cand_t[h] - first) < 0) first = d->cand_t[h];
                    break;
                }
            }
        }
        if (count < DET_MATCH) continue;
        // Syncs of this length between the grid points mean another line
        // rate (Robot 12 B/W's 100 ms lines put every third sync on Robot
        // 36's 300 ms pair grid).
        int off = 0;
        for (int h = 0; h < d->ncand; h++) {
            if (!det_length_ok(d->cand_est[h], m)) continue;
            float dd = (float)(int32_t)(t - d->cand_t[h]);
            if (!(dd > 0 && dd < 8.5f * tb)) continue;
            int k = hf_round(dd / tb);
            float r = dd - k * tb, tol = DET_TOL + 0.005f * (k > 1 ? k : 1) * tb;
            if (r > tol || r < -tol) off++;
        }
        if (2 * off > count) continue;
        if (count > best_count) { best_count = count; best_mode = mi; best_first = first; }
    }
    // Tracking.
    if (d->track_mode >= 0 && det_length_ok(est, &hf_modes[d->track_mode])) {
        float tb = hf_modes[d->track_mode].line_ms * 2;
        float dd = (float)(int32_t)(t - d->track_anchor);
        int k = hf_round(dd / tb);
        float tol = DET_TOL + 0.005f * (k > 0 ? k : 1) * tb, r = dd - k * tb;
        if ((k >= 1 || (k == 0 && d->track_predicted)) && r <= tol && r >= -tol) {
            d->track_anchor = t;
            d->track_line += k;
            d->track_lines++;
            d->track_last = t;
            d->track_predicted = 0;
        }
    } else if (best_mode >= 0) {
        const hf_mode *m = &hf_modes[best_mode];
        det_event(d, HF_EV_SYNC, best_mode, m->vis, 0, best_count, best_first * 4 - 16);
        d->track_mode = best_mode;
        d->track_line = hf_round((float)(int32_t)(t - best_first) / (m->line_ms * 2));
        d->track_lines = best_count + 1;
        d->track_predicted = 0;
        d->track_anchor = d->track_last = t;
    }
    if (d->ncand == DET_CANDS) {
        for (int h = 1; h < DET_CANDS; h++) { d->cand_t[h - 1] = d->cand_t[h]; d->cand_est[h - 1] = d->cand_est[h]; }
        d->ncand--;
    }
    d->cand_t[d->ncand] = t;
    d->cand_est[d->ncand] = (int16_t)est;
    d->ncand++;
}

// A bin of z is complete: its partial DFTs are in acc/pacc (cleared here).
// part/ppart: the last 20 bins' partials (a stack copy; PSRAM is slow).
static void det_bin(hf_det *d, float (*acc)[2], float *pacc, float (*part)[DET_NGRID][2], float *ppart) {
    uint32_t b = d->bin++;
    unsigned slot = b % 20;
    for (int g = 0; g < DET_NGRID; g++) {
        part[slot][g][0] = acc[g][0]; part[slot][g][1] = acc[g][1];
        acc[g][0] = acc[g][1] = 0;
    }
    ppart[slot] = *pacc;
    *pacc = 0;
    // Sync: the 3 ms sub-block of bins b-5..b, then the window of DET_W
    // sub-blocks that ends with it (it starts at bin b - DET_K + 1).
    if (b >= HF_SUB - 1) {
        uint32_t s = b - (HF_SUB - 1);
        unsigned w = s % DET_W;
        float p = 0;
        for (unsigned q = 0; q < HF_SUB; q++) p += ppart[(s + q) % 20];
        d->sub_p[w] = p;
        for (int h = 0; h < DET_NSYNC; h++) {
            float re = 0, im = 0;
            for (unsigned q = 0; q < HF_SUB; q++) { re += part[(s + q) % 20][4 + h][0]; im += part[(s + q) % 20][4 + h][1]; }
            d->sub_e[w][h] = (re * re + im * im) / (HF_SUB * HF_ZPB);
        }
        if (s >= DET_W - 1) {
            uint32_t bs = s - (DET_W - 1);
            float den = 0, num = 0;
            for (unsigned q = 0; q < DET_W; q++) den += d->sub_p[q];
            for (int h = 0; h < DET_NSYNC; h++) {
                float a = 0;
                for (unsigned q = 0; q < DET_W; q++) a += d->sub_e[q][h];
                if (a > num) num = a;
            }
            float sc = num / (den > 1e-9f ? den : 1e-9f);
            if (sc > 1) sc = 1;
            d->score = sc;
            if (sc >= DET_THRESHOLD) {
                if (!d->pl_on) { d->pl_on = 1; d->pl_start = bs; d->pl_len = 0; d->pl_peak = 0; }
                d->pl_len++;
                if (sc > d->pl_peak) d->pl_peak = sc;
            } else if (d->pl_on) {
                d->pl_on = 0;
                // The 3 ms sub-blocks keep the score up about 6 bins longer
                // than the sync itself, and it crosses the threshold about 2
                // bins before the sync starts.
                det_candidate(d, d->pl_start + 2, (float)(d->pl_len + DET_K - 7));
            }
        }
    }
    // VIS energies: every ms, the 10 ms window of bins b-19..b.
    if (b & 1) {
        uint32_t m = (b - 1) / 2;
        unsigned nb = b + 1 < 20 ? b + 1 : 20;
        float *row = d->hist[m % DET_HIST];
        for (int g = 0; g < DET_NGRID; g++) {
            float re = 0, im = 0;
            for (unsigned q = 0; q < nb; q++) { re += part[(b - q) % 20][g][0]; im += part[(b - q) % 20][g][1]; }
            row[g] = re * re + im * im;
        }
        float pw = 0;
        for (unsigned q = 0; q < nb; q++) pw += ppart[(b - q) % 20];
        row[DET_NGRID] = pw * 20 * HF_ZPB;
        d->ms = m + 1;
        det_vis_test(d, m);
    }
}

// The per-sample state, copied to the stack for a block of samples (the
// detector state lives in PSRAM, which is much slower to work in).
typedef struct {
    hf_front fe;
    uint32_t gi[DET_NGRID];
    float acc[DET_NGRID][2], pacc;
    float part[20][DET_NGRID][2], ppart[20];
    uint32_t n;
} det_hot;

static void det_hot_load(const hf_det *d, det_hot *h) {
    h->fe = d->fe;
    for (int g = 0; g < DET_NGRID; g++) { h->gi[g] = d->gi[g]; h->acc[g][0] = d->acc[g][0]; h->acc[g][1] = d->acc[g][1]; }
    h->pacc = d->pacc;
    h->n = d->n;
    for (int k = 0; k < 20; k++) {
        h->ppart[k] = d->ppart[k];
        for (int g = 0; g < DET_NGRID; g++) { h->part[k][g][0] = d->part[k][g][0]; h->part[k][g][1] = d->part[k][g][1]; }
    }
}

static void det_hot_store(hf_det *d, const det_hot *h) {
    d->fe = h->fe;
    for (int g = 0; g < DET_NGRID; g++) { d->gi[g] = h->gi[g]; d->acc[g][0] = h->acc[g][0]; d->acc[g][1] = h->acc[g][1]; }
    d->pacc = h->pacc;
    d->n = h->n;
    for (int k = 0; k < 20; k++) {
        d->ppart[k] = h->ppart[k];
        for (int g = 0; g < DET_NGRID; g++) { d->part[k][g][0] = h->part[k][g][0]; d->part[k][g][1] = h->part[k][g][1]; }
    }
}

static void hf_det_sample(hf_det *d, det_hot *hot, float x) {
    hf_front_push(&hot->fe, x);
    if (hot->n & 1) {
        // Odd-numbered samples only: z needs no more than 4 kHz.
        float zr, zi;
        hf_front_out(&hot->fe, &zr, &zi);
        for (int g = 0; g < DET_NGRID; g++) {
            const float *r = hf_rot160[hot->gi[g]];
            hot->acc[g][0] += zr * r[0] - zi * r[1];
            hot->acc[g][1] += zr * r[1] + zi * r[0];
        }
        hot->pacc += zr * zr + zi * zi;
    }
    for (int g = 0; g < DET_NGRID; g++) {
        unsigned q = hot->gi[g] + det_grid_k[g];
        hot->gi[g] = q >= 160 ? q - 160 : q;
    }
    hot->n++;
    if (!(hot->n & 3)) {
        d->n = hot->n;
        det_bin(d, hot->acc, &hot->pacc, hot->part, hot->ppart);
    }
}

// 32 kHz int16 PCM in; 8 kHz int16 written to ring at byte write_pos
// (wrapping) and run through the detector. Returns the new write_pos.
static size_t hf_det_feed(hf_det *d, const uint8_t *pcm, size_t pcm_len, uint8_t *ring, size_t ring_len, size_t wp) {
    const unsigned taps = HF_DECIM_TAPS;
    det_hot hot;
    det_hot_load(d, &hot);
    float dh[2 * HF_DECIM_TAPS];
    for (unsigned k = 0; k < 2 * taps; k++) dh[k] = d->dh[k];
    unsigned h = d->dpos, phase = d->dphase;
    for (size_t i = 0; i + 1 < pcm_len; i += 2) {
        float x = (float)(int16_t)(pcm[i] | (pcm[i + 1] << 8));
        dh[h] = x; dh[h + taps] = x;
        if (++h == taps) h = 0;
        if (++phase < 4) continue;
        phase = 0;
        const float *w = dh + h;
        float y = 0;
        for (unsigned t = 0; t < taps / 2; t++) y += hf_decim[t] * (w[t] + w[taps - 1 - t]);
        int v = hf_round(y);
        if (v > 32767) v = 32767;
        if (v < -32768) v = -32768;
        ring[wp] = (uint8_t)v; ring[wp + 1] = (uint8_t)(v >> 8);
        wp += 2;
        if (wp >= ring_len) wp = 0;
        hf_det_sample(d, &hot, (float)v);
    }
    for (unsigned k = 0; k < 2 * taps; k++) d->dh[k] = dh[k];
    d->dpos = h; d->dphase = phase;
    det_hot_store(d, &hot);
    return wp;
}

// Run the detector over `length` bytes of 8 kHz PCM at byte `start` of the
// ring (wrapping), e.g. a recording read back from the SD card.
static void hf_det_scan(hf_det *d, const uint8_t *ring, size_t ring_len, size_t start, size_t length) {
    size_t p = start % ring_len;
    det_hot hot;
    det_hot_load(d, &hot);
    for (size_t i = 0; i + 1 < length; i += 2) {
        hf_det_sample(d, &hot, (float)(int16_t)(ring[p] | (ring[p + 1] << 8)));
        p += 2;
        if (p >= ring_len) p = 0;
    }
    det_hot_store(d, &hot);
}

// Oldest pending event into *e; 0 if none.
static int hf_det_event(hf_det *d, hf_event *e) {
    if (!d->ev_n) return 0;
    *e = d->ev[d->ev_head];
    d->ev_head = (d->ev_head + 1) % DET_EVENTS;
    d->ev_n--;
    return 1;
}

#endif
