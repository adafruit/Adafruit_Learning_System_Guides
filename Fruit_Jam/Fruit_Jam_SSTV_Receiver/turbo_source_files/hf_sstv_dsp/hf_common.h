// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// HF SSTV: mode table, front end and small maths shared by the live
// detector (hf_detect.h) and the decoder (hf_decode.h).
//
// Everything runs on 8 kHz signed 16-bit mono PCM. The front end mixes the
// SSTV tones down by 1700 Hz (1100..2300 Hz -> -600..+600 Hz) and low-passes
// them (32 taps) into a complex signal z that lags the input by
// HF_LP_DELAY samples.
#ifndef HF_COMMON_H
#define HF_COMMON_H
#include <stdint.h>
#include <stddef.h>
#include "hf_coeffs.h"

#define HF_RATE 8000
#define HF_MIX 1700
#define HF_LP_DELAY ((HF_LP_TAPS - 1) / 2.0f)
#define HF_BIN 4                 // samples per 0.5 ms score bin
#define HF_ZPB 2                 // z samples used per bin by the detector and the score pass:
                                 // only odd-numbered ones (z is band-limited to +-1150 Hz)
#define HF_SUB 6                 // bins per coherent sub-block (3 ms)
#define HF_PI 3.14159265359f
#define HF_TWO_PI 6.28318530718f

// ------------------------------------------------------------------ modes

enum { HF_GBR, HF_PD, HF_R36 };
enum { CH_R, CH_G, CH_B, CH_Y0, CH_V, CH_U, CH_Y1, CH_Y, CH_C, CH_SEP };

typedef struct { float start, dur; uint8_t id; } hf_chan;

// Segment times are ms from the start of the line's sync pulse (negative
// for Scottie, whose sync is in the middle of the line). vis_to_sync0: from
// the end of the VIS stop bit to line 0's sync.
typedef struct {
    const char *name;
    uint8_t vis, family, rows, nchan;
    uint16_t width, height, lines;
    float line_ms, sync_ms, vis_to_sync0;
    float sync_bias;     // sync score peak minus true sync start, bins (measured)
    hf_chan ch[5];
} hf_mode;

#define HF_MARTIN(n, v, s) {n, v, HF_GBR, 1, 3, 320, 256, 256, 4.862f + 0.572f + 3 * ((s) + 0.572f), 4.862f, 0, -0.39f, \
    {{5.434f, s, CH_G}, {5.434f + (s) + 0.572f, s, CH_B}, {5.434f + 2 * ((s) + 0.572f), s, CH_R}}}
#define HF_SCOTTIE(n, v, s) {n, v, HF_GBR, 1, 3, 320, 256, 256, 3 * (s) + 4.5f + 9.0f, 9.0f, 9.0f + 2 * (s) + 3.0f, 0.10f, \
    {{-(2 * (s) + 1.5f), s, CH_G}, {-(s), s, CH_B}, {10.5f, s, CH_R}}}
#define HF_PDM(n, v, w, h, s) {n, v, HF_PD, 2, 4, w, h, (h) / 2, 22.08f + 4 * (s), 20.0f, 0, 0.08f, \
    {{22.08f, s, CH_Y0}, {22.08f + (s), s, CH_V}, {22.08f + 2 * (s), s, CH_U}, {22.08f + 3 * (s), s, CH_Y1}}}

#define HF_NMODES 9
static const hf_mode hf_modes[HF_NMODES] = {
    HF_MARTIN("Martin 1", 44, 146.432f),
    HF_MARTIN("Martin 2", 40, 73.216f),
    HF_SCOTTIE("Scottie 1", 60, 138.24f),
    HF_SCOTTIE("Scottie 2", 56, 88.064f),
    HF_PDM("PD90", 99, 320, 256, 170.24f),
    HF_PDM("PD120", 95, 640, 496, 121.6f),
    HF_PDM("PD180", 96, 640, 496, 183.04f),
    {"Robot 36", 8, HF_R36, 1, 3, 320, 240, 240, 150.0f, 9.0f, 0, -0.06f,
     {{12.0f, 88.0f, CH_Y}, {106.0f, 44.0f, CH_C}, {100.0f, 4.5f, CH_SEP}}},
    HF_SCOTTIE("Scottie DX", 76, 345.6f),
};

static int hf_mode_by_vis(int code) {
    for (int i = 0; i < HF_NMODES; i++) if (hf_modes[i].vis == code) return i;
    return -1;
}

static int hf_sync_bins(const hf_mode *m) { return (int)(m->sync_ms * 2 + 0.5f); }

// Whole seconds of a transmission, VIS header included.
static float hf_mode_seconds(const hf_mode *m) {
    return (m->lines * m->line_ms + m->vis_to_sync0) / 1000.0f + 0.91f;
}

// ------------------------------------------------------------------ maths

static float hf_angle(float y, float x) {
    float ax = y < 0 ? -y : y, bx = x < 0 ? -x : x, a;
    if (ax == 0 && bx == 0) return 0;
    if (bx >= ax) { float z = ax / bx, z2 = z * z; a = z * (0.9998660f + z2 * (-0.3302995f + z2 * (0.1801410f + z2 * (-0.0851330f + z2 * 0.0208351f)))); }
    else { float z = bx / ax, z2 = z * z; a = 1.57079632679f - z * (0.9998660f + z2 * (-0.3302995f + z2 * (0.1801410f + z2 * (-0.0851330f + z2 * 0.0208351f)))); }
    if (x < 0) a = HF_PI - a;
    return y < 0 ? -a : a;
}

// cos and sin of x (radians, any value), Taylor polynomials after range
// reduction to [-pi/2, pi/2]; error < 1e-6.
static void hf_sincos(float x, float *c, float *s) {
    float turns = x / HF_TWO_PI;
    int k = (int)(turns < 0 ? turns - 0.5f : turns + 0.5f);
    x -= k * HF_TWO_PI;
    float sc = 1.0f;
    if (x > 1.57079632679f) { x = HF_PI - x; sc = -1.0f; }
    else if (x < -1.57079632679f) { x = -HF_PI - x; sc = -1.0f; }
    float x2 = x * x;
    *s = x * (1.0f + x2 * (-1.0f / 6 + x2 * (1.0f / 120 + x2 * (-1.0f / 5040 + x2 * (1.0f / 362880 + x2 * (-1.0f / 39916800))))));
    *c = sc * (1.0f + x2 * (-0.5f + x2 * (1.0f / 24 + x2 * (-1.0f / 720 + x2 * (1.0f / 40320 + x2 * (-1.0f / 3628800))))));
}

// log2 for positive x, piecewise linear between powers of two.
static float hf_log2(float x) {
    union { float f; uint32_t u; } v = { x };
    return (float)((int)((v.u >> 23) & 255) - 127) + (float)(v.u & 0x7fffff) / 8388608.0f;
}

static int hf_round(float x) { return (int)(x < 0 ? x - 0.5f : x + 0.5f); }
static int hf_floor(float x) { int i = (int)x; return (float)i > x ? i - 1 : i; }

// ------------------------------------------------------------------ front end

typedef struct {
    float hi[2 * HF_LP_TAPS], hq[2 * HF_LP_TAPS];   // doubled history: one contiguous window
    uint32_t h, ph;                                 // history position, mixer phase 0..79
} hf_front;

static void hf_front_reset(hf_front *f) {
    for (int k = 0; k < 2 * HF_LP_TAPS; k++) f->hi[k] = f->hq[k] = 0;
    f->h = 0; f->ph = 0;
}

// One input sample into the filter history (mixed down).
static inline void hf_front_push(hf_front *f, float x) {
    const unsigned taps = HF_LP_TAPS;
    unsigned h = f->h;
    float i = x * hf_mix80[f->ph][0], q = x * hf_mix80[f->ph][1];
    if (++f->ph == 80) f->ph = 0;
    f->hi[h] = i; f->hi[h + taps] = i;
    f->hq[h] = q; f->hq[h + taps] = q;
    if (++h == taps) h = 0;
    f->h = h;
}

// z for the newest sample pushed (re, im).
static inline void hf_front_out(const hf_front *f, float *zr, float *zi) {
    const unsigned taps = HF_LP_TAPS;
    // hi[h .. h+taps-1] is oldest .. newest; hf_lp is symmetric.
    const float *wi = f->hi + f->h, *wq = f->hq + f->h;
    float ai = 0, aq = 0;
    for (unsigned t = 0; t < taps / 2; t++) {
        float c = hf_lp[t];
        ai += c * (wi[t] + wi[taps - 1 - t]);
        aq += c * (wq[t] + wq[taps - 1 - t]);
    }
    *zr = ai; *zi = aq;
}

// One input sample in, z out.
static inline void hf_front_step(hf_front *f, float x, float *zr, float *zi) {
    hf_front_push(f, x);
    hf_front_out(f, zr, zi);
}

// Sample `i` (0-based) of a recording of `length` bytes at byte `start` of
// a ring of `ring_len` bytes; 0 outside the recording.
static inline float hf_ring_sample(const uint8_t *ring, size_t ring_len, size_t start, size_t length, long i) {
    if (i < 0 || (size_t)i * 2 >= length) return 0;
    size_t p = start + (size_t)i * 2;
    if (p >= ring_len) p -= ring_len;
    return (float)(int16_t)(ring[p] | (ring[p + 1] << 8));
}

// Phasor index for the tone hz on the 50 Hz grid: exp(-j 2 pi (hz - 1700) n
// / 8000) = hf_rot160[(k * n) % 160] with k = (hz - 1700) / 50.
static inline unsigned hf_grid_k(int hz) { return (unsigned)(((hz - HF_MIX) / 50 % 160 + 160) % 160); }

#endif
