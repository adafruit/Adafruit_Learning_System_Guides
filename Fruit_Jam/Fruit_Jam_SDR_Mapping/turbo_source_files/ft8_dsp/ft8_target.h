// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// What the board build of ft8_lib needs from a C library that a native
// module does not have. Included by ft8_core.h before the ft8_lib sources
// when FT8_TARGET is defined. memset, memcpy and memmove come from
// CircuitPython (mpy_ld links them to its function table).
#ifndef FT8_TARGET_H
#define FT8_TARGET_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

// ft8_lib's debug logging (debug.h) and kissfft's error messages: off.
#define LOG_PRINTF(...) ((void)0)
#define KISS_FFT_NO_STDIO
// No heap: the FFT configuration always goes in caller memory, and the
// in-place FFT path (which would allocate) is never used.
#define KISS_FFT_MALLOC(n) ((void *)0)
#define KISS_FFT_FREE(p) ((void)0)
// kissfft calls exit() on misuse (in void functions): return instead.
#define exit(code) return

// String functions used by ft8_lib's message packing (renamed, so the
// compiler does not treat them as its built-ins).
static char *ft8_strcpy(char *d, const char *s) {
    char *r = d;
    while ((*d++ = *s++) != '\0') {
    }
    return r;
}
static char *ft8_stpcpy(char *d, const char *s) {
    while ((*d = *s++) != '\0') d++;
    return d;
}
static size_t ft8_strlen(const char *s) {
    size_t n = 0;
    while (s[n]) n++;
    return n;
}
static char *ft8_strcat(char *d, const char *s) {
    ft8_strcpy(d + ft8_strlen(d), s);
    return d;
}
static char *ft8_strchr(const char *s, int c) {
    for (;; s++) {
        if (*s == (char)c) return (char *)s;
        if (!*s) return NULL;
    }
}
static int ft8_strcmp(const char *a, const char *b) {
    while (*a && *a == *b) a++, b++;
    return (unsigned char)*a - (unsigned char)*b;
}
static char *ft8_strncpy(char *d, const char *s, size_t n) {
    size_t i = 0;
    for (; i < n && s[i]; i++) d[i] = s[i];
    for (; i < n; i++) d[i] = '\0';
    return d;
}
static int ft8_memcmp(const void *a, const void *b, size_t n) {
    const unsigned char *x = a, *y = b;
    for (size_t i = 0; i < n; i++) {
        if (x[i] != y[i]) return x[i] - y[i];
    }
    return 0;
}
static int ft8_atoi(const char *s) {
    int sign = 1, v = 0;
    while (*s == ' ') s++;
    if (*s == '+' || *s == '-') sign = (*s++ == '-') ? -1 : 1;
    while (*s >= '0' && *s <= '9') v = 10 * v + (*s++ - '0');
    return sign * v;
}
#define memcmp ft8_memcmp
#define atoi ft8_atoi
#define strcpy ft8_strcpy
#define stpcpy ft8_stpcpy
#define strlen ft8_strlen
#define strcat ft8_strcat
#define strchr ft8_strchr
#define strcmp ft8_strcmp
#define strncpy ft8_strncpy

#endif
