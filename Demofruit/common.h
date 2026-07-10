// common.h — shared infrastructure for the Fruit Jam Demoscene Sampler
// Buttons, launch scratch registers, color helper, shared memory arena.

#pragma once
#include <Arduino.h>
#include <hardware/watchdog.h>

// ── RGB565 helper (single definition for all demos) ──────────────────────────
#define C565(r,g,b) ((uint16_t)((((r)>>3)<<11)|(((g)>>2)<<5)|((b)>>3)))

// ── Buttons: Fruit Jam GPIO0/4/5 ─────────────────────────────────────────────
#define SMP_BTN_COUNT 3
static const int  _smpBtnPin[SMP_BTN_COUNT] = { 0, 4, 5 };
static bool       _smpBtnLast[SMP_BTN_COUNT] = { HIGH, HIGH, HIGH };
static uint32_t   _smpBtnTime[SMP_BTN_COUNT] = { 0, 0, 0 };
#define SMP_DEBOUNCE_MS 200

static void smpBtnInit() {
  for (int i = 0; i < SMP_BTN_COUNT; i++) pinMode(_smpBtnPin[i], INPUT_PULLUP);
}

// true once per press (falling edge + debounce). idx 0..2 = Button1..3
static bool smpBtn(int idx) {
  bool s = digitalRead(_smpBtnPin[idx]);
  uint32_t now = millis();
  if (s == LOW && _smpBtnLast[idx] == HIGH
      && (now - _smpBtnTime[idx]) > SMP_DEBOUNCE_MS) {
    _smpBtnTime[idx] = now; _smpBtnLast[idx] = s; return true;
  }
  _smpBtnLast[idx] = s; return false;
}

// ── Launch mechanism: watchdog scratch registers ──────────────────────────────
// scratch[2] = magic, scratch[3] = demo id. Survive soft reset; we clear the
// magic immediately on demo boot so the NEXT reset returns to the menu.
#define SMP_MAGIC 0xDE110F00u   // "DEMO" launch magic

static void smpLaunchDemo(uint32_t id) {
  // CRITICAL: wait for all buttons to be released before rebooting.
  // Button1 is GPIO0, which doubles as the BOOT strap — rebooting while
  // it's still held drops the chip into the UF2 bootloader, not the demo.
  for (;;) {
    bool anyDown = false;
    for (int i = 0; i < SMP_BTN_COUNT; i++)
      if (digitalRead(_smpBtnPin[i]) == LOW) anyDown = true;
    if (!anyDown) break;
    delay(5);
  }
  delay(50);   // settle past contact bounce

  watchdog_hw->scratch[2] = SMP_MAGIC;
  watchdog_hw->scratch[3] = id;
  watchdog_reboot(0, 0, 10);   // soft reboot in 10ms
  for (;;) tight_loop_contents();
}

// returns demo id if booted via launcher, -1 if cold boot / reset (menu)
static int smpBootDemoId() {
  if (watchdog_hw->scratch[2] == SMP_MAGIC) {
    int id = (int)watchdog_hw->scratch[3];
    watchdog_hw->scratch[2] = 0;   // clear: next reset -> menu
    return id;
  }
  return -1;
}

// ── Shared memory arena ───────────────────────────────────────────────────────
// Big per-demo buffers overlay here. Only one demo runs per boot, so the
// arena is sized for the hungriest demo (rotozoom: 150K buf + 37K lens).
// Two overlay arenas (one demo per boot, so buffers share):
//
// SRAM arena — hot read/WRITE buffers. PSRAM write bandwidth (~7.4MB/s)
// cannot sustain per-frame full-buffer rewrites (rotozoom needs 9.2MB/s),
// and saturating the QMI from core1 destabilizes long runs. Sized for
// the largest customer (rotozoom pixel buffer, 150K).
#define SMP_SRAM_ARENA_SIZE (154 * 1024)
alignas(8) static uint8_t g_sramArena[SMP_SRAM_ARENA_SIZE];

// PSRAM arena — read-mostly tables only (plasma radial wave, rotozoom
// lens). Sequential/cached reads are PSRAM's strength (~31MB/s).
#define SMP_ARENA_SIZE (200 * 1024)
static uint8_t g_arena[SMP_ARENA_SIZE] PSRAM;

// ── PSRAM timing fix (call after display object construction) ────────────────
#include <psram.h>
static void smpPsramFix() {
  psram_reinit_timing();
  extern uint8_t __psram_start__;
  volatile uint8_t *x = &__psram_start__;
  *x ^= 0xff; *x ^= 0xff;
  asm volatile("" ::: "memory");
}
