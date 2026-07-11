// SPDX-FileCopyrightText: 2026 John Park with Claude Opus 4.8 for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// leds.h — 5-pixel NeoPixel status strip for the Fruit Jam Demoscene Sampler
//
// UI grammar (learned once, used everywhere):
//   count of lit pixels = "how much / which of N"
//   color               = "what kind / which mode"
//   a press always produces a strip response (settings persist; stateless
//   actions like randomize give a one-shot blink in the current color)
//
// Brightness is NOT used as a signal (hard to read against a bright screen).
// Updates happen only on state change, so the brief interrupt-masked
// NeoPixel write never perturbs audio or vsync.

#pragma once
#include <Adafruit_NeoPixel.h>

static Adafruit_NeoPixel _smpStrip(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// fixed, readable brightness — constant so it carries no meaning
#define LED_BRIGHT 40

// ── Per-demo signature colors (also used by the menu color-coding) ───────────
#define LED_C_STARFIELD  255,255,255   // white
#define LED_C_PLASMA     255,0,200     // magenta
#define LED_C_CHROME     0,220,255     // cyan
#define LED_C_VALLEY     0,255,40      // green
#define LED_C_ROTOZOOM   255,120,0     // orange
#define LED_C_JUGGLER    255,30,30     // red

static void ledInit() {
  _smpStrip.begin();
  _smpStrip.setBrightness(LED_BRIGHT);
  _smpStrip.clear();
  _smpStrip.show();
}

// light `n` of 5 pixels (0..5) in color (r,g,b), rest off.
// Physical layout: pixel 0 = BOTTOM, pixel 4 = TOP. We grow the bar from
// the top, so the lit pixels are the highest-indexed n.
static void ledBar(int n, uint8_t r, uint8_t g, uint8_t b) {
  if (n < 0) n = 0; if (n > (int)NUM_NEOPIXEL) n = NUM_NEOPIXEL;
  for (int i = 0; i < (int)NUM_NEOPIXEL; i++) {
    bool lit = (i >= (int)NUM_NEOPIXEL - n);   // top n pixels
    _smpStrip.setPixelColor(i, lit ? _smpStrip.Color(r, g, b) : 0);
  }
  _smpStrip.show();
}

// all five one color
static void ledAll(uint8_t r, uint8_t g, uint8_t b) {
  ledBar(NUM_NEOPIXEL, r, g, b);
}

// distinct color per pixel (used by plasma rainbow palette)
static void ledSpread() {
  // top (idx 4) -> bottom (idx 0)
  _smpStrip.setPixelColor(4, _smpStrip.Color(255, 0, 0));
  _smpStrip.setPixelColor(3, _smpStrip.Color(255, 200, 0));
  _smpStrip.setPixelColor(2, _smpStrip.Color(0, 255, 0));
  _smpStrip.setPixelColor(1, _smpStrip.Color(0, 120, 255));
  _smpStrip.setPixelColor(0, _smpStrip.Color(200, 0, 255));
  _smpStrip.show();
}

// one-shot blink (blocking ~120ms) — only for stateless action feedback,
// called when no animation/audio-critical timing is mid-flight
static void ledBlink(uint8_t r, uint8_t g, uint8_t b) {
  ledAll(r, g, b);
  delay(60);
  _smpStrip.clear();
  _smpStrip.show();
  delay(60);
}

// signature color lookup by demo id (1..6 in menu order)
static void ledDemoColor(int id) {
  switch (id) {
    case 1: ledAll(LED_C_STARFIELD); break;
    case 2: ledAll(LED_C_PLASMA);    break;
    case 3: ledAll(LED_C_CHROME);    break;
    case 4: ledAll(LED_C_VALLEY);    break;
    case 5: ledAll(LED_C_ROTOZOOM);  break;
    case 6: ledAll(LED_C_JUGGLER);   break;
    default: _smpStrip.clear(); _smpStrip.show(); break;
  }
}
