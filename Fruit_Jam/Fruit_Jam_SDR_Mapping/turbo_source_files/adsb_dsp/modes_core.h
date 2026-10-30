// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Mode S / ADS-B decoder for short 2 MS/s 8-bit I/Q snapshots (the
// RTL2832U's EPA FIFO after a reset: 3760 bytes, 940 us). Plain C, no
// allocation, no libc: the same code runs on the board (_adsb.c) and on the
// PC (for tests).
//
// Per snapshot:
//  - magnitude of every sample (x16, uint16), and the mean as the noise level;
//  - preamble search: at every sample j, the four preamble pulses (0, 1,
//    3.5, 4.5 us; each in sample j+k or the next, whatever the timing phase)
//    must stand above the noise and above the quiet spots between and after
//    them;
//  - each preamble that passes is demodulated. 2 MS/s is one sample per
//    0.5 us chip, and when the samples fall on the chip edges each one is
//    half of two chips, so "first chip > second chip" fails. Instead the
//    pulse response is fitted on the preamble (the magnitude at sample n as
//    d + a*chip[n+1] + b*chip[n] + e*chip[n-1]) and a 2-state Viterbi finds
//    the bits that best explain the magnitudes. Then the Mode S CRC-24:
//    DF17/18 with a clean CRC, DF11 with a CRC residual < 128 (the
//    interrogator code) are accepted; a DF17/18 with one wrong bit is fixed
//    (its syndrome), or with two among the 12 least reliable bits (the
//    Viterbi's fit with each bit flipped); DF0/4/5/16/20/21, whose parity is
//    the address, are accepted when the address is a known aircraft;
//  - accepted messages are written to `out` as MODES_RECORD-byte records.
// "Known" aircraft: addresses seen in a DF11 or a clean DF17/18 in the
// last MODES_KNOWN_SECONDS.
#pragma once
#include <stdint.h>
#include "modes_tables.h"

#define MODES_MAGIC 0x41445342u  // "ADSB"
#define MODES_MAX_SAMPLES 4096
#define MODES_PAD 300            // a 112-bit message is 240 samples
#define MODES_KNOWN 256          // open-addressed table of known addresses
#define MODES_KNOWN_SECONDS 120
#define MODES_RECORD 24

// Record layout (little endian):
//  0      message length in bytes (7 or 14)
//  1      flags: bit 0 one or two bits fixed, bit 1 address/parity matched a known
//         aircraft, bits 2-3 which start sample decoded (0: the preamble's
//         first pulse sample j, 1: j + 1, 2: j - 1)
//  2..3   signal: the fitted pulse amplitude a + b + e (x16)
//  4..5   noise: mean magnitude of the snapshot (x16)
//  6..7   sample index of the preamble's first pulse in the snapshot
//  8..21  the message (14 bytes; a 7-byte message leaves 7 zeros)
//  22..23 reserved

#define MODES_FLAG_FIXED 1
#define MODES_FLAG_AP 2

typedef struct {
    uint32_t magic;
    // settings
    uint32_t pulse_ratio_x16;   // preamble pulses must reach noise * ratio / 16
    uint32_t quiet_ratio_x16;   // quiet spots below mean pulse * ratio / 16
    // counters
    uint32_t snapshots, samples, candidates, demods, accepted;
    uint32_t df17, df11, ap, fixed, crc_fail, ap_unknown;
    uint32_t fixed2;            // DF17s with two bits fixed (fixed: one)
    uint32_t noise_x16;         // last snapshot's noise
    // tables
    uint32_t crc_table[256];
    uint32_t syndrome[112];     // CRC residual of a 112-bit message with only bit i set
    uint32_t known_addr[MODES_KNOWN];   // 0: empty (address 0 is never stored)
    uint32_t known_time[MODES_KNOWN];
    uint16_t mag[MODES_MAX_SAMPLES + MODES_PAD];
} modes_state;

#define MODES_STATE_BYTES ((int)sizeof(modes_state))

static uint32_t modes_crc(const modes_state *s, const uint8_t *data, int n) {
    uint32_t c = 0;
    for (int i = 0; i < n; i++)
        c = ((c << 8) & 0xFFFFFF) ^ s->crc_table[((c >> 16) ^ data[i]) & 255];
    return c;
}

// CRC of the message minus its last three bytes, xor those bytes: 0 for a
// clean DF17, the address for DF0/4/5/16/20/21, the IID for DF11.
static uint32_t modes_residual(const modes_state *s, const uint8_t *msg, int nbytes) {
    uint32_t p = ((uint32_t)msg[nbytes - 3] << 16) | ((uint32_t)msg[nbytes - 2] << 8) | msg[nbytes - 1];
    return modes_crc(s, msg, nbytes - 3) ^ p;
}

static void modes_reset(modes_state *s) {
    uint8_t *p = (uint8_t *)s;
    for (int i = 0; i < (int)sizeof(modes_state); i++)
        p[i] = 0;
    s->magic = MODES_MAGIC;
    s->pulse_ratio_x16 = 40;   // 2.5 x the mean noise magnitude
    s->quiet_ratio_x16 = 9;    // quiet spots below 0.56 x the mean pulse
    for (uint32_t b = 0; b < 256; b++) {
        uint32_t c = b << 16;
        for (int k = 0; k < 8; k++)
            c = (c & 0x800000) ? ((c << 1) ^ 0xFFF409) : (c << 1);
        s->crc_table[b] = c & 0xFFFFFF;
    }
    for (int i = 0; i < 112; i++) {
        uint8_t m[14] = {0};
        m[i >> 3] = 0x80 >> (i & 7);
        s->syndrome[i] = modes_residual(s, m, 14);
    }
}

static uint32_t modes_hash(uint32_t a) {
    return ((a * 2654435761u) >> 24) & (MODES_KNOWN - 1);
}

static int modes_known(const modes_state *s, uint32_t addr, uint32_t now) {
    if (!addr)
        return 0;
    uint32_t h = modes_hash(addr);
    for (int k = 0; k < MODES_KNOWN; k++) {
        uint32_t i = (h + k) & (MODES_KNOWN - 1);
        if (s->known_addr[i] == 0)
            return 0;
        if (s->known_addr[i] == addr)
            return now - s->known_time[i] <= MODES_KNOWN_SECONDS;
    }
    return 0;
}

static void modes_remember(modes_state *s, uint32_t addr, uint32_t now) {
    if (!addr)
        return;
    uint32_t h = modes_hash(addr);
    int stale = -1;
    for (int k = 0; k < MODES_KNOWN; k++) {
        uint32_t i = (h + k) & (MODES_KNOWN - 1);
        if (s->known_addr[i] == addr || s->known_addr[i] == 0) {
            s->known_addr[i] = addr;
            s->known_time[i] = now;
            return;
        }
        if (stale < 0 && now - s->known_time[i] > MODES_KNOWN_SECONDS)
            stale = i;
    }
    // Full: reuse an expired slot (keeps the probe chains intact).
    if (stale >= 0) {
        s->known_addr[stale] = addr;
        s->known_time[stale] = now;
    }
}

// Viterbi demodulation of nbits bits from sample j (the preamble's first
// pulse), with the pulse response fitted on the preamble. The state is the
// previous bit; the two samples 15+2i and 16+2i depend only on bits i-1 and
// i: sample n is d + a*c[n+1] + b*c[n] + e*c[n-1], and bit i's chips are
// c[16+2i] = bit, c[17+2i] = !bit.
static void modes_viterbi(const uint16_t *mag, int j, int nbits, const float *f, uint8_t *msg, float *rel) {
    float d = f[0], a = f[1], b = f[2], e = f[3];
    const uint16_t *m = mag + j;
    uint8_t from[112];          // bit i: the best previous bit for state 0 (bit 0) and 1 (bit 1)
    float met[2];
    for (int bit = 0; bit < 2; bit++) {
        // c[14] = c[15] = 0 (preamble), c[16] = bit, c[17] = !bit
        float x15 = d + a * bit - m[15] * (1.0f / 16);
        float x16 = d + a * (1 - bit) + b * bit - m[16] * (1.0f / 16);
        met[bit] = x15 * x15 + x16 * x16;
    }
    from[0] = 0;
    for (int i = 1; i < nbits; i++) {
        float y1 = m[15 + 2 * i] * (1.0f / 16), y2 = m[16 + 2 * i] * (1.0f / 16);
        float nm[2];
        uint8_t fr = 0;
        for (int bit = 0; bit < 2; bit++) {
            float best = 0;
            for (int bp = 0; bp < 2; bp++) {
                float x1 = d + a * bit + b * (1 - bp) + e * bp - y1;
                float x2 = d + a * (1 - bit) + b * bit + e * (1 - bp) - y2;
                float v = met[bp] + x1 * x1 + x2 * x2;
                if (bp == 0 || v < best) {
                    best = v;
                    if (bp) fr |= 1 << bit; else fr &= ~(1 << bit);
                }
            }
            nm[bit] = best;
        }
        met[0] = nm[0];
        met[1] = nm[1];
        from[i] = fr;
    }
    // After the last bit (c[16+2n] = c[17+2n] = 0): sample 15+2n is
    // b*c[15+2n] + e*c[14+2n] = b*!bit + e*bit, sample 16+2n is e*!bit.
    float y1 = m[15 + 2 * nbits] * (1.0f / 16), y2 = m[16 + 2 * nbits] * (1.0f / 16);
    for (int bit = 0; bit < 2; bit++) {
        float x1 = d + b * (1 - bit) + e * bit - y1;
        float x2 = d + e * (1 - bit) - y2;
        met[bit] += x1 * x1 + x2 * x2;
    }
    int bit = met[1] < met[0];
    for (int i = 0; i < 14; i++)
        msg[i] = 0;
    for (int i = nbits - 1; i >= 0; i--) {
        if (bit)
            msg[i >> 3] |= 0x80 >> (i & 7);
        bit = (from[i] >> bit) & 1;
    }
    if (!rel)
        return;
    // Each bit's reliability: how much worse the four samples it touches
    // (15+2i .. 18+2i) fit with that bit flipped and the others kept.
    uint8_t c[16 + 2 * 112 + 4];
    for (int t = 0; t < 16; t++)
        c[t] = (0xA140 >> (15 - t)) & 1;   // 1010 0001 0100 0000
    for (int i = 0; i < nbits; i++) {
        int b = (msg[i >> 3] >> (7 - (i & 7))) & 1;
        c[16 + 2 * i] = b;
        c[17 + 2 * i] = !b;
    }
    for (int t = 16 + 2 * nbits; t < 16 + 2 * nbits + 4; t++)
        c[t] = 0;
    for (int i = 0; i < nbits; i++) {
        float good = 0, flip = 0;
        int t0 = 16 + 2 * i;
        for (int k = 15 + 2 * i; k <= 18 + 2 * i; k++) {
            float y = m[k] * (1.0f / 16);
            float x = d + a * c[k + 1] + b * c[k] + e * c[k - 1] - y;
            good += x * x;
            // the same with chips t0 and t0+1 swapped
            int cn1 = c[k + 1], cn = c[k], cp = c[k - 1];
            if (k + 1 == t0 || k + 1 == t0 + 1) cn1 = !cn1;
            if (k == t0 || k == t0 + 1) cn = !cn;
            if (k - 1 == t0 || k - 1 == t0 + 1) cp = !cp;
            x = d + a * cn1 + b * cn + e * cp - y;
            flip += x * x;
        }
        rel[i] = flip - good;
    }
}

#define MODES_SOFT 12         // the least reliable bits tried in pairs

// The CRC checks; 1 to accept msg (fixed in place if one or two bits were
// wrong). rel: the bits' reliabilities (from modes_viterbi).
static int modes_check(modes_state *s, uint8_t *msg, int nb, uint32_t now, int *flags, const float *rel) {
    int df = msg[0] >> 3;
    uint32_t r = modes_residual(s, msg, nb);
    uint32_t addr = ((uint32_t)msg[1] << 16) | ((uint32_t)msg[2] << 8) | msg[3];
    *flags = 0;
    if (df == 17 || df == 18) {
        if (r == 0) {
            modes_remember(s, addr, now);
            s->df17++;
            return 1;
        }
        // One wrong bit anywhere after the DF: its syndrome is the residual.
        // Junk passes with odds of 1/16 (DF) x 107 / 2^24: about 4e-7.
        for (int b = 5; b < 112; b++) {
            if (s->syndrome[b] != r)
                continue;
            msg[b >> 3] ^= 0x80 >> (b & 7);
            *flags = MODES_FLAG_FIXED;
            s->df17++;
            s->fixed++;
            return 1;
        }
        // Two wrong bits among the MODES_SOFT least reliable ones.
        int weak[MODES_SOFT];
        int nw = 0;
        for (int b = 5; b < 112; b++) {
            int k = nw < MODES_SOFT ? nw++ : MODES_SOFT;
            if (k == MODES_SOFT) {
                if (rel[b] >= rel[weak[MODES_SOFT - 1]])
                    continue;
                k = MODES_SOFT - 1;
            }
            while (k > 0 && rel[weak[k - 1]] > rel[b]) {
                weak[k] = weak[k - 1];
                k--;
            }
            weak[k] = b;
        }
        for (int x = 0; x < nw; x++)
            for (int y = x + 1; y < nw; y++) {
                if ((s->syndrome[weak[x]] ^ s->syndrome[weak[y]]) != r)
                    continue;
                msg[weak[x] >> 3] ^= 0x80 >> (weak[x] & 7);
                msg[weak[y] >> 3] ^= 0x80 >> (weak[y] & 7);
                *flags = MODES_FLAG_FIXED;
                s->df17++;
                s->fixed2++;
                return 1;
            }
        return 0;
    }
    if (df == 11) {
        // The parity is xored with the interrogator's code (0..127). A
        // random 56 bits pass with odds of 2^-17 (and 1/32 for the DF),
        // so these are trusted, as dump1090 does.
        if (r < 128) {
            modes_remember(s, addr, now);
            s->df11++;
            return 1;
        }
        return 0;
    }
    if (df == 0 || df == 4 || df == 5 || df == 16 || df == 20 || df == 21) {
        if (modes_known(s, r, now)) {
            *flags = MODES_FLAG_AP;
            s->ap++;
            modes_remember(s, r, now);
            return 1;
        }
        s->ap_unknown++;
    }
    return 0;
}

static int modes_decode(modes_state *s, const uint8_t *iq, int nbytes, uint8_t *out, int out_len, uint32_t now) {
    int n = nbytes / 2;
    if (n > MODES_MAX_SAMPLES)
        n = MODES_MAX_SAMPLES;
    uint16_t *mag = s->mag;
    uint32_t sum = 0;
    for (int i = 0; i < n; i++) {
        float a = (float)iq[2 * i] - 127.4f, b = (float)iq[2 * i + 1] - 127.4f;
        uint32_t m = (uint32_t)(__builtin_sqrtf(a * a + b * b) * 16.0f + 0.5f);
        mag[i] = m > 65535 ? 65535 : m;
        sum += m;
    }
    for (int i = n; i < n + MODES_PAD; i++)
        mag[i] = 0;
    s->snapshots++;
    s->samples += n;
    if (n < 16 + 2 * 56 + 4)
        return 0;
    uint32_t noise = sum / n;   // x16
    if (noise < 8)
        noise = 8;              // half a count: an all-quiet snapshot
    s->noise_x16 = noise;
    uint32_t pulse_min = noise * s->pulse_ratio_x16 / 16;
    int found = 0;
    int last = n - (16 + 2 * 56 + 2);   // a short message must fit
    for (int j = 2; j < last; j++) {
        uint32_t h0 = mag[j] > mag[j + 1] ? mag[j] : mag[j + 1];
        if (h0 < pulse_min)
            continue;
        uint32_t h7 = mag[j + 7] > mag[j + 8] ? mag[j + 7] : mag[j + 8];
        if (h7 < pulse_min)
            continue;
        uint32_t h2 = mag[j + 2] > mag[j + 3] ? mag[j + 2] : mag[j + 3];
        uint32_t h9 = mag[j + 9] > mag[j + 10] ? mag[j + 9] : mag[j + 10];
        if (h2 < pulse_min || h9 < pulse_min || mag[j - 1] >= h0)
            continue;
        uint32_t quiet = (h0 + h2 + h7 + h9) / 4 * s->quiet_ratio_x16 / 16;
        if (mag[j + 5] >= quiet || mag[j + 6] >= quiet || mag[j + 12] >= quiet
                || mag[j + 13] >= quiet || mag[j + 14] >= quiet)
            continue;
        s->candidates++;
        static const int8_t starts[3] = {0, 1, -1};
        for (int k = 0; k < 3; k++) {
            int jj = j + starts[k];
            float f[4];
            for (int r = 0; r < 4; r++) {
                float v = 0;
                for (int t = 0; t < 16; t++)
                    v += MODES_FIT[r][t] * mag[jj - 1 + t];
                f[r] = v * (1.0f / 16);
            }
            if (f[1] + f[2] + f[3] <= 0)
                continue;
            uint8_t msg[14];
            float rel[112];
            if (jj + 16 + 2 * 56 >= n)
                continue;
            modes_viterbi(mag, jj, 56, f, msg, 0);
            int nbits = 56;
            if (msg[0] & 0x80) {
                nbits = 112;
                if (jj + 16 + 2 * nbits >= n)
                    continue;   // runs off the snapshot's end
                modes_viterbi(mag, jj, 112, f, msg, rel);
            }
            s->demods++;
            int nb = nbits / 8, flags;
            if (!modes_check(s, msg, nb, now, &flags, rel)) {
                s->crc_fail++;
                continue;
            }
            s->accepted++;
            if ((found + 1) * MODES_RECORD <= out_len) {
                uint8_t *rec = out + found * MODES_RECORD;
                float amp = (f[1] + f[2] + f[3]) * 16;
                uint32_t sig = amp > 65535 ? 65535 : (uint32_t)amp;
                rec[0] = nb;
                rec[1] = flags | (k << 2);
                rec[2] = sig & 255; rec[3] = (sig >> 8) & 255;
                rec[4] = noise & 255; rec[5] = (noise >> 8) & 255;
                rec[6] = jj & 255; rec[7] = (jj >> 8) & 255;
                for (int i = 0; i < 14; i++)
                    rec[8 + i] = i < nb ? msg[i] : 0;
                rec[22] = rec[23] = 0;
                found++;
            }
            j = jj + 16 + 2 * nbits - 2;   // past this message
            break;
        }
    }
    return found;
}
