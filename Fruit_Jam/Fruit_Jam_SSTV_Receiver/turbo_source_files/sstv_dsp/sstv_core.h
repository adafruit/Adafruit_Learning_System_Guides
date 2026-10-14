// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// SSTV receiver demodulator core: 256 ksample/s unsigned 8-bit I/Q in,
// 32 kHz signed 16-bit mono PCM out, one output sample per 8 input samples.
//
//   u8 I/Q -> NCO shift -> 64-tap FIR, /8 -> 32 kHz complex
//          -> 48-tap channel FIR -> discriminator -> de-emphasis,
//             300 Hz high-pass, 3.4 kHz low-pass, noise squelch
//
// This is the NFM path of _ham_dsp (ham_core.h) plus automatic
// frequency control (AFC) for satellite Doppler. At 437 MHz a low-orbit
// satellite drifts by up to about +-11 kHz over a pass and by up to ~250 Hz/s
// near closest approach, more than the +-7.5 kHz channel tolerates.
//
// AFC: the mean of an FM discriminator's output is the carrier's offset from
// where the receiver is tuned, because the modulation averages to zero.
// Every 16 ms window the NCO moves by a fraction of that mean.
//   - Signal in the channel (squelch open): the channel discriminator's mean.
//   - A signal elsewhere in +-16 kHz (the power there has risen 1.5 dB above
//     its slowly tracked floor): a second discriminator on the 32 kHz complex
//     signal before the channel filter. A carrier anywhere in that band pulls
//     its mean toward the carrier in proportion to the carrier's share of
//     the power, enough to bring it into the channel, where the squelch then
//     opens. A satellite keys its transmitter on and off, so it shows up as
//     a step in power.
//   - Neither: return to the nominal frequency (2 s time constant). The
//     wide discriminator is not used on noise alone: the tuner's noise floor
//     is tilted by about a dB across the band, which biases its mean by
//     hundreds of hertz and would walk the AFC off to one side.
// The correction is clamped to +-afc_range around the nominal offset.
//
// There is no DC removal: the caller keeps the wanted signal 12-100 kHz
// from the hardware centre, so after the NCO shift the receiver's DC offset
// lies in the stopband of the first filter.
//
// Caller validates the state buffer and buffer sizes; see _sstv_dsp.c.
#ifndef SSTV_CORE_H
#define SSTV_CORE_H
#include <stdint.h>
#include <stddef.h>
#include "sstv_coeffs.h"

#define SSTV_STATE_BYTES 4096
#define SSTV_MAGIC 0x53535431u
#define SSTV_IN_RATE 256000.0f
#define SSTV_RATE 32000.0f
#define SSTV_WINDOW 512             // 16 ms at 32 kHz

#define SSTV_FLAG_CONJUGATE 1u      // input spectrum is inverted: use conj(I/Q)
#define SSTV_FLAG_GATE 2u           // mute the audio while the squelch is closed
#define SSTV_FLAG_AFC 4u            // track the carrier

// AFC loop gains per 16 ms window: time constants of 0.16 s (channel),
// 0.32 s (wide, scaled down further by the carrier's share of the power) and
// 2 s for the return to nominal.
#define SSTV_AFC_K_CHANNEL 0.1f
#define SSTV_AFC_K_WIDE 0.05f
#define SSTV_AFC_RETURN 0.008f
// Wide-band floor: follows drops within ~0.3 s and rises over ~10 s, so a
// transmitter keying on stands out as "activity" for several seconds.
#define SSTV_FLOOR_DOWN 0.05f
#define SSTV_FLOOR_UP 0.0016f
#define SSTV_ACTIVITY 1.41f         // +1.5 dB over the floor

typedef struct {
    uint32_t magic, flags, squelch_open;
    // NCO: rotates the input by e^{-j 2 pi (offset + afc) n / 256k}.
    float nco_c, nco_s, nco_sc, nco_ss;
    float offset_hz, afc_hz, afc_range, squelch;
    // Measurements over the latest complete 16 ms window. Windows and
    // oscillator renormalization run on sample counts, not per call, so the
    // output does not depend on how the input is split into calls.
    float power, noise, wide_hz, chan_hz, wide_power, floor;
    uint32_t win_n, renorm_n, active;
    float power_acc, noise_acc, wide_acc, chan_acc, wide_pacc;
    // Stage 1: 256k -> 32k.
    uint32_t h1, p1;
    float f1i[2 * SSTV_F1_TAPS], f1q[2 * SSTV_F1_TAPS];
    float wprev_i, wprev_q;
    // Channel and audio at 32k.
    uint32_t hn;
    float fni[2 * SSTV_FNFM_TAPS], fnq[2 * SSTV_FNFM_TAPS];
    float prev_i, prev_q, prev_d, deemph, gate;
    float hp_z1, hp_z2, hp_z3, hp_z4, lp_z1, lp_z2;
} sstv_state;
typedef char sstv_state_size_check[(sizeof(sstv_state) <= SSTV_STATE_BYTES) ? 1 : -1];
typedef char sstv_fir_taps_check[(SSTV_F1_TAPS % 4 == 0 && SSTV_FNFM_TAPS % 4 == 0) ? 1 : -1];

static float sstv_abs(float x) { return __builtin_fabsf(x); }

// sin and cos of x in [-pi, pi]; relative error below 1e-7 near 0, which
// matters because NCO steps are small angles.
static void sstv_sincos(float x, float *s, float *c) {
    float sign_c = 1.0f;
    if (x > 1.57079632679f) { x = 3.14159265359f - x; sign_c = -1.0f; }
    else if (x < -1.57079632679f) { x = -3.14159265359f - x; sign_c = -1.0f; }
    float x2 = x * x;
    *s = x * (1.0f + x2 * (-1.0f / 6 + x2 * (1.0f / 120 + x2 * (-1.0f / 5040 + x2 * (1.0f / 362880 + x2 * (-1.0f / 39916800))))));
    *c = sign_c * (1.0f + x2 * (-0.5f + x2 * (1.0f / 24 + x2 * (-1.0f / 720 + x2 * (1.0f / 40320 + x2 * (-1.0f / 3628800 + x2 * (1.0f / 479001600)))))));
}

// atan on [0,1], max error approximately 1.2e-5 radians.
static float sstv_atan(float z) {
    float z2 = z * z;
    return z * (0.9998660f + z2 * (-0.3302995f + z2 * (0.1801410f + z2 * (-0.0851330f + z2 * 0.0208351f))));
}
static float sstv_angle(float y, float x) {
    float ax = sstv_abs(x), ay = sstv_abs(y), angle;
    if (ax == 0 && ay == 0) return 0;
    if (ax >= ay) angle = sstv_atan(ay / ax);
    else angle = 1.57079632679f - sstv_atan(ax / ay);
    if (x < 0) angle = 3.14159265359f - angle;
    return y < 0 ? -angle : angle;
}

// Angle 2 pi f / rate wrapped to [-pi, pi].
static float sstv_angle_step(float f, float rate) {
    float turns = f / rate;
    turns -= (float)(int32_t)turns;
    if (turns > 0.5f) turns -= 1.0f;
    if (turns < -0.5f) turns += 1.0f;
    return turns * 6.28318530718f;
}

static void sstv_set_nco(sstv_state *s) {
    float sn, cs;
    sstv_sincos(-sstv_angle_step(s->offset_hz + s->afc_hz, SSTV_IN_RATE), &sn, &cs);
    s->nco_sc = cs; s->nco_ss = sn;
}

static void sstv_reset(sstv_state *s) {
    uint8_t *p = (uint8_t *)s;
    for (size_t j = 0; j < sizeof(sstv_state); j++) p[j] = 0;
    s->magic = SSTV_MAGIC;
    s->nco_c = 1;
    sstv_set_nco(s);
}

// Set the nominal offset, squelch, flags and AFC range. Filter history and
// the AFC correction are kept, so this is click-free; a change of more than
// afc_range in the nominal offset (a new frequency) restarts the AFC.
static void sstv_configure(sstv_state *s, float offset_hz, float squelch, uint32_t flags, float afc_range) {
    if (s->magic != SSTV_MAGIC) sstv_reset(s);
    float moved = offset_hz - s->offset_hz;
    if (sstv_abs(moved) > afc_range) s->floor = 0;   // new frequency: measure the floor again
    if (sstv_abs(moved) > afc_range || !(flags & SSTV_FLAG_AFC)) s->afc_hz = 0;
    s->offset_hz = offset_hz;
    s->squelch = squelch;
    s->flags = flags;
    s->afc_range = afc_range;
    if (s->afc_hz > afc_range) s->afc_hz = afc_range;
    if (s->afc_hz < -afc_range) s->afc_hz = -afc_range;
    sstv_set_nco(s);
}

static float sstv_clip16(float v) {
    if (v != v) return 0;
    if (v > 32767) return 32767;
    if (v < -32768) return -32768;
    return v;
}

static void sstv_put(uint8_t *pcm, size_t *written, float v) {
    int32_t sample = (int32_t)sstv_clip16(v);
    pcm[(*written)++] = (uint8_t)sample;
    pcm[(*written)++] = (uint8_t)((uint32_t)sample >> 8);
}

static float sstv_biquad(const float *k, float x, float *z1, float *z2) {
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
static void sstv_fir2(const float *k, const float *hi, const float *hq, unsigned taps, float *oi, float *oq) {
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

// End of a 16 ms window: squelch decision (with hysteresis) and AFC step.
static void sstv_window_done(sstv_state *s) {
    const float to_hz = SSTV_RATE / 6.28318530718f / SSTV_WINDOW;
    s->power = s->power_acc / SSTV_WINDOW;
    s->noise = s->noise_acc / SSTV_WINDOW;
    s->wide_hz = s->wide_acc * to_hz;
    s->chan_hz = s->chan_acc * to_hz;
    s->wide_power = s->wide_pacc / SSTV_WINDOW;
    s->power_acc = s->noise_acc = s->wide_acc = s->chan_acc = s->wide_pacc = 0;
    s->win_n = 0;
    float wp = s->wide_power;
    if (!(s->floor > 0)) s->floor = wp;
    s->active = wp > s->floor * SSTV_ACTIVITY;
    s->floor += (wp < s->floor ? SSTV_FLOOR_DOWN : SSTV_FLOOR_UP) * (wp - s->floor);
    if (s->squelch <= 0) s->squelch_open = 1;
    else if (s->squelch_open) {
        if (s->noise > s->squelch * 1.25f) s->squelch_open = 0;
    } else if (s->noise < s->squelch) {
        s->squelch_open = 1;
    }
    if (!(s->flags & SSTV_FLAG_AFC)) return;
    // With the squelch off (0) "open" means nothing; use the carrier test
    // at the default level instead.
    int carrier = s->squelch > 0 ? (int)s->squelch_open : s->noise < 1.0f;
    float afc = s->afc_hz;
    if (carrier) afc += SSTV_AFC_K_CHANNEL * s->chan_hz;
    else if (s->active) afc += SSTV_AFC_K_WIDE * s->wide_hz;
    else afc -= SSTV_AFC_RETURN * afc;
    if (afc > s->afc_range) afc = s->afc_range;
    if (afc < -s->afc_range) afc = -s->afc_range;
    s->afc_hz = afc;
    sstv_set_nco(s);
}

// One audio sample from the 32 kHz complex sample (i, q).
static float sstv_demod(sstv_state *s, float i, float q) {
    // Wide discriminator, before the channel filter (AFC acquisition only).
    s->wide_acc += sstv_angle(q * s->wprev_i - i * s->wprev_q, i * s->wprev_i + q * s->wprev_q);
    s->wide_pacc += i * i + q * q;
    s->wprev_i = i; s->wprev_q = q;
    unsigned h = s->hn;
    s->fni[h] = i; s->fni[h + SSTV_FNFM_TAPS] = i;
    s->fnq[h] = q; s->fnq[h + SSTV_FNFM_TAPS] = q;
    if (++h == SSTV_FNFM_TAPS) h = 0;
    s->hn = h;
    sstv_fir2(sstv_fnfm, s->fni + h, s->fnq + h, SSTV_FNFM_TAPS, &i, &q);
    s->power_acc += i * i + q * q;
    float d = sstv_angle(q * s->prev_i - i * s->prev_q, i * s->prev_i + q * s->prev_q);
    s->prev_i = i; s->prev_q = q;
    s->chan_acc += d;
    // Noise squelch: with no carrier the discriminator output is wide-band
    // noise; a received channel is band-limited. The first difference
    // weighs the high frequencies.
    float dd = d - s->prev_d;
    s->prev_d = d;
    s->noise_acc += dd * dd;
    if (++s->win_n == SSTV_WINDOW) sstv_window_done(s);
    // 750 us de-emphasis (212 Hz), with gain so that 1 kHz is unity.
    s->deemph += 0.04085f * (d - s->deemph);
    float a = s->deemph * 4.82f;
    a = sstv_biquad(sstv_audio_hp, a, &s->hp_z1, &s->hp_z2);
    a = sstv_biquad(sstv_audio_hp, a, &s->hp_z3, &s->hp_z4);
    a = sstv_biquad(sstv_audio_lp, a, &s->lp_z1, &s->lp_z2);
    // Fade the gate over ~4 ms instead of switching abruptly.
    float target = (s->squelch_open || !(s->flags & SSTV_FLAG_GATE)) ? 1.0f : 0.0f;
    s->gate += 0.008f * (target - s->gate);
    // 3 kHz deviation, a 1 kHz tone, gives about half of full scale.
    return a * 27000.0f * s->gate;
}

// Caller validates state, buffer sizes, non-overlap, and even input length.
// Writes one PCM sample (2 bytes) per 8 input I/Q samples; returns bytes.
static size_t sstv_process(const uint8_t *restrict iq, size_t n, uint8_t *restrict pcm, sstv_state *restrict s) {
    size_t written = 0;
    unsigned h1 = s->h1, p1 = s->p1;
    float nc = s->nco_c, ns = s->nco_s;
    float qsign = (s->flags & SSTV_FLAG_CONJUGATE) ? -1.0f : 1.0f;
    for (size_t p = 0; p < n; p += 2) {
        float i = (float)iq[p] - 127.5f, q = ((float)iq[p + 1] - 127.5f) * qsign;
        float ri = i * nc - q * ns, rq = i * ns + q * nc;
        // The AFC may change the step at any window end, so read it here.
        float sc = s->nco_sc, ss = s->nco_ss;
        float c = nc * sc - ns * ss;
        ns = nc * ss + ns * sc;
        nc = c;
        s->f1i[h1] = ri; s->f1i[h1 + SSTV_F1_TAPS] = ri;
        s->f1q[h1] = rq; s->f1q[h1 + SSTV_F1_TAPS] = rq;
        if (++h1 == SSTV_F1_TAPS) h1 = 0;
        if (++p1 < 8) continue;
        p1 = 0;
        if (++s->renorm_n == 256) {
            // One Newton step toward |nco| = 1, every 2048 input samples.
            float g = 1.5f - 0.5f * (nc * nc + ns * ns);
            nc *= g; ns *= g;
            s->renorm_n = 0;
        }
        float bi, bq;
        sstv_fir2(sstv_f1, s->f1i + h1, s->f1q + h1, SSTV_F1_TAPS, &bi, &bq);
        sstv_put(pcm, &written, sstv_demod(s, bi, bq));
    }
    s->nco_c = nc; s->nco_s = ns;
    s->h1 = h1; s->p1 = p1;
    return written;
}
#endif
