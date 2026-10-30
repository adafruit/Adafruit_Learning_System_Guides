# ft8_lib in ft8_receiver

Vendored from https://github.com/kgoba/ft8_lib at commit
`9fec6ca39886edbf96f4f5e71edc76da5074e871` (2025-08-24, "non-standard
callsigns; special CQ; field type annotation (#47)"). MIT licence (LICENSE);
kissfft is BSD-3-Clause (SPDX headers in fft/).

Only the library parts are here: `ft8/` (all of it) and `fft/`. Not copied:
`common/` (monitor.c, wave.c, audio.c: replaced by `../ft8_core.h`), `demo/`,
`test/`, `utils/`, `ft4_ft8_public/`.

Every file in `ft8/` and `fft/` starts with SPDX copyright and licence
comment lines (for the Learning System Guides' SPDX check); no code changed.

## Edits

All in `fft/`, so that the sources build for the board (no double-precision
FPU, no heap, no stdio) as one translation unit. With the defaults, the host
build behaves as upstream.

- `_kiss_fft_guts.h`: include guard; `KISS_FFT_COS`/`KISS_FFT_SIN` can be
  defined by the includer (`#ifndef`); new `kiss_fft_phase_t` (default
  `double`) for the twiddle phase; `HALF_OF` can be defined by the
  includer (`#ifndef`: single precision on the RISC-V board build).
- `kiss_fft.h`: `KISS_FFT_MALLOC`/`KISS_FFT_FREE` can be defined by the
  includer (`#ifndef`).
- `kiss_fft.c`: twiddle phase as `kiss_fft_phase_t`; `kf_factor` computes
  floor(sqrt(n)) with integers instead of `floor(sqrt((double)n))`.
- `kiss_fftr.c`: super-twiddle phase as `kiss_fft_phase_t`; its `fprintf`
  error messages are inside `#ifndef KISS_FFT_NO_STDIO`.

## Not edits, but changed behaviour (in ../ft8_core.h)

- The waterfall is built by `ft8_feed()` (live, 80 ms rows) in place of
  monitor.c; same layout and scaling, but `log10f` and the window's `sinf`
  are single-precision approximations (`ft8_log2`, `ft8_sincos`), and the
  FFT twiddles use `ft8_sincos` on both builds.
- The candidate search is ft8_lib's `ftx_find_candidates` split into rows
  (same order, same result).
- LDPC: `ft8_bp_decode`, a copy of `bp_decode` with WSJT-X's early stop
  (switchable; on by default on the board) and the parity tables copied to
  the stack.
- The callsign hash table is in caller memory; it is rebuilt (not left with
  holes) when old calls are aged out.
- DT is reported as WSJT-X does (minus 0.5 s) and also minus 0.16 s: the
  demo's times are one symbol late.
- SNR is measured (decoded tones' power against the 10th percentile of the
  waterfall), not `score * 0.5`.
