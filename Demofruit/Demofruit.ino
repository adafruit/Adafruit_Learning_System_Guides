// SPDX-FileCopyrightText: 2026 John Park with Claude Opus 4.8 for Adafruit Industries
//
// SPDX-License-Identifier: MIT
//
// Demofruit Fruit Jam Demoscene demo
// music by kqvc
// ═══ DEMOFRUIT — FRUIT JAM DEMOSCENE SAMPLER ═══
// Six demos, one UF2. Boot menu selects; watchdog-scratch reboot launches
// each demo with its ideal display configuration; RESET returns to menu.
//
//   STARFIELD      — warp field + bouncing chrome text   (DVHSTX16)
//   PLASMA         — palette plasma, software palette    (DVHSTX16)
//   CHROME SPHERE  — dual-core raytracer                 (DVHSTX16)
//   VALLEY RUN     — wireframe trench + shaded ship      (DVHSTX16)
//   ROTOZOOM       — texture spin/zoom + lens            (DVHSTX16, dual-core)
//   THE JUGGLER    — Eric Graham 1987, PSRAM playback    (DVHSTX16, dual-core)
//
// REQUIREMENTS: Board = Adafruit Fruit Jam RP2350, CPU Speed = 150MHz.

#include <Arduino.h>
#include <new>
#include <Adafruit_dvhstx.h>
#include <Adafruit_GFX.h>
#include <Fonts/FreeSansBold24pt7b.h>
#include <pico/multicore.h>
#include <hardware/watchdog.h>
#include <math.h>

#include "common.h"
#include "audio.h"
#include "leds.h"

// ── Songs: song_0.h = menu, song_1..6.h = demos in menu order ────────────────
// Each is a standard mod2header output (MOD_DATA), wrapped in a namespace.
namespace song0 {
#include "song_0.h"
}
namespace song1 {
#include "song_1.h"
}
namespace song2 {
#include "song_2.h"
}
namespace song3 {
#include "song_3.h"
}
namespace song4 {
#include "song_4.h"
}
namespace song5 {
#include "song_5.h"
}
namespace song6 {
#include "song_6.h"
}
struct SmpSong { const unsigned char *data; unsigned size; };
static const SmpSong g_songs[7] = {
  { song0::MOD_DATA, sizeof(song0::MOD_DATA) },   // menu
  { song1::MOD_DATA, sizeof(song1::MOD_DATA) },   // starfield
  { song2::MOD_DATA, sizeof(song2::MOD_DATA) },   // plasma
  { song3::MOD_DATA, sizeof(song3::MOD_DATA) },   // chrome sphere
  { song4::MOD_DATA, sizeof(song4::MOD_DATA) },   // valley run
  { song5::MOD_DATA, sizeof(song5::MOD_DATA) },   // rotozoom
  { song6::MOD_DATA, sizeof(song6::MOD_DATA) },   // the juggler
};
#include "texture.h"     // rotozoom bitmap (global: plain data)

// ── Demo modules, each in its own namespace ──────────────────────────────────
namespace sf {
  enum RampPhase { CRUISE, RAMP, WARP, SNAP, RECOVER };
  #include "starfield_impl.h"
}
namespace pl {
#include "plasma_impl.h"
}
namespace rt {
#include "raytracer_impl.h"
}
namespace vy {
#include "valley_impl.h"
}
namespace rz {
#include "rotozoom_impl.h"
}
namespace jg {
#include "juggler_impl.h"
}

#include "launcher.h"

// ── Displays ──────────────────────────────────────────────────────────────────
// DVHSTX16 as a GLOBAL — identical to every proven standalone sketch
// (the library does clock setup tied to static construction). One display,
// one begin() per boot. All demos render through it; plasma uses a
// software palette LUT instead of DVHSTX8 hardware palette (runtime
// display construction proved unreliable).
DVHSTX16 display16(ADAFRUIT_FRUIT_JAM_CFG, DVHSTX_RESOLUTION_320x240,
                   true /* double_buffered */);

static void dispFail() {
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) {
    Serial.println("FATAL: display.begin() failed");
    digitalWrite(LED_BUILTIN, HIGH); delay(150);
    digitalWrite(LED_BUILTIN, LOW);  delay(850);
  }
}

static DVHSTX16 *use16() {
  DVHSTX16 *d = &display16;
  Serial.println("display16.begin()..."); Serial.flush();
  if (!d->begin()) dispFail();
  Serial.println("display16 OK"); Serial.flush();
  smpPsramFix();
  return d;
}

// ── Boot dispatch ─────────────────────────────────────────────────────────────
void setup() {
  smpBtnInit();
  ledInit();
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && (millis() - t0) < 2000) delay(10);

  int id = smpBootDemoId();   // -1 = menu; clears scratch so reset -> menu
  Serial.printf("boot: demo id %d\n", id); Serial.flush();

  switch (id) {
    case 0: {  // STARFIELD
      DVHSTX16 *d = use16();
      smpAudioInit(g_songs[1].data, g_songs[1].size);
      ledAll(LED_C_STARFIELD);   // signature color carried from menu
      Serial.println("demo: starfield");
      sf::starfieldRun(*d);
    }
    case 1: {  // PLASMA — software palette through the shared display
      DVHSTX16 *d = use16();
      smpAudioInit(g_songs[2].data, g_songs[2].size);
      ledAll(LED_C_PLASMA);   // signature color carried from menu
      Serial.println("demo: plasma");
      pl::plasmaInit();
      for (;;) { smpAudioPump(); pl::plasmaTick(*d); }
    }
    case 2: {  // CHROME SPHERE
      DVHSTX16 *d = use16();
      smpAudioInit(g_songs[3].data, g_songs[3].size);
      ledAll(LED_C_CHROME);   // signature color carried from menu
      Serial.println("demo: raytracer");
      rt::rtInit(*d);
      multicore_launch_core1(rt::rtCore1Entry);
      for (;;) { smpAudioPump(); rt::rtCore0Loop(*d); }
    }
    case 3: {  // VALLEY RUN
      DVHSTX16 *d = use16();
      smpAudioInit(g_songs[4].data, g_songs[4].size);
      ledAll(LED_C_VALLEY);   // signature color carried from menu
      Serial.println("demo: valley");
      vy::valleyInit();
      for (;;) { smpAudioPump(); vy::valleyTick(*d); }
    }
    case 4: {  // ROTOZOOM
      DVHSTX16 *d = use16();
      smpAudioInit(g_songs[5].data, g_songs[5].size);
      ledAll(LED_C_ROTOZOOM);   // signature color carried from menu
      Serial.println("demo: rotozoom");
      rz::rzInit();
      multicore_launch_core1(rz::rzCore1Entry);
      for (;;) { smpAudioPump(); rz::rzCore0Loop(*d); }
    }
    case 5: {  // THE JUGGLER
      DVHSTX16 *d = use16();
      smpAudioInit(g_songs[6].data, g_songs[6].size);
      ledAll(LED_C_JUGGLER);   // signature color carried from menu
      Serial.println("demo: juggler");
      jg::jugglerRun(*d);
    }
    default: { // MENU
      DVHSTX16 *d = use16();
      smpAudioInit(g_songs[0].data, g_songs[0].size);
      Serial.println("menu"); Serial.flush();
      menuRun(*d);
    }
  }
}

void loop() { /* unreachable — every path above loops forever */ }
