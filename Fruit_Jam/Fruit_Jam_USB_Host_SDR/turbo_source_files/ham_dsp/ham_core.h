// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// Ham radio demodulator core: 256 ksample/s unsigned 8-bit I/Q in,
// 32 kHz signed 16-bit mono PCM out, one output sample per 8 input samples.
//
//   u8 I/Q -> NCO shift -> 64-tap FIR, /8 -> 32 kHz complex
//     NFM:        48-tap channel FIR -> discriminator -> de-emphasis,
//                 300 Hz high-pass, 3.4 kHz low-pass, noise squelch
//     USB/LSB/CW/AM: 64-tap FIR, /4 -> 8 kHz complex -> 128-tap channel FIR
//                 -> BFO product detector (SSB, CW) or envelope (AM)
//                 -> AGC -> 64-tap interpolator, x4 -> 32 kHz
//
// SSB and CW channel filters are real low-pass filters. The NCO puts the
// middle of the wanted passband at 0 Hz, and the BFO moves it back to audio,
// so USB, LSB and CW differ only in the NCO/BFO offsets.
//
// There is no DC removal: the caller keeps the wanted signal 12-100 kHz
// from the hardware centre, so after the NCO shift the receiver's DC offset
// lies in the stopband of the first filter.
//
// Caller validates the state buffer and buffer sizes; see _ham_dsp.c.
#ifndef HAM_CORE_H
#define HAM_CORE_H
#include <stdint.h>
#include <stddef.h>
#include "ham_coeffs.h"

#define HAM_STATE_BYTES 8192
#define HAM_MAGIC 0x48414d31u
#define HAM_IN_RATE 256000.0f

enum { HAM_NFM = 0, HAM_AM = 1, HAM_USB = 2, HAM_LSB = 3, HAM_CW = 4, HAM_MODES = 5 };
#define HAM_FLAG_CONJUGATE 1u   // input spectrum is inverted: use conj(I/Q)

#define HAM_SSB_CENTER 1675.0f  // middle of the 300..3050 Hz SSB passband
#define HAM_CW_PITCH 700.0f
#define HAM_AGC_DELAY 32        // look-ahead, 4 ms at 8 kHz

typedef struct {
    uint32_t magic, mode, flags, squelch_open;
    // NCO: rotates the input by e^{-j 2 pi offset n / 256k}.
    float nco_c, nco_s, nco_sc, nco_ss;
    // BFO at 8 kHz.
    float bfo_c, bfo_s, bfo_sc, bfo_ss;
    float offset_hz, squelch;
    // Measurements over the latest complete 16 ms window. Windows and
    // oscillator renormalization run on sample counts, not per call, so the
    // output does not depend on how the input is split into calls.
    float power, noise;
    uint32_t power_n, noise_n, renorm_n;
    float power_acc, noise_acc;
    // Stage 1: 256k -> 32k.
    uint32_t h1, p1;
    float f1i[2 * HAM_F1_TAPS], f1q[2 * HAM_F1_TAPS];
    // NFM at 32k.
    uint32_t hn;
    float fni[2 * HAM_FNFM_TAPS], fnq[2 * HAM_FNFM_TAPS];
    float prev_i, prev_q, prev_d, deemph, gate;
    float hp_z1, hp_z2, hp_z3, hp_z4, lp_z1, lp_z2;
    // SSB/CW/AM: 32k -> 8k, channel filter, AGC, interpolation.
    uint32_t h2, p2, hc, ha, hint;
    float f2i[2 * HAM_F2_TAPS], f2q[2 * HAM_F2_TAPS];
    float fci[2 * HAM_FSSB_TAPS], fcq[2 * HAM_FSSB_TAPS];
    float am_dc, agc_env, agc_gain;
    float agc_delay[HAM_AGC_DELAY];
    float fint[2 * (HAM_FINT_TAPS / 4)];
} ham_state;
typedef char ham_state_size_check[(sizeof(ham_state) <= HAM_STATE_BYTES) ? 1 : -1];
typedef char ham_channel_taps_check[(HAM_FCW_TAPS == HAM_FSSB_TAPS && HAM_FAM_TAPS == HAM_FSSB_TAPS) ? 1 : -1];
typedef char ham_fint_taps_check[(HAM_FINT_TAPS % 4 == 0) ? 1 : -1];
typedef char ham_fir_taps_check[(HAM_F1_TAPS % 4 == 0 && HAM_FNFM_TAPS % 4 == 0 && HAM_F2_TAPS % 4 == 0 && HAM_FSSB_TAPS % 4 == 0) ? 1 : -1];

static float ham_abs(float x) { return __builtin_fabsf(x); }

// sin and cos of x in [-pi, pi]; relative error below 1e-7 near 0, which
// matters because NCO steps are small angles.
static void ham_sincos(float x, float *s, float *c) {
    float sign_c = 1.0f;
    if (x > 1.57079632679f) { x = 3.14159265359f - x; sign_c = -1.0f; }
    else if (x < -1.57079632679f) { x = -3.14159265359f - x; sign_c = -1.0f; }
    float x2 = x * x;
    *s = x * (1.0f + x2 * (-1.0f / 6 + x2 * (1.0f / 120 + x2 * (-1.0f / 5040 + x2 * (1.0f / 362880 + x2 * (-1.0f / 39916800))))));
    *c = sign_c * (1.0f + x2 * (-0.5f + x2 * (1.0f / 24 + x2 * (-1.0f / 720 + x2 * (1.0f / 40320 + x2 * (-1.0f / 3628800 + x2 * (1.0f / 479001600)))))));
}

// atan on [0,1], max error approximately 1.2e-5 radians (as fm_core.h).
static float ham_atan(float z) {
    float z2 = z * z;
    return z * (0.9998660f + z2 * (-0.3302995f + z2 * (0.1801410f + z2 * (-0.0851330f + z2 * 0.0208351f))));
}
static float ham_angle(float y, float x) {
    float ax = ham_abs(x), ay = ham_abs(y), angle;
    if (ax == 0 && ay == 0) return 0;
    if (ax >= ay) angle = ham_atan(ay / ax);
    else angle = 1.57079632679f - ham_atan(ax / ay);
    if (x < 0) angle = 3.14159265359f - angle;
    return y < 0 ? -angle : angle;
}

static float ham_sqrt(float x) { return __builtin_sqrtf(x); }

// Angle 2 pi f / rate wrapped to [-pi, pi].
static float ham_angle_step(float f, float rate) {
    float turns = f / rate;
    turns -= (float)(int32_t)turns;
    if (turns > 0.5f) turns -= 1.0f;
    if (turns < -0.5f) turns += 1.0f;
    return turns * 6.28318530718f;
}

static void ham_set_nco(ham_state *s) {
    float shift = s->offset_hz;
    if (s->mode == HAM_USB) shift += HAM_SSB_CENTER;
    else if (s->mode == HAM_LSB) shift -= HAM_SSB_CENTER;
    float sn, cs;
    ham_sincos(-ham_angle_step(shift, HAM_IN_RATE), &sn, &cs);
    s->nco_sc = cs; s->nco_ss = sn;
    float bfo = 0;
    if (s->mode == HAM_USB) bfo = HAM_SSB_CENTER;
    else if (s->mode == HAM_LSB) bfo = -HAM_SSB_CENTER;
    else if (s->mode == HAM_CW) bfo = HAM_CW_PITCH;
    ham_sincos(ham_angle_step(bfo, 8000.0f), &sn, &cs);
    s->bfo_sc = cs; s->bfo_ss = sn;
}

static void ham_reset(ham_state *s, uint32_t mode) {
    uint8_t *p = (uint8_t *)s;
    for (size_t j = 0; j < sizeof(ham_state); j++) p[j] = 0;
    s->magic = HAM_MAGIC;
    s->mode = mode;
    s->nco_c = 1; s->bfo_c = 1;
    s->agc_env = 1; s->agc_gain = 1;
    ham_set_nco(s);
}

// Change mode (resets filters), frequency offset and squelch. A pure offset
// change keeps all history, so retuning within the band is click-free.
static void ham_configure(ham_state *s, uint32_t mode, float offset_hz, float squelch, uint32_t flags) {
    if (s->magic != HAM_MAGIC || s->mode != mode) ham_reset(s, mode);
    s->offset_hz = offset_hz;
    s->squelch = squelch;
    s->flags = flags;
    ham_set_nco(s);
}

static float ham_clip16(float v) {
    if (v != v) return 0;
    if (v > 32767) return 32767;
    if (v < -32768) return -32768;
    return v;
}

static void ham_put(uint8_t *pcm, size_t *written, float v) {
    int32_t sample = (int32_t)ham_clip16(v);
    pcm[(*written)++] = (uint8_t)sample;
    pcm[(*written)++] = (uint8_t)((uint32_t)sample >> 8);
}

static float ham_biquad(const float *k, float x, float *z1, float *z2) {
    // Transposed direct form II.
    float y = k[0] * x + *z1;
    *z1 = k[1] * x - k[3] * y + *z2;
    *z2 = k[2] * x - k[4] * y;
    return y;
}

// Filter the I and Q histories with one symmetric FIR. hi/hq point at the
// oldest of `taps` contiguous samples (a doubled circular buffer). Folding
// the symmetric halves and sharing each coefficient load between I and Q
// roughly halves the work; two accumulator pairs break the add chain.
static void ham_fir2(const float *k, const float *hi, const float *hq, unsigned taps, float *oi, float *oq) {
    float ai0 = 0, aq0 = 0, ai1 = 0, aq1 = 0;
    const float *ei = hi + taps - 1, *eq = hq + taps - 1;
    for (unsigned j = 0; j < taps / 2; j += 2) {
        float c0 = k[j], c1 = k[j + 1];
        ai0 += c0 * (hi[j] + ei[-(int)j]);
        aq0 += c0 * (hq[j] + eq[-(int)j]);
        ai1 += c1 * (hi[j + 1] + ei[-(int)j - 1]);
        aq1 += c1 * (hq[j + 1] + eq[-(int)j - 1]);
    }
    *oi = ai0 + ai1;
    *oq = aq0 + aq1;
}

static void ham_window_done(ham_state *s) {
    s->power = s->power_acc / (float)s->power_n;
    s->power_acc = 0; s->power_n = 0;
}

// Noise squelch decision every 512 samples (16 ms) with hysteresis.
static void ham_squelch_update(ham_state *s) {
    s->noise = s->noise_acc / (float)s->noise_n;
    s->noise_acc = 0; s->noise_n = 0;
    if (s->squelch <= 0) { s->squelch_open = 1; return; }
    if (s->squelch_open) {
        if (s->noise > s->squelch * 1.25f) s->squelch_open = 0;
    } else if (s->noise < s->squelch) {
        s->squelch_open = 1;
    }
}

// One NFM output sample from the 32 kHz complex sample (i, q).
static float ham_nfm(ham_state *s, float i, float q) {
    unsigned h = s->hn;
    s->fni[h] = i; s->fni[h + HAM_FNFM_TAPS] = i;
    s->fnq[h] = q; s->fnq[h + HAM_FNFM_TAPS] = q;
    if (++h == HAM_FNFM_TAPS) h = 0;
    s->hn = h;
    ham_fir2(ham_fnfm, s->fni + h, s->fnq + h, HAM_FNFM_TAPS, &i, &q);
    s->power_acc += i * i + q * q;
    if (++s->power_n == 512) ham_window_done(s);
    float d = ham_angle(q * s->prev_i - i * s->prev_q, i * s->prev_i + q * s->prev_q);
    s->prev_i = i; s->prev_q = q;
    // Noise squelch: with no carrier the discriminator output is wide-band
    // noise; a received voice channel is band-limited. The first difference
    // weighs the high frequencies.
    float dd = d - s->prev_d;
    s->prev_d = d;
    s->noise_acc += dd * dd;
    if (++s->noise_n == 512) ham_squelch_update(s);
    // 750 us de-emphasis (212 Hz), with gain so that 1 kHz is unity.
    s->deemph += 0.04085f * (d - s->deemph);
    float a = s->deemph * 4.82f;
    // Two high-pass sections: CTCSS tones (67..254 Hz) are not
    // pre-emphasized, so de-emphasis lifts them 10-14 dB above voice.
    a = ham_biquad(ham_nfm_hp, a, &s->hp_z1, &s->hp_z2);
    a = ham_biquad(ham_nfm_hp, a, &s->hp_z3, &s->hp_z4);
    a = ham_biquad(ham_nfm_lp, a, &s->lp_z1, &s->lp_z2);
    // Fade the gate over ~4 ms instead of switching abruptly.
    float target = s->squelch_open ? 1.0f : 0.0f;
    s->gate += 0.008f * (target - s->gate);
    // 3 kHz deviation, a 1 kHz tone, gives about half of full scale.
    return a * 27000.0f * s->gate;
}

// SSB/CW/AM: one 8 kHz complex sample in, one 8 kHz audio sample out.
static float ham_narrow(ham_state *s, float i, float q) {
    unsigned h = s->hc;
    s->fci[h] = i; s->fci[h + HAM_FSSB_TAPS] = i;
    s->fcq[h] = q; s->fcq[h + HAM_FSSB_TAPS] = q;
    if (++h == HAM_FSSB_TAPS) h = 0;
    s->hc = h;
    const float *k = s->mode == HAM_CW ? ham_fcw : (s->mode == HAM_AM ? ham_fam : ham_fssb);
    ham_fir2(k, s->fci + h, s->fcq + h, HAM_FSSB_TAPS, &i, &q);
    s->power_acc += i * i + q * q;
    if (++s->power_n == 128) ham_window_done(s);
    float a;
    if (s->mode == HAM_AM) {
        a = ham_sqrt(i * i + q * q);
        s->am_dc += 0.0005f * (a - s->am_dc);
        a -= s->am_dc;
    } else {
        // Re((i + jq) e^{j bfo n})
        a = i * s->bfo_c - q * s->bfo_s;
        float c = s->bfo_c * s->bfo_sc - s->bfo_s * s->bfo_ss;
        s->bfo_s = s->bfo_c * s->bfo_ss + s->bfo_s * s->bfo_sc;
        s->bfo_c = c;
        if ((s->power_n & 63) == 0) {
            float g = 1.5f - 0.5f * (s->bfo_c * s->bfo_c + s->bfo_s * s->bfo_s);
            s->bfo_c *= g; s->bfo_s *= g;
        }
    }
    // AGC with look-ahead: the envelope sees each sample HAM_AGC_DELAY
    // samples before it is played, so attacks do not overshoot.
    unsigned d = s->ha;
    float out = s->agc_delay[d];
    s->agc_delay[d] = a;
    if (++d == HAM_AGC_DELAY) d = 0;
    s->ha = d;
    float mag = ham_abs(a);
    if (mag > s->agc_env) s->agc_env += 0.25f * (mag - s->agc_env);
    else s->agc_env *= 0.99985f;         // ~0.8 s decay at 8 kHz
    if (s->agc_env < 0.02f) s->agc_env = 0.02f;
    // Target about -9 dBFS peaks; gain limited so band noise stays moderate.
    float gain = 11500.0f / s->agc_env;
    if (gain > 40000.0f) gain = 40000.0f;
    // Smooth gain changes to avoid zipper noise on the look-ahead edge.
    s->agc_gain += 0.05f * (gain - s->agc_gain);
    return out * s->agc_gain;
}

// Caller validates state, buffer sizes, non-overlap, and even input length.
// Writes one PCM sample (2 bytes) per 8 input I/Q samples; returns bytes.
static size_t ham_process(const uint8_t *restrict iq, size_t n, uint8_t *restrict pcm, ham_state *restrict s) {
    size_t written = 0;
    unsigned h1 = s->h1, p1 = s->p1;
    float nc = s->nco_c, ns = s->nco_s, sc = s->nco_sc, ss = s->nco_ss;
    float qsign = (s->flags & HAM_FLAG_CONJUGATE) ? -1.0f : 1.0f;
    for (size_t p = 0; p < n; p += 2) {
        float i = (float)iq[p] - 127.5f, q = ((float)iq[p + 1] - 127.5f) * qsign;
        float ri = i * nc - q * ns, rq = i * ns + q * nc;
        float c = nc * sc - ns * ss;
        ns = nc * ss + ns * sc;
        nc = c;
        s->f1i[h1] = ri; s->f1i[h1 + HAM_F1_TAPS] = ri;
        s->f1q[h1] = rq; s->f1q[h1 + HAM_F1_TAPS] = rq;
        if (++h1 == HAM_F1_TAPS) h1 = 0;
        if (++p1 < 8) continue;
        p1 = 0;
        if (++s->renorm_n == 256) {
            // One Newton step toward |nco| = 1, every 2048 input samples.
            float g = 1.5f - 0.5f * (nc * nc + ns * ns);
            nc *= g; ns *= g;
            s->renorm_n = 0;
        }
        // 32 kHz complex sample.
        float bi, bq;
        ham_fir2(ham_f1, s->f1i + h1, s->f1q + h1, HAM_F1_TAPS, &bi, &bq);
        if (s->mode == HAM_NFM) {
            ham_put(pcm, &written, ham_nfm(s, bi, bq));
            continue;
        }
        unsigned h2 = s->h2;
        s->f2i[h2] = bi; s->f2i[h2 + HAM_F2_TAPS] = bi;
        s->f2q[h2] = bq; s->f2q[h2 + HAM_F2_TAPS] = bq;
        if (++h2 == HAM_F2_TAPS) h2 = 0;
        s->h2 = h2;
        // Interpolator: the 8 kHz audio history, zero-stuffed x4, is
        // filtered one polyphase branch per 32 kHz output.
        unsigned phase = s->p2;
        if (phase == 0) {
            float ni, nq;
            ham_fir2(ham_f2, s->f2i + h2, s->f2q + h2, HAM_F2_TAPS, &ni, &nq);
            float a = ham_narrow(s, ni, nq);
            unsigned hi = s->hint;
            s->fint[hi] = a; s->fint[hi + HAM_FINT_TAPS / 4] = a;
            if (++hi == HAM_FINT_TAPS / 4) hi = 0;
            s->hint = hi;
        }
        // Branch `phase` uses coefficients phase, phase + 4, ... against
        // audio newest-first.
        const float *hist = s->fint + s->hint;
        float acc = 0;
        for (unsigned j = 0; j < HAM_FINT_TAPS / 4; j++)
            acc += ham_fint[phase + 4 * j] * hist[HAM_FINT_TAPS / 4 - 1 - j];
        s->p2 = (phase + 1) & 3;
        ham_put(pcm, &written, acc);
    }
    s->nco_c = nc; s->nco_s = ns;
    s->h1 = h1; s->p1 = p1;
    return written;
}
#endif
