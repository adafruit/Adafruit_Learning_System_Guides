// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// APRS (AX.25, Bell 202 AFSK 1200 baud) decoder core: 32 kHz signed 16-bit
// FM-demodulated audio in (as _ham_dsp's NFM mode gives it), CRC-checked
// AX.25 frames out.
//
//   32 kHz -> 24-tap low-pass, /2 -> 16 kHz -> 47-tap band-pass 800-2600 Hz
//   -> mark (1200 Hz) and space (2200 Hz) correlators: mix with each tone,
//      low-pass over 1.35 bits (18 samples, half-sine window), amplitude
//   -> APRS_SLICERS slicers, each its own bit clock (PLL), NRZI and HDLC
//      decoder. Slicer 0 compares the mark and space amplitudes after a
//      peak/valley AGC on each (which takes out the tone "twist" of
//      pre-/de-emphasis); the others compare mark against space x a gain
//      (0.5 ... 2.8), as Dire Wolf's multiple slicers do.
//   -> frames with a good FCS (CRC-16/X.25) go to a queue; a frame several
//      slicers decode is queued once.
//
// The state is one caller-owned buffer (APRS_STATE_BYTES). The caller
// validates buffers; see _aprs.c. Floats only inside.
#ifndef APRS_CORE_H
#define APRS_CORE_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define APRS_STATE_BYTES 16384
#define APRS_MAGIC 0x41505231u
#define APRS_IN_RATE 32000
#define APRS_RATE 16000
#define APRS_BAUD 1200
#define APRS_SLICERS 7
#define APRS_DEC_TAPS 24
#define APRS_COR_TAPS 18         // default correlator window: 18 samples, 1.35 bits
#define APRS_COR_MAX 32
#define APRS_PRE_MAX 64          // band-pass before the correlators (0 taps = none)
#define APRS_PRE_TAPS 47         // default: 800-2600 Hz
#define APRS_MAX_FRAME 340       // AX.25 with 8 digipeaters and 256 info bytes, + FCS
#define APRS_MIN_FRAME 17        // 2 addresses, control, FCS (no PID / info)
#define APRS_QUEUE 6
#define APRS_RECENT 8            // FCS of recent frames, for dropping repeats from other slicers
#define APRS_DUP_SAMPLES (APRS_RATE / 2)   // a repeat within 0.5 s is the same transmission

typedef struct {
    int32_t pll;
    uint8_t prev_data, prev_raw, pat, oacc;
    int16_t olen;                // bits in oacc; -1: not in a frame
    uint16_t len;
    uint8_t locked;
    uint8_t buf[APRS_MAX_FRAME];
} aprs_slicer;

typedef struct {
    uint16_t len;
    uint8_t slicer;
    uint8_t data[APRS_MAX_FRAME - 2];
} aprs_frame;

typedef struct {
    uint32_t magic;
    uint32_t phase;              // input samples mod 2 (decimator)
    uint32_t hd, hc;             // ring heads
    uint32_t ph_m, ph_s;         // NCO phases
    uint32_t samples;            // 16 kHz samples since configure (wraps)
    float dec[2 * APRS_DEC_TAPS];
    float mi[2 * APRS_COR_MAX], mq[2 * APRS_COR_MAX];
    float si[2 * APRS_COR_MAX], sq[2 * APRS_COR_MAX];
    float pre_hist[2 * APRS_PRE_MAX];
    uint32_t hp;
    // tuning (set by aprs_reset; the host tests change them)
    uint32_t cor_taps, pre_taps;
    float cor_win[APRS_COR_MAX], pre[APRS_PRE_MAX];
    float pll_locked, pll_search, agc_attack, agc_decay;
    float m_peak, m_valley, s_peak, s_valley;
    float level;                 // mean |audio| (16 kHz), for the display
    aprs_slicer sl[APRS_SLICERS];
    uint32_t q_head, q_count;
    aprs_frame queue[APRS_QUEUE];
    uint16_t recent_fcs[APRS_RECENT];
    uint32_t recent_at[APRS_RECENT];
    uint32_t recent_head;
    // statistics
    uint32_t frames, dupes, crc_fail, dropped, flags, per_slicer[APRS_SLICERS];
} aprs_state;

typedef char aprs_state_size_check[sizeof(aprs_state) <= APRS_STATE_BYTES ? 1 : -1];

// 24-tap low-pass for /2 (cutoff 3.8 kHz at 32 kHz, Hamming); unity at DC.
static const float aprs_dec_taps[APRS_DEC_TAPS] = {
#include "aprs_dec_taps.h"
};
// Band-pass before the correlators, 800-2600 Hz, unity at 1700 Hz.
static const float aprs_pre_taps[APRS_PRE_TAPS] = {
#include "aprs_pre_taps.h"
};
// sin table, 256 entries over one turn.
static const float aprs_sin[256] = {
#include "aprs_sin.h"
};

static const float aprs_space_gain[APRS_SLICERS] = {0.0f, 0.5f, 0.71f, 1.0f, 1.41f, 2.0f, 2.83f};

// Phase steps: 2^32 * f / 16000.
#define APRS_STEP_MARK 322122547u    // 1200 Hz
#define APRS_STEP_SPACE 590558003u   // 2200 Hz
#define APRS_PLL_STEP ((int32_t)322122547)   // 2^32 * 1200 / 16000, as a signed step

// Correlator window: half a sine over `taps` samples, sum 1.
static void aprs_set_window(aprs_state *s, unsigned taps) {
    if (taps < 4) taps = 4;
    if (taps > APRS_COR_MAX) taps = APRS_COR_MAX;
    s->cor_taps = taps;
    float total = 0;
    for (unsigned k = 0; k < taps; k++) {
        float x = (k + 0.5f) * 128.0f / taps;       // 0..128: half a turn of the table
        unsigned i = (unsigned)x;
        float fr = x - i;
        float v = aprs_sin[i & 255] + fr * (aprs_sin[(i + 1) & 255] - aprs_sin[i & 255]);
        s->cor_win[k] = v;
        total += v;
    }
    for (unsigned k = 0; k < taps; k++) s->cor_win[k] /= total;
}

static void aprs_reset(aprs_state *s) {
    memset(s, 0, sizeof(*s));
    s->magic = APRS_MAGIC;
    for (int i = 0; i < APRS_SLICERS; i++) s->sl[i].olen = -1;
    aprs_set_window(s, APRS_COR_TAPS);
    s->pre_taps = APRS_PRE_TAPS;
    for (int i = 0; i < APRS_PRE_TAPS; i++) s->pre[i] = aprs_pre_taps[i];
    s->pll_locked = 0.74f;
    s->pll_search = 0.50f;
    s->agc_attack = 0.70f;
    s->agc_decay = 0.00025f;
}

static uint16_t aprs_crc(const uint8_t *p, size_t n) {
    uint16_t crc = 0xffff;
    while (n--) {
        crc ^= *p++;
        for (int b = 0; b < 8; b++) crc = (crc & 1) ? (crc >> 1) ^ 0x8408 : crc >> 1;
    }
    return crc;
}

static void aprs_frame_done(aprs_state *s, aprs_slicer *h, int slicer) {
    unsigned n = h->len;
    if (n < APRS_MIN_FRAME) return;
    if (aprs_crc(h->buf, n) != 0xf0b8) {   // residue of a good X.25 FCS
        s->crc_fail++;
#ifdef APRS_FAIL_HOOK
        APRS_FAIL_HOOK(s, h->buf, n, slicer);
#endif
        return;
    }
    uint16_t fcs = (uint16_t)(h->buf[n - 2] | (h->buf[n - 1] << 8));
    for (int i = 0; i < APRS_RECENT; i++) {
        if (s->recent_fcs[i] == fcs && s->samples - s->recent_at[i] < APRS_DUP_SAMPLES && s->recent_at[i]) {
            s->dupes++;
            return;
        }
    }
    s->recent_fcs[s->recent_head] = fcs;
    s->recent_at[s->recent_head] = s->samples ? s->samples : 1;
    s->recent_head = (s->recent_head + 1) % APRS_RECENT;
    s->frames++;
    s->per_slicer[slicer]++;
    if (s->q_count == APRS_QUEUE) {
        s->dropped++;
        return;
    }
    aprs_frame *f = &s->queue[(s->q_head + s->q_count) % APRS_QUEUE];
    f->len = (uint16_t)(n - 2);
    f->slicer = (uint8_t)slicer;
    memcpy(f->data, h->buf, n - 2);
    s->q_count++;
}

// One received bit (after NRZI) into a slicer's HDLC decoder.
static void aprs_hdlc_bit(aprs_state *s, aprs_slicer *h, int slicer, unsigned bit) {
    h->pat = (uint8_t)((h->pat >> 1) | (bit << 7));
    if (h->pat == 0x7e) {
        if (h->olen >= 0) aprs_frame_done(s, h, slicer);
        if (slicer == 0) s->flags++;
        h->olen = 0;
        h->len = 0;
        h->oacc = 0;
        h->locked = 1;
        return;
    }
    if (h->pat == 0xfe) {        // seven 1s: abort / idle
        h->olen = -1;
        h->len = 0;
        h->locked = 0;
        return;
    }
    if ((h->pat & 0xfc) == 0x7c) return;   // a stuffed 0 after five 1s
    if (h->olen < 0) return;
    h->oacc = (uint8_t)((h->oacc >> 1) | (bit << 7));
    if (++h->olen == 8) {
        h->olen = 0;
        if (h->len >= APRS_MAX_FRAME) {
            h->olen = -1;
            h->len = 0;
            h->locked = 0;
            return;
        }
        h->buf[h->len++] = h->oacc;
    }
}

// The demodulated level (positive = mark) of one 16 kHz sample into a slicer.
static void aprs_slice(aprs_state *s, int k, float d) {
    aprs_slicer *h = &s->sl[k];
    unsigned data = d > 0;
    int32_t prev = h->pll;
    h->pll = (int32_t)((uint32_t)h->pll + (uint32_t)APRS_PLL_STEP);
    if (h->pll < 0 && prev >= 0) {
        // Clock overflow: sample the bit. NRZI: no change = 1.
        unsigned bit = data == h->prev_raw;
        h->prev_raw = (uint8_t)data;
        aprs_hdlc_bit(s, h, k, bit);
    }
    if (data != h->prev_data) {
        // A transition: pull the clock toward mid-bit sampling.
        h->pll = (int32_t)((float)h->pll * (h->locked ? s->pll_locked : s->pll_search));
        h->prev_data = (uint8_t)data;
    }
}

static float aprs_agc(float in, float *peak, float *valley, float attack, float decay) {
    *peak += (in >= *peak ? attack : decay) * (in - *peak);
    *valley += (in <= *valley ? attack : decay) * (in - *valley);
    float span = *peak - *valley;
    return span > 0 ? (in - 0.5f * (*peak + *valley)) / span : 0.0f;
}

static float aprs_dot(const float *win, const float *a, unsigned n) {
    float acc = 0;
    for (unsigned k = 0; k < n; k++) acc += win[k] * a[k];
    return acc;
}

static void aprs_sample16(aprs_state *s, float x) {
    s->samples++;
    s->level += 0.001f * (__builtin_fabsf(x) - s->level);
    if (s->pre_taps) {
        unsigned hp = s->hp, n = s->pre_taps;
        s->pre_hist[hp] = s->pre_hist[hp + n] = x;
        if (++hp == n) hp = 0;
        s->hp = hp;
        x = aprs_dot(s->pre, s->pre_hist + hp, n);
    }
    float cm = aprs_sin[((s->ph_m >> 24) + 64) & 255], sm = aprs_sin[s->ph_m >> 24];
    float cs = aprs_sin[((s->ph_s >> 24) + 64) & 255], ss = aprs_sin[s->ph_s >> 24];
    s->ph_m += APRS_STEP_MARK;
    s->ph_s += APRS_STEP_SPACE;
    unsigned h = s->hc, L = s->cor_taps;
    s->mi[h] = s->mi[h + L] = x * cm;
    s->mq[h] = s->mq[h + L] = x * sm;
    s->si[h] = s->si[h + L] = x * cs;
    s->sq[h] = s->sq[h + L] = x * ss;
    if (++h == L) h = 0;
    s->hc = h;
    float a = aprs_dot(s->cor_win, s->mi + h, L), b = aprs_dot(s->cor_win, s->mq + h, L);
    float m = __builtin_sqrtf(a * a + b * b);
    a = aprs_dot(s->cor_win, s->si + h, L); b = aprs_dot(s->cor_win, s->sq + h, L);
    float sp = __builtin_sqrtf(a * a + b * b);
    float mn = aprs_agc(m, &s->m_peak, &s->m_valley, s->agc_attack, s->agc_decay);
    float sn = aprs_agc(sp, &s->s_peak, &s->s_valley, s->agc_attack, s->agc_decay);
    aprs_slice(s, 0, mn - sn);
    for (int k = 1; k < APRS_SLICERS; k++) aprs_slice(s, k, m - sp * aprs_space_gain[k]);
}

// n bytes of 32 kHz s16 little-endian PCM. Returns frames now queued.
static uint32_t aprs_feed(aprs_state *s, const uint8_t *pcm, size_t n) {
    unsigned hd = s->hd, phase = s->phase;
    for (size_t p = 0; p + 1 < n; p += 2) {
        float x = (float)(int16_t)(pcm[p] | (pcm[p + 1] << 8));
        s->dec[hd] = s->dec[hd + APRS_DEC_TAPS] = x;
        if (++hd == APRS_DEC_TAPS) hd = 0;
        if ((phase ^= 1)) continue;
        const float *hist = s->dec + hd;
        float acc = 0;
        for (unsigned k = 0; k < APRS_DEC_TAPS; k++) acc += aprs_dec_taps[k] * hist[k];
        aprs_sample16(s, acc);
    }
    s->hd = hd;
    s->phase = phase;
    return s->q_count;
}

// Pops the oldest queued frame into out (without FCS); returns its length,
// or 0 if none. *slicer gets the slicer that decoded it.
static size_t aprs_pop(aprs_state *s, uint8_t *out, size_t cap, unsigned *slicer) {
    if (!s->q_count) return 0;
    aprs_frame *f = &s->queue[s->q_head];
    size_t n = f->len < cap ? f->len : cap;
    memcpy(out, f->data, n);
    if (slicer) *slicer = f->slicer;
    s->q_head = (s->q_head + 1) % APRS_QUEUE;
    s->q_count--;
    return n;
}

// Slicers currently inside a frame (flags seen, no abort): a "data carrier".
static unsigned aprs_dcd(const aprs_state *s) {
    unsigned n = 0;
    for (int i = 0; i < APRS_SLICERS; i++) n += s->sl[i].locked;
    return n;
}
#endif
