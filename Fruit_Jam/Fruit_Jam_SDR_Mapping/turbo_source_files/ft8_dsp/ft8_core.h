// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// FT8 receiver core around Karlis Goba's ft8_lib (ft8_lib/, MIT licence):
// a live spectrogram ("waterfall") fed with audio as it arrives, and a
// decoder that works through a finished slot's waterfall in small steps,
// so the caller can keep the USB stream going in between.
//
// Feed:   16-bit PCM at 32 kHz (or 8 kHz) -> 8 kHz -> every 80 ms (half a
//         symbol) one 2560-point Hann-windowed FFT of the last 320 ms ->
//         one waterfall row of 1-byte magnitudes, 0.5 dB steps, for 200 Hz
//         to 3 kHz at 3.125 Hz (half a tone step). The same layout and
//         scaling as ft8_lib's monitor.c with time_osr = freq_osr = 2.
// Decode: ft8_lib's Costas sync search, one (time sub-step, frequency
//         sub-step, time offset) row of it per step, then one candidate
//         per step: soft bits, LDPC belief propagation, CRC, message
//         unpacking. Duplicates are dropped. The callsign hash table (for
//         <...> calls) lives in the work memory and is kept between slots.
//
// The ft8_lib sources are compiled into this translation unit (so its
// static functions, such as the sync score, can be used step by step); its
// changes are listed in ft8_lib/CHANGES.md.
//
// Everything is in caller memory (no malloc): a feed state, one or more
// waterfalls (one fills while the other is decoded) and the decode work.
// The caller validates buffer sizes; see _ft8.c.
#ifndef FT8_CORE_H
#define FT8_CORE_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>

// Both builds (board and host) compute FFT twiddles and the window with
// the single-precision functions below, so their waterfalls match.
static void ft8_sincos(float x, float *s, float *c);
static inline float ft8_cos_f(float x) { float s, c; ft8_sincos(x, &s, &c); return c; }
static inline float ft8_sin_f(float x) { float s, c; ft8_sincos(x, &s, &c); return s; }
#define kiss_fft_phase_t float
#define KISS_FFT_COS(phase) ft8_cos_f(phase)
#define KISS_FFT_SIN(phase) ft8_sin_f(phase)
#ifdef __riscv
// The ESP32-P4's libgcc has no position-independent double arithmetic for
// a native module: halve in single precision (the same result, as the
// subtraction it feeds is exact in either).
#define HALF_OF(x) ((x) * 0.5f)
#endif

#ifdef FT8_TARGET
#include "ft8_target.h"
#endif

#include "ft8_lib/ft8/constants.c"
#include "ft8_lib/ft8/crc.c"
#include "ft8_lib/ft8/text.c"
#include "ft8_lib/ft8/ldpc.c"
#include "ft8_lib/ft8/encode.c"
#include "ft8_lib/ft8/decode.c"
#include "ft8_lib/ft8/message.c"
#include "ft8_lib/fft/kiss_fft.c"
#include "ft8_lib/fft/kiss_fftr.c"

#define FT8_RATE 8000
#define FT8_SYM 1280                        // samples per symbol (0.16 s)
#define FT8_TOSR 2                          // time sub-steps per symbol
#define FT8_FOSR 2                          // frequency sub-steps per tone step
#define FT8_SUB (FT8_SYM / FT8_TOSR)        // 640 samples (80 ms) per waterfall row
#define FT8_NFFT (FT8_SYM * FT8_FOSR)       // 2560
#define FT8_MIN_BIN 32                      // 200 Hz (in 6.25 Hz tone steps)
#define FT8_NUM_BINS 449                    // ... to 3006 Hz
#define FT8_BLOCKS 93                       // symbols in a slot's waterfall (14.88 s)
#define FT8_ROWS (FT8_BLOCKS * FT8_TOSR)    // 186
#define FT8_ROW_BYTES (FT8_FOSR * FT8_NUM_BINS)
#define FT8_STRIDE (FT8_TOSR * FT8_ROW_BYTES)
#define FT8_T_MIN (-10)                     // candidate time offsets, symbols (as ft8_lib)
#define FT8_T_MAX 20
#define FT8_SEARCH_ROWS (FT8_TOSR * FT8_FOSR * (FT8_T_MAX - FT8_T_MIN))
#define FT8_MAX_RESULTS 64
#define FT8_HASH_SIZE 256                   // callsign hash table entries
#define FT8_HASH_MAX_AGE 10                 // slots a callsign is kept without being heard
#define FT8_PI 3.14159265358979f
// The noise floor is this percentile of a slot's waterfall values (see
// ft8_decode_begin).
#ifndef FT8_NOISE_PERCENT
#define FT8_NOISE_PERCENT 10
#endif

#define FT8_FEED_MAGIC 0x46543846u          // 'FT8F'
#define FT8_SPEC_MAGIC 0x46543857u          // 'FT8W'
#define FT8_WORK_MAGIC 0x46543844u          // 'FT8D'

// ------------------------------------------------------------- small maths

// sin and cos of x (any float angle; meant for |x| <= 2 pi). Octant
// reduction and Taylor polynomials: error about 1e-7.
static void ft8_sincos(float x, float *s, float *c) {
    const float two_pi = 6.28318530718f, half_pi = 1.57079632679f;
    x -= two_pi * (float)(int)(x / two_pi);
    if (x < 0) x += two_pi;
    int q = (int)(x / half_pi + 0.5f);       // nearest quarter turn, 0..4
    float r = x - (float)q * half_pi;        // |r| <= pi/4
    float r2 = r * r;
    float sr = r * (1.0f - r2 * (1.0f / 6 - r2 * (1.0f / 120 - r2 * (1.0f / 5040 - r2 * (1.0f / 362880)))));
    float cr = 1.0f - r2 * (0.5f - r2 * (1.0f / 24 - r2 * (1.0f / 720 - r2 * (1.0f / 40320 - r2 * (1.0f / 3628800)))));
    switch (q & 3) {
        case 0: *s = sr; *c = cr; break;
        case 1: *s = cr; *c = -sr; break;
        case 2: *s = -sr; *c = -cr; break;
        default: *s = -cr; *c = sr; break;
    }
}

// log2(x) for x > 0, error about 2e-5.
static float ft8_log2(float x) {
    union { float f; uint32_t u; } v = { x };
    int e = (int)((v.u >> 23) & 255) - 127;
    v.u = (v.u & 0x007fffffu) | 0x3f800000u;     // mantissa in [1, 2)
    float t = (v.f - 1.0f) / (v.f + 1.0f), t2 = t * t;
    return (float)e + 2.88539008178f * t * (1.0f + t2 * (0.333333333f + t2 * (0.2f + t2 * (0.142857143f + t2 * 0.111111111f))));
}

// ------------------------------------------------------------------ feed

// A waterfall: header + ft8_lib's mag array, uint8_t[blocks][time_osr]
// [freq_osr][bins]. hist counts the magnitude values written, for the
// noise floor.
typedef struct {
    uint32_t magic, rows;
    int32_t tag;                  // the caller's (e.g. the slot's time)
    uint32_t reserved;
    uint32_t hist[256];
} ft8_spec_header;
#define FT8_SPEC_BYTES (sizeof(ft8_spec_header) + FT8_BLOCKS * FT8_STRIDE)

#define FT8_FFT_MEM 26624         // kiss_fftr config for 2560 points (checked at init)

typedef struct {
    uint32_t magic, step, acc_n, fill, wpos;
    uint32_t ring_pos;            // next byte of the caller's 8 kHz audio ring
    int32_t acc;
    uintptr_t self;               // where the FFT config was built (it holds pointers into itself)
    float scale;
    float hist[FT8_NFFT];         // the last NFFT samples, circular, oldest at wpos
    float window[FT8_NFFT];
    float time[FT8_NFFT];
    kiss_fft_cpx freq[FT8_NFFT / 2 + 1];
    uint32_t fft_mem[FT8_FFT_MEM / 4];
} ft8_feed_state;
#define FT8_FEED_BYTES sizeof(ft8_feed_state)

static int ft8_fft_ready(ft8_feed_state *s) {
    if (s->self == (uintptr_t)s) return 1;
    size_t len = sizeof(s->fft_mem);
    if (!kiss_fftr_alloc(FT8_NFFT, 0, s->fft_mem, &len)) return 0;
    s->self = (uintptr_t)s;
    return 1;
}

// Start over. step: input samples per 8 kHz sample, 4 (32 kHz) or 1.
static int ft8_feed_init(ft8_feed_state *s, int step) {
    memset(s, 0, sizeof(*s));
    s->magic = FT8_FEED_MAGIC;
    s->step = (uint32_t)step;
    s->scale = 1.0f / (32768.0f * (float)step);
    const float norm = 2.0f / FT8_NFFT;
    for (int i = 0; i < FT8_NFFT; i++) {
        float x = ft8_sin_f(FT8_PI * (float)i / FT8_NFFT);
        s->window[i] = norm * x * x;
    }
    return ft8_fft_ready(s);
}

static void ft8_spec_reset(uint8_t *spec, int32_t tag) {
    ft8_spec_header *h = (ft8_spec_header *)spec;
    memset(h, 0, sizeof(*h));
    h->magic = FT8_SPEC_MAGIC;
    h->tag = tag;
}

// The waterfall starts here: its first row ends FT8_SUB samples after this
// point. The analysis window still holds the audio from before it.
static void ft8_slot_reset(ft8_feed_state *s, uint8_t *spec, int32_t tag) {
    s->fill = 0;
    ft8_spec_reset(spec, tag);
}

static void ft8_row(ft8_feed_state *s, uint8_t *spec) {
    ft8_spec_header *h = (ft8_spec_header *)spec;
    if (h->rows >= FT8_ROWS) return;
    const float *w = s->window, *x = s->hist;
    float *t = s->time;
    uint32_t a = FT8_NFFT - s->wpos;
    for (uint32_t i = 0; i < a; i++) t[i] = w[i] * x[s->wpos + i];
    for (uint32_t i = a; i < FT8_NFFT; i++) t[i] = w[i] * x[i - a];
    kiss_fftr((kiss_fftr_cfg)s->fft_mem, t, s->freq);
    uint8_t *out = spec + sizeof(ft8_spec_header) + h->rows * FT8_ROW_BYTES;
    uint32_t *hist = h->hist;
    for (int f = 0; f < FT8_FOSR; f++) {
        const kiss_fft_cpx *q = s->freq + FT8_FOSR * FT8_MIN_BIN + f;
        for (int b = 0; b < FT8_NUM_BINS; b++, q += FT8_FOSR) {
            float mag2 = q->r * q->r + q->i * q->i;
            // 2 * 10 log10(mag2) + 240, as monitor.c
            int v = (int)(6.02059991f * ft8_log2(1e-12f + mag2) + 240.0f);
            v = v < 0 ? 0 : (v > 255 ? 255 : v);
            *out++ = (uint8_t)v;
            hist[v]++;
        }
    }
    h->rows++;
}

// n 16-bit samples through the feed; returns the waterfall's rows so far.
// The 8 kHz audio also goes into ring (if any: ring_len bytes, even) at
// s->ring_pos, wrapping.
static uint32_t ft8_feed(ft8_feed_state *restrict s, const int16_t *restrict pcm, size_t n, uint8_t *restrict spec,
                         uint8_t *restrict ring, size_t ring_len) {
    uint32_t step = s->step, acc_n = s->acc_n, fill = s->fill, wpos = s->wpos, rp = s->ring_pos;
    if (rp >= ring_len) rp = 0;
    int32_t acc = s->acc;
    const float scale = s->scale;
    for (size_t i = 0; i < n; i++) {
        acc += pcm[i];
        if (++acc_n < step) continue;
        s->hist[wpos] = (float)acc * scale;
        if (ring) {
            int32_t v = acc / (int32_t)step;
            ring[rp] = (uint8_t)v;
            ring[rp + 1] = (uint8_t)((uint32_t)v >> 8);
            rp += 2;
            if (rp >= ring_len) rp = 0;
        }
        acc = 0;
        acc_n = 0;
        if (++wpos == FT8_NFFT) wpos = 0;
        if (++fill == FT8_SUB) {
            fill = 0;
            s->wpos = wpos;
            ft8_row(s, spec);
        }
    }
    s->acc = acc; s->acc_n = acc_n; s->fill = fill; s->wpos = wpos; s->ring_pos = rp;
    return ((ft8_spec_header *)spec)->rows;
}

// ---------------------------------------------------------------- decode

typedef struct {
    char callsign[12];
    uint32_t hash;                // 8 MSBs: age in slots; 22 LSBs: hash
} ft8_hash_entry;

typedef struct {
    int16_t snr, dt_ms, freq_hz, score;
    uint16_t msg_hash;
    uint8_t payload[FTX_PAYLOAD_LENGTH_BYTES];
    char text[FTX_MAX_MESSAGE_LENGTH + 1];
} ft8_result;

enum { FT8_IDLE, FT8_SEARCH, FT8_DECODE, FT8_DONE };

typedef struct {
    uint32_t magic, max_cand, phase;
    int32_t min_score, ldpc_iters, early_stop;
    uint32_t search_row, heap_size, next, num_blocks;
    float noise;                  // mean noise power per waterfall bin (linear)
    int32_t noise_v;              // its median, waterfall units (0.5 dB, 240 = 0 dB)
    uint32_t n_results, hash_size;
    uint32_t tried, ldpc_fail, crc_fail, unpack_fail, dupes;
    float lin[256];               // waterfall value -> power
    ft8_result results[FT8_MAX_RESULTS];
    ft8_hash_entry table[FT8_HASH_SIZE];
    ftx_candidate_t cand[];       // max_cand
} ft8_work;
#define FT8_WORK_BYTES(max_cand) (sizeof(ft8_work) + (size_t)(max_cand) * sizeof(ftx_candidate_t))

// The table the hash callbacks use (ft8_lib's interface has no context
// argument). Set before every call that may unpack a message.
ft8_work *ft8_hash_work;

static void ft8_hash_add(const char *callsign, uint32_t hash) {
    ft8_work *w = ft8_hash_work;
    uint16_t hash10 = (hash >> 12) & 0x3FFu;
    int i = (hash10 * 23) % FT8_HASH_SIZE;
    while (w->table[i].callsign[0] != '\0') {
        if ((w->table[i].hash & 0x3FFFFFu) == hash && strcmp(w->table[i].callsign, callsign) == 0) {
            w->table[i].hash &= 0x3FFFFFu;            // heard again: age 0
            return;
        }
        i = (i + 1) % FT8_HASH_SIZE;
    }
    if (w->hash_size >= FT8_HASH_SIZE - 1) return;   // full (keep one empty slot to end lookups)
    w->hash_size++;
    strncpy(w->table[i].callsign, callsign, 11);
    w->table[i].callsign[11] = '\0';
    w->table[i].hash = hash;
}

static bool ft8_hash_lookup(ftx_callsign_hash_type_t hash_type, uint32_t hash, char *callsign) {
    ft8_work *w = ft8_hash_work;
    uint8_t shift = (hash_type == FTX_CALLSIGN_HASH_10_BITS) ? 12 : (hash_type == FTX_CALLSIGN_HASH_12_BITS ? 10 : 0);
    uint16_t hash10 = (hash >> (12 - shift)) & 0x3FFu;
    int i = (hash10 * 23) % FT8_HASH_SIZE;
    while (w->table[i].callsign[0] != '\0') {
        if (((w->table[i].hash & 0x3FFFFFu) >> shift) == hash) {
            strcpy(callsign, w->table[i].callsign);
            return true;
        }
        i = (i + 1) % FT8_HASH_SIZE;
    }
    callsign[0] = '\0';
    return false;
}

// Age every callsign by one slot; forget those older than max_age. (The
// table is rebuilt after removals, so open-addressing chains stay intact.)
static void ft8_hash_cleanup(ft8_work *w, uint8_t max_age) {
    ft8_hash_entry keep[FT8_HASH_SIZE];
    int n = 0;
    for (int i = 0; i < FT8_HASH_SIZE; i++) {
        ft8_hash_entry *e = &w->table[i];
        if (e->callsign[0] == '\0') continue;
        uint8_t age = (uint8_t)(e->hash >> 24);
        if (age <= max_age) {
            keep[n] = *e;
            keep[n].hash = (((uint32_t)age + 1u) << 24) | (e->hash & 0x3FFFFFu);
            n++;
        }
    }
    memset(w->table, 0, sizeof(w->table));
    w->hash_size = 0;
    ft8_hash_work = w;
    for (int k = 0; k < n; k++) {
        ft8_hash_add(keep[k].callsign, keep[k].hash & 0x3FFFFFu);
        // (ft8_hash_add found an empty slot for it: restore its age)
        uint16_t hash10 = (keep[k].hash >> 12) & 0x3FFu;
        int i = (hash10 * 23) % FT8_HASH_SIZE;
        while (strcmp(w->table[i].callsign, keep[k].callsign) != 0) i = (i + 1) % FT8_HASH_SIZE;
        w->table[i].hash = keep[k].hash;
    }
}

static void ft8_work_init(ft8_work *w, uint32_t max_cand) {
    memset(w, 0, FT8_WORK_BYTES(max_cand));
    w->magic = FT8_WORK_MAGIC;
    w->max_cand = max_cand;
    w->phase = FT8_IDLE;
    // Waterfall value v is (2 * dB + 240): power 10^((v - 240) / 20).
    float p = 1e-12f, k = 1.12201845f;      // 10^(1/20)
    for (int v = 0; v < 256; v++) { w->lin[v] = p; p *= k; }
}

static ftx_waterfall_t ft8_waterfall(const uint8_t *spec, uint32_t num_blocks) {
    ftx_waterfall_t wf;
    wf.max_blocks = FT8_BLOCKS;
    wf.num_blocks = (int)num_blocks;
    wf.num_bins = FT8_NUM_BINS;
    wf.time_osr = FT8_TOSR;
    wf.freq_osr = FT8_FOSR;
    wf.mag = (WF_ELEM_T *)(spec + sizeof(ft8_spec_header));
    wf.block_stride = FT8_STRIDE;
    wf.protocol = FTX_PROTOCOL_FT8;
    return wf;
}

// Start decoding a waterfall (complete or not: only whole symbols are
// used). Results of the previous decode are cleared.
static void ft8_decode_begin(ft8_work *w, const uint8_t *spec, int min_score, int ldpc_iters, int early_stop) {
    const ft8_spec_header *h = (const ft8_spec_header *)spec;
    w->min_score = min_score;
    w->ldpc_iters = ldpc_iters;
    w->early_stop = early_stop;
    w->num_blocks = h->rows / FT8_TOSR;
    w->search_row = 0;
    w->heap_size = 0;
    w->next = 0;
    w->n_results = 0;
    w->tried = w->ldpc_fail = w->crc_fail = w->unpack_fail = w->dupes = 0;
    // Noise floor: a low percentile of the waterfall values (a crowded
    // band's signals raise the median), as a mean power: noise power in a
    // bin is exponentially distributed, so its p-quantile is -ln(1 - p)
    // times its mean.
    uint32_t total = 0, below, acc = 0;
    int v = 0;
    for (int i = 0; i < 256; i++) total += h->hist[i];
    below = (uint32_t)((uint64_t)total * FT8_NOISE_PERCENT / 100);
    for (v = 0; v < 255; v++) {
        acc += h->hist[v];
        if (acc > below) break;
    }
    w->noise_v = v;
    w->noise = w->lin[v] / (-0.693147181f * ft8_log2(1.0f - FT8_NOISE_PERCENT / 100.0f));
    w->phase = FT8_SEARCH;
}

// One row of the sync search: all frequency offsets at one time offset
// and sub-step (the same order as ft8_lib's ftx_find_candidates, so the
// same candidates come out).
static void ft8_search_row(ft8_work *w, const ftx_waterfall_t *wf) {
    uint32_t r = w->search_row;
    int span = FT8_T_MAX - FT8_T_MIN;
    ftx_candidate_t c;
    c.time_sub = (uint8_t)(r / (FT8_FOSR * span));
    c.freq_sub = (uint8_t)((r / span) % FT8_FOSR);
    c.time_offset = (int16_t)(FT8_T_MIN + (int)(r % span));
    ftx_candidate_t *heap = w->cand;
    int heap_size = (int)w->heap_size, num = (int)w->max_cand;
    for (c.freq_offset = 0; (c.freq_offset + 7) < wf->num_bins; ++c.freq_offset) {
        c.score = (int16_t)ft8_sync_score(wf, &c);
        if (c.score < w->min_score) continue;
        if (heap_size == num && c.score > heap[0].score) {
            --heap_size;
            heap[0] = heap[heap_size];
            heapify_down(heap, heap_size);
        }
        if (heap_size < num) {
            heap[heap_size] = c;
            ++heap_size;
            heapify_up(heap, heap_size);
        }
    }
    w->heap_size = (uint32_t)heap_size;
    if (++w->search_row == FT8_SEARCH_ROWS) {
        // Sort by score, best first (as ftx_find_candidates).
        int len = heap_size;
        while (len > 1) {
            ftx_candidate_t tmp = heap[len - 1];
            heap[len - 1] = heap[0];
            heap[0] = tmp;
            len--;
            heapify_down(heap, len);
        }
        w->phase = FT8_DECODE;
    }
}

// SNR in 2500 Hz, dB: the mean power in the decoded tones' bins against
// the noise floor. FT8_SNR_OFFSET (dB) converts a waterfall bin's
// bandwidth to 2500 Hz and was fitted against WSJT-X on real slots.
#ifndef FT8_SNR_OFFSET
#define FT8_SNR_OFFSET (-26.0f)
#endif
static int ft8_snr(const ft8_work *w, const ftx_waterfall_t *wf, const ftx_candidate_t *c, const uint8_t *payload) {
    uint8_t tones[FT8_NN];
    ft8_encode(payload, tones);
    const uint8_t *mag = get_cand_mag(wf, c);
    float sum = 0;
    int n = 0;
    for (int k = 0; k < FT8_NN; k++) {
        int block = c->time_offset + k;
        if (block < 0 || block >= wf->num_blocks) continue;
        sum += w->lin[mag[k * wf->block_stride + tones[k]]];
        n++;
    }
    if (!n || w->noise <= 0) return -30;
    float ratio = sum / (float)n / w->noise - 1.0f;
    if (ratio < 1e-3f) ratio = 1e-3f;
    float db = 3.01029996f * ft8_log2(ratio) + FT8_SNR_OFFSET;
    int snr = (int)(db < 0 ? db - 0.5f : db + 0.5f);
    return snr < -30 ? -30 : (snr > 49 ? 49 : snr);
}

// ft8_lib's bp_decode (ldpc.c) with WSJT-X's early stop (bpdecode174_91):
// give up once the number of failed parity checks has not gone down for 5
// iterations, after at least 10, while more than 15 checks fail. Most
// candidates are noise, and this ends them in about half the time. The
// parity tables are copied to the stack first (the module's constants are
// in PSRAM, the stack in SRAM).
static void ft8_bp_decode(const float codeword[], int max_iters, int early_stop, uint8_t plain[], int *ok) {
    float tov[FTX_LDPC_N][3];
    float toc[FTX_LDPC_M][7];
    uint8_t nm[FTX_LDPC_M][7], mn[FTX_LDPC_N][3], rows[FTX_LDPC_M];
    memcpy(nm, kFTX_LDPC_Nm, sizeof(nm));
    memcpy(mn, kFTX_LDPC_Mn, sizeof(mn));
    memcpy(rows, kFTX_LDPC_Num_rows, sizeof(rows));
    int min_errors = FTX_LDPC_M, last = FTX_LDPC_M, stuck = 0;
    memset(tov, 0, sizeof(tov));
    for (int iter = 0; iter < max_iters; ++iter) {
        int plain_sum = 0;
        for (int n = 0; n < FTX_LDPC_N; ++n) {
            plain[n] = ((codeword[n] + tov[n][0] + tov[n][1] + tov[n][2]) > 0) ? 1 : 0;
            plain_sum += plain[n];
        }
        if (plain_sum == 0) break;               // all zeros is not a message
        int errors = 0;
        for (int m = 0; m < FTX_LDPC_M; ++m) {
            uint8_t x = 0;
            for (int i = 0; i < rows[m]; ++i) x ^= plain[nm[m][i] - 1];
            errors += x;
        }
        if (errors < min_errors) {
            min_errors = errors;
            if (errors == 0) break;
        }
        if (iter > 0) {
            stuck = errors < last ? 0 : stuck + 1;
            if (early_stop && stuck >= 5 && iter >= 10 && errors > 15) break;
        }
        last = errors;
        for (int m = 0; m < FTX_LDPC_M; ++m) {
            for (int n_idx = 0; n_idx < rows[m]; ++n_idx) {
                int n = nm[m][n_idx] - 1;
                float Tnm = codeword[n];
                for (int m_idx = 0; m_idx < 3; ++m_idx) {
                    if ((mn[n][m_idx] - 1) != m) Tnm += tov[n][m_idx];
                }
                toc[m][n_idx] = fast_tanh(-Tnm / 2);
            }
        }
        for (int n = 0; n < FTX_LDPC_N; ++n) {
            for (int m_idx = 0; m_idx < 3; ++m_idx) {
                int m = mn[n][m_idx] - 1;
                float Tmn = 1.0f;
                for (int n_idx = 0; n_idx < rows[m]; ++n_idx) {
                    if ((nm[m][n_idx] - 1) != n) Tmn *= toc[m][n_idx];
                }
                tov[n][m_idx] = -2 * fast_atanh(Tmn);
            }
        }
    }
    *ok = min_errors;
}

// ftx_decode_candidate (decode.c) for FT8, with ft8_bp_decode.
static bool ft8_decode_candidate(const ftx_waterfall_t *wf, const ftx_candidate_t *cand, int max_iterations,
                                 int early_stop, ftx_message_t *message, ftx_decode_status_t *status) {
    float log174[FTX_LDPC_N];
    ft8_extract_likelihood(wf, cand, log174);
    ftx_normalize_logl(log174);
    uint8_t plain174[FTX_LDPC_N];
    ft8_bp_decode(log174, max_iterations, early_stop, plain174, &status->ldpc_errors);
    if (status->ldpc_errors > 0) return false;
    uint8_t a91[FTX_LDPC_K_BYTES];
    pack_bits(plain174, FTX_LDPC_K, a91);
    status->crc_extracted = ftx_extract_crc(a91);
    a91[9] &= 0xF8;
    a91[10] &= 0x00;
    status->crc_calculated = ftx_compute_crc(a91, 96 - 14);
    if (status->crc_extracted != status->crc_calculated) return false;
    message->hash = status->crc_calculated;
    for (int i = 0; i < 10; ++i) message->payload[i] = a91[i];
    return true;
}

static void ft8_decode_one(ft8_work *w, const ftx_waterfall_t *wf) {
    const ftx_candidate_t *c = &w->cand[w->next++];
    w->tried++;
    ftx_message_t msg;
    ftx_decode_status_t st;
    if (!ft8_decode_candidate(wf, c, w->ldpc_iters, w->early_stop, &msg, &st)) {
        if (st.ldpc_errors > 0) w->ldpc_fail++;
        else w->crc_fail++;
        return;
    }
    for (uint32_t i = 0; i < w->n_results; i++) {
        if (w->results[i].msg_hash == msg.hash && memcmp(w->results[i].payload, msg.payload, sizeof(msg.payload)) == 0) {
            w->dupes++;
            return;
        }
    }
    if (w->n_results >= FT8_MAX_RESULTS) return;
    ft8_result *r = &w->results[w->n_results];
    ftx_callsign_hash_interface_t hif = { ft8_hash_lookup, ft8_hash_add };
    ftx_message_offsets_t offsets;
    ft8_hash_work = w;
    char text[FTX_MAX_MESSAGE_LENGTH + 8];
    if (ftx_message_decode(&msg, &hif, text, &offsets) != FTX_MESSAGE_RC_OK) {
        w->unpack_fail++;
        return;
    }
    text[FTX_MAX_MESSAGE_LENGTH] = '\0';
    strcpy(r->text, text);
    memcpy(r->payload, msg.payload, sizeof(msg.payload));
    r->msg_hash = msg.hash;
    r->score = c->score;
    // Time from the waterfall's start, less the 0.5 s an FT8 transmission
    // starts into its slot (WSJT-X's DT), less 160 ms: a row's 2-symbol
    // window is centred one symbol before its end, so the best-matching row
    // for a symbol comes one symbol after it starts (ft8_lib's demo prints
    // times 0.16 s late).
    r->dt_ms = (int16_t)((c->time_offset * FT8_TOSR + c->time_sub) * 80 - 660);
    // ((MIN_BIN + offset) * FOSR + sub) * 3.125 Hz, rounded
    r->freq_hz = (int16_t)((((FT8_MIN_BIN + c->freq_offset) * FT8_FOSR + c->freq_sub) * 25 + 4) / 8);
    r->snr = (int16_t)ft8_snr(w, wf, c, msg.payload);
    w->n_results++;
}

// Up to `units` units of work (a search row or a candidate each); returns
// the units left, 0 when the decode is complete.
static uint32_t ft8_decode_step(ft8_work *w, const uint8_t *spec, uint32_t units) {
    ftx_waterfall_t wf = ft8_waterfall(spec, w->num_blocks);
    while (units--) {
        if (w->phase == FT8_SEARCH) {
            ft8_search_row(w, &wf);
        } else if (w->phase == FT8_DECODE) {
            if (w->next < w->heap_size) {
                ft8_decode_one(w, &wf);
            }
            if (w->next >= w->heap_size) {
                ft8_hash_cleanup(w, FT8_HASH_MAX_AGE);
                w->phase = FT8_DONE;
            }
        } else {
            break;
        }
    }
    if (w->phase == FT8_SEARCH) return FT8_SEARCH_ROWS - w->search_row + w->max_cand;
    if (w->phase == FT8_DECODE) return w->heap_size - w->next;
    return 0;
}

#endif
