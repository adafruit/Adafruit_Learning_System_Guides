// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
// SPDX-License-Identifier: GPL-3.0-or-later
// Freestanding C library functions for the native module. A native .mpy is not
// linked against the firmware's libc (and the ESP toolchain's libc/libgcc are not
// position independent), so the few functions the compiler emits calls to are
// defined here. Force-included into tf_api.cpp by the Makefile.
#pragma once

#include <stddef.h>
#include <stdint.h>

extern "C" {

void* memcpy(void* dst, const void* src, size_t n) {
    unsigned char*       d = static_cast<unsigned char*>(dst);
    const unsigned char* s = static_cast<const unsigned char*>(src);
    if (((uintptr_t(d) | uintptr_t(s) | n) & 3) == 0)
    {
        uint32_t*       dw = reinterpret_cast<uint32_t*>(d);
        const uint32_t* sw = reinterpret_cast<const uint32_t*>(s);
        for (size_t i = 0; i < n / 4; i++)
            dw[i] = sw[i];
        return dst;
    }
    while (n--)
        *d++ = *s++;
    return dst;
}

void* memmove(void* dst, const void* src, size_t n) {
    unsigned char*       d = static_cast<unsigned char*>(dst);
    const unsigned char* s = static_cast<const unsigned char*>(src);
    if (d < s)
        while (n--)
            *d++ = *s++;
    else
        while (n--)
            d[n] = s[n];
    return dst;
}

void* memset(void* dst, int c, size_t n) {
    unsigned char* d = static_cast<unsigned char*>(dst);
    if (((uintptr_t(d) | n) & 3) == 0)
    {
        uint32_t  w  = 0x01010101u * uint8_t(c);
        uint32_t* dw = reinterpret_cast<uint32_t*>(d);
        for (size_t i = 0; i < n / 4; i++)
            dw[i] = w;
        return dst;
    }
    while (n--)
        *d++ = uint8_t(c);
    return dst;
}

size_t strlen(const char* s) {
    size_t n = 0;
    while (s[n])
        n++;
    return n;
}

// libgcc helpers GCC calls on rv32 (both only on cold paths: FEN parsing and once
// per root move). The real libgcc can't be linked: it isn't position independent.
long long __ashldi3(long long a, int b) {
    uint32_t lo = uint32_t(a), hi = uint32_t(uint64_t(a) >> 32);
    if (b >= 32)
    {
        hi = lo << (b - 32);
        lo = 0;
    }
    else if (b > 0)
    {
        hi = (hi << b) | (lo >> (32 - b));
        lo <<= b;
    }
    return (long long) ((uint64_t(hi) << 32) | lo);
}

// Only an -Os build calls this (-O2 inlines 64-bit shifts)
long long __lshrdi3(long long a, int b) {
    uint32_t lo = uint32_t(a), hi = uint32_t(uint64_t(a) >> 32);
    if (b >= 32)
    {
        lo = hi >> (b - 32);
        hi = 0;
    }
    else if (b > 0)
    {
        lo = (lo >> b) | (hi << (32 - b));
        hi >>= b;
    }
    return (long long) ((uint64_t(hi) << 32) | lo);
}

// Only an -Os build calls this
long long __ashrdi3(long long a, int b) {
    int32_t  hi = int32_t(uint64_t(a) >> 32);
    uint32_t lo = uint32_t(a);
    if (b >= 32)
    {
        lo = uint32_t(hi >> (b - 32));
        hi = hi >> 31;
    }
    else if (b > 0)
    {
        lo = (lo >> b) | (uint32_t(hi) << (32 - b));
        hi >>= b;
    }
    return (long long) ((uint64_t(uint32_t(hi)) << 32) | lo);
}

unsigned long long __udivdi3(unsigned long long n, unsigned long long d) {
    if (d == 0)
        return 0;
    unsigned long long q = 0, r = 0;
    for (int i = 63; i >= 0; i--)
    {
        r = (r << 1) | ((n >> i) & 1);
        if (r >= d)
        {
            r -= d;
            q |= 1ULL << i;
        }
    }
    return q;
}

}  // extern "C"
