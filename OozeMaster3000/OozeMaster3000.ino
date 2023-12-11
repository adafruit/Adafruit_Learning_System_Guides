// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// OOZE MASTER 3000: NeoPixel simulated liquid physics. Up to 7 NeoPixel
// strands dribble light, while an 8th strand "catches the drips."
// Designed for the Adafruit Feather M0 or M4 with matching version of
// NeoPXL8 FeatherWing, or for RP2040 boards including SCORPIO. This can be
// adapted for other M0, M4, RP2040 or ESP32-S3 boards but you will need to
// do your own "pin sudoku" & level shifting (e.g. NeoPXL8 Friend breakout).
// See here: https://learn.adafruit.com/adafruit-neopxl8-featherwing-and-library
// Requires Adafruit_NeoPixel, Adafruit_NeoPXL8 and Adafruit_ZeroDMA libraries.

#include <Adafruit_NeoPXL8.h>

#define PIXEL_PITCH (1.0 / 150.0) // 150 pixels/m
#define ICE_BRIGHTNESS 0          // Icycle effect Brightness (0 to <100%)
#define COLOR_ORDER NEO_GRB       // NeoPixel color format (see Adafruit_NeoPixel)

#define GAMMA   2.6   // For linear brightness correction
#define G_CONST 9.806 // Standard acceleration due to gravity
// While the above G_CONST is correct for "real time" drips, you can dial it
// back for a more theatric effect / to slow the drips like they've still got
// a syrupy "drool string" attached (try much lower values like 2.0 to 3.0).

// NeoPXL8 pin numbers
#if defined(ARDUINO_ADAFRUIT_FEATHER_RP2040_SCORPIO)
#define USE_HDR // RP2040 has enough "oomph" for HDR color!
int8_t pins[8] = { 16, 17, 18, 19, 20, 21, 22, 23 };
#else
// These are default connections on NeoPXL8 M0 FeatherWing:
int8_t pins[8] = { PIN_SERIAL1_RX, PIN_SERIAL1_TX, MISO, 13, 5, SDA, A4, A3 };
// If using an M4 Feather & NeoPXL8 FeatherWing, use these values instead:
//int8_t pins[8] = { 13, 12, 11, 10, SCK, 5, 9, 6 };
#endif

typedef enum {
  MODE_IDLE,
  MODE_OOZING,
  MODE_DRIBBLING_1,
  MODE_DRIBBLING_2,
  MODE_DRIPPING
} dropState;

// A color palette allows one to "theme" a project. By default there's just
// one color, and all drips use only that. Setting up a color list, and then
// declaring a range of indices in the drip[] table later, allows some
// randomization while still keeping appearance within a predictable range.
// Each drip could be its own fixed color, or each could be randomly picked
// from a set of colors. Explained further in Adafruit Learning System guide.
// Q: WHY NOT JUST PICK RANDOM RGB COLORS?
// Because that would pick a lot of ugly or too-dark RGB combinations.
// WHY NOT RANDOM FULL-BRIGHTNESS HUES FROM THE ColorHSV() FUNCTION?
// Two reasons: First, to apply a consistent color theme to a project;
// Halloween, Christmas, fire, water, etc. Second, because NeoPixels
// have been around for over a decade and it's time we mature past the
// Lisa Frank stage of all-rainbows-all-the-time and consider matters of
// taste and restraint. If you WANT all rainbows, that's still entirely
// possile just by setting up a palette of bright colors!
uint8_t palette[][3] = {
  { 0, 255, 0 }, // Bright green ectoplasm
};
#define NUM_COLORS (sizeof palette / sizeof palette[0])
// Note that color randomization does not pair well with the ICE_BRIGHTNESS
// effect; you'll probably want to pick one or the other: random colors
// (from palette) and no icicles, or fixed color (per strand or overall)
// with ice. Otherwise the color jump of the icicle looks bad and wrong.

// Optional "Carrie mode" -- if a pin is defined here, and a switch or button
// added between this pin and ground -- when active, each new drip is drawn
// using the last color in the palette table (and slowly returns to original
// color scheme when released). i.e. there might normally be pleasant wintry
// colors in the palette, then plop pure red at the end of the list and watch
// the fun unfold!
//#define CARRIE_PIN    A2
// If you could use an extra ground pin for that, define that here; this
// is a signal ground only, for the switch, NOT for powering anything.
//#define CARRIE_GROUND A3

struct {
  uint16_t  length;            // Length of NeoPixel strip IN PIXELS
  uint16_t  dribblePixel;      // Index of pixel where dribble pauses before drop (0 to length-1)
  float     height;            // Height IN METERS of dribblePixel above ground
  uint16_t  palette_min;       // Lower color palette index for this strip
  uint16_t  palette_max;       // Upper color palette index for this strip
  dropState mode;              // One of the above states (MODE_IDLE, etc.)
  uint32_t  eventStartUsec;    // Starting time of current event
  uint32_t  eventDurationUsec; // Duration of current event, in microseconds
  float     eventDurationReal; // Duration of current event, in seconds (float)
  uint32_t  splatStartUsec;    // Starting time of most recent "splat"
  uint32_t  splatDurationUsec; // Fade duration of splat
  float     pos;               // Position of drip on prior frame
  uint8_t   color[3];          // RGB color (randomly picked from from palette[])
  uint8_t   splatColor[3];     // RGB color of "splat" (may be from prior drip)
} drip[] = {
  // THIS TABLE CONTAINS INFO FOR UP TO 8 NEOPIXEL DRIPS
  { 16,  7, 0.157, 0, 0 }, // NeoPXL8 output 0: 16 pixels long, drip pauses at index 7, 0.157 meters above ground, use palette colors 0-0
  { 19,  6, 0.174, 0, 0 }, // NeoPXL8 output 1: 19 pixels long, pause at index 6, 0.174 meters up
  { 18,  5, 0.195, 0, 0 }, // NeoPXL8 output 2: etc.
  { 17,  6, 0.16 , 0, 0 }, // NeoPXL8 output 3
  { 16,  1, 0.21 , 0, 0 }, // NeoPXL8 output 4
  { 16,  1, 0.21 , 0, 0 }, // NeoPXL8 output 5
  { 21, 10, 0.143, 0, 0 }, // NeoPXL8 output 6
  // NeoPXL8 output 7 is normally reserved for ground splats
  // You CAN add an eighth drip here, but then will not get splats
};
// There might be situations where the "splat" pixels are more easily
// installed using a longer strand of fixed-spacing "pebble style" NeoPixels
// rather than soldering up separate pixels for each one...and then lighting
// up only specific pixels along that strand for splats, leaving the others
// un-lit. This table holds indices for seven pixels along that strand
// corresponding to the seven splats. Could also be used to reverse the
// order of splat indices, etc.
uint8_t splatmap[] = { 0, 1, 2, 3, 4, 5, 6 };

#ifdef USE_HDR
Adafruit_NeoPXL8HDR *pixels = NULL;
#else
Adafruit_NeoPXL8    *pixels = NULL;
#endif
#define N_DRIPS      (sizeof drip / sizeof drip[0])
int                  longestStrand = (N_DRIPS < 8) ? N_DRIPS : 0;

void setup() {
  Serial.begin(9600);
  randomSeed(analogRead(A0) + analogRead(A1));

#ifdef CARRIE_PIN
  pinMode(CARRIE_PIN, INPUT_PULLUP);
#endif
#ifdef CARRIE_GROUND
  pinMode(CARRIE_GROUND, OUTPUT);
  digitalWrite(CARRIE_GROUND, LOW);
#endif

  for(int i=0; i<N_DRIPS; i++) {
    drip[i].mode              = MODE_IDLE; // Start all drips in idle mode
    drip[i].eventStartUsec    = 0;
    drip[i].eventDurationUsec = random(500000, 2500000); // Initial idle 0.5-2.5 sec
    drip[i].eventDurationReal = (float)drip[i].eventDurationUsec / 1000000.0;
    drip[i].splatStartUsec    = 0;
    drip[i].splatDurationUsec = 0;
    if(drip[i].length    > longestStrand) longestStrand = drip[i].length;
    if((splatmap[i] + 1) > longestStrand) longestStrand = splatmap[i] + 1;
    // Randomize initial color:
    memcpy(drip[i].color, palette[random(drip[i].palette_min, drip[i].palette_max + 1)], sizeof palette[0]);
    memcpy(drip[i].splatColor, drip[i].color, sizeof palette[0]);
#ifdef CARRIE_PIN
    // If "Carrie" switch is on, override above color with last palette entry
    if (!digitalRead(CARRIE_PIN)) {
      memcpy(drip[i].color, palette[NUM_COLORS - 1], sizeof palette[0]);
    }
#endif
  }

#ifdef USE_HDR
  pixels = new Adafruit_NeoPXL8HDR(longestStrand, pins, COLOR_ORDER);
  if (!pixels->begin(true, 4, true)) {
    // HDR requires inordinate RAM! Blink onboard LED if there's trouble:
    pinMode(LED_BUILTIN, OUTPUT);
    for (;;) digitalWrite(LED_BUILTIN, (millis() / 500) & 1);
  }
  pixels->setBrightness(65535, GAMMA); // NeoPXL8HDR handles gamma correction
#else
  pixels = new Adafruit_NeoPXL8(longestStrand, pins, COLOR_ORDER);
  pixels->begin();
#endif
}

void loop() {
  uint32_t t = micros(); // Current time, in microseconds

  float x = 0.0; // multipurpose interim result
  pixels->clear();

  for(int i=0; i<N_DRIPS; i++) {
    uint32_t dtUsec = t - drip[i].eventStartUsec; // Elapsed time, in microseconds, since start of current event
    float    dtReal = (float)dtUsec / 1000000.0;  // Elapsed time, in seconds

    // Handle transitions between drip states (oozing, dribbling, dripping, etc.)
    if(dtUsec >= drip[i].eventDurationUsec) {              // Are we past end of current event?
      drip[i].eventStartUsec += drip[i].eventDurationUsec; // Yes, next event starts here
      dtUsec                 -= drip[i].eventDurationUsec; // We're already this far into next event
      dtReal                  = (float)dtUsec / 1000000.0;
      switch(drip[i].mode) { // Current mode...about to switch to next mode...
        case MODE_IDLE:
          drip[i].mode              = MODE_OOZING; // Idle to oozing transition
          drip[i].eventDurationUsec = random(800000, 1200000); // 0.8 to 1.2 sec ooze
          drip[i].eventDurationReal = (float)drip[i].eventDurationUsec / 1000000.0;
          // Randomize next drip color from palette settings:
          memcpy(drip[i].color, palette[random(drip[i].palette_min, drip[i].palette_max + 1)], sizeof palette[0]);
#ifdef CARRIE_PIN
          // If "Carrie" switch is on, override color with last palette entry
          if (!digitalRead(CARRIE_PIN)) {
            memcpy(drip[i].color, palette[NUM_COLORS - 1], sizeof palette[0]);
          }
#endif
          break;
        case MODE_OOZING:
          if(drip[i].dribblePixel) { // If dribblePixel is nonzero...
            drip[i].mode              = MODE_DRIBBLING_1; // Oozing to dribbling transition
            drip[i].pos               = (float)drip[i].dribblePixel;
            drip[i].eventDurationUsec = 250000 + drip[i].dribblePixel * random(30000, 40000);
            drip[i].eventDurationReal = (float)drip[i].eventDurationUsec / 1000000.0;
          } else { // No dribblePixel...
            drip[i].pos               = (float)drip[i].dribblePixel; // Oozing to dripping transition
            drip[i].mode              = MODE_DRIPPING;
            drip[i].eventDurationReal = sqrt(drip[i].height * 2.0 / G_CONST); // SCIENCE
            drip[i].eventDurationUsec = (uint32_t)(drip[i].eventDurationReal * 1000000.0);
          }
          break;
        case MODE_DRIBBLING_1:
          drip[i].mode              = MODE_DRIBBLING_2; // Dripping 1st half to 2nd half transition
          drip[i].eventDurationUsec = drip[i].eventDurationUsec * 3 / 2; // Second half is 1/3 slower
          drip[i].eventDurationReal = (float)drip[i].eventDurationUsec / 1000000.0;
          break;
        case MODE_DRIBBLING_2:
          drip[i].mode              = MODE_DRIPPING; // Dribbling 2nd half to dripping transition
          drip[i].pos               = (float)drip[i].dribblePixel;
          drip[i].eventDurationReal = sqrt(drip[i].height * 2.0 / G_CONST); // SCIENCE
          drip[i].eventDurationUsec = (uint32_t)(drip[i].eventDurationReal * 1000000.0);
          break;
        case MODE_DRIPPING:
          drip[i].mode              = MODE_IDLE; // Dripping to idle transition
          drip[i].eventDurationUsec = random(500000, 1200000); // Idle for 0.5 to 1.2 seconds
          drip[i].eventDurationReal = (float)drip[i].eventDurationUsec / 1000000.0;
          drip[i].splatStartUsec    = drip[i].eventStartUsec; // Splat starts now!
          drip[i].splatDurationUsec = random(900000, 1100000);
          memcpy(drip[i].splatColor, drip[i].color, sizeof palette[0]); // Save color for splat
          break;
      }
    }

    // Render drip state to NeoPixels...
#if ICE_BRIGHTNESS > 0
      // Draw icycles if ICE_BRIGHTNESS is set
      x = (float)ICE_BRIGHTNESS * 0.01;
      for(int d=0; d<=drip[i].dribblePixel; d++) {
        set(i, i, d, x);
      }
#endif
    switch(drip[i].mode) {
      case MODE_IDLE:
        // Do nothing
        break;
      case MODE_OOZING:
        x = dtReal / drip[i].eventDurationReal; // 0.0 to 1.0 over ooze interval
        x = sqrt(x); // Perceived area increases linearly
#if ICE_BRIGHTNESS > 0
        x = ((float)ICE_BRIGHTNESS * 0.01) +
            x * (float)(100 - ICE_BRIGHTNESS) * 0.01;
#endif
        set(i, i, 0, x);
        break;
      case MODE_DRIBBLING_1:
        // Point b moves from first to second pixel over event time
        x = dtReal / drip[i].eventDurationReal; // 0.0 to 1.0 during move
        x = 3 * x * x - 2 * x * x * x; // Easing function: 3*x^2-2*x^3 0.0 to 1.0
        dripDraw(i, 0.0, x * drip[i].dribblePixel, false);
        break;
      case MODE_DRIBBLING_2:
        // Point a moves from first to second pixel over event time
        x = dtReal / drip[i].eventDurationReal; // 0.0 to 1.0 during move
        x = 3 * x * x - 2 * x * x * x; // Easing function: 3*x^2-2*x^3 0.0 to 1.0
        dripDraw(i, x * drip[i].dribblePixel, drip[i].dribblePixel, false);
        break;
      case MODE_DRIPPING:
        x = 0.5 * G_CONST * dtReal * dtReal; // Position in meters
        x = drip[i].dribblePixel + x / PIXEL_PITCH; // Position in pixels
        dripDraw(i, drip[i].pos, x, true);
        drip[i].pos = x;
        break;
    }

    if(N_DRIPS < 8) { // Do splats unless there's an 8th drip defined
      dtUsec = t - drip[i].splatStartUsec; // Elapsed time, in microseconds, since start of splat
      if(dtUsec < drip[i].splatDurationUsec) {
        x = 1.0 - sqrt((float)dtUsec / (float)drip[i].splatDurationUsec);
        set(7, i, splatmap[i], x);
      }
    }
  }

  pixels->show();
}

// This "draws" a drip in the NeoPixel buffer...zero to peak brightness
// at center and back to zero. Peak brightness diminishes with length,
// and drawn dimmer as pixels approach strand length.
void dripDraw(uint8_t dNum, float a, float b, bool fade) {
  if(a > b) { // Sort a,b inputs if needed so a<=b
    float t = a;
    a = b;
    b = t;
  }
  // Find range of pixels to draw. If first pixel is off end of strand,
  // nothing to draw. If last pixel is off end of strand, clip to strand length.
  int firstPixel = (int)a;
  if(firstPixel >= drip[dNum].length) return;
  int lastPixel  = (int)b + 1;
  if(lastPixel >= drip[dNum].length) lastPixel = drip[dNum].length - 1;

  float center   = (a + b) * 0.5;    // Midpoint of a-to-b
  float range    = center - a + 1.0; // Distance from center to a, plus 1 pixel
  for(int i=firstPixel; i<= lastPixel; i++) {
    float x = fabs(center - (float)i); // Pixel distance from center point
    if(x < range) {                    // Inside drip
      x = (range - x) / range;         // 0.0 (edge) to 1.0 (center)
      if(fade) {
        int dLen   = drip[dNum].length - drip[dNum].dribblePixel; // Length of drip
        if(dLen > 0) { // Scale x by 1.0 at top to 1/3 at bottom of drip
          int dPixel = i - drip[dNum].dribblePixel; // Pixel position along drip
          x *= 1.0 - ((float)dPixel / (float)dLen * 0.66);
        }
      }
    } else {
      x = 0.0;
    }
#if ICE_BRIGHTNESS > 0
    // Upper pixels may be partially lit for an icycle effect
    if(i <= drip[dNum].dribblePixel) {
      // Math because preprocessor doesn't allow float constant in #if.
      // Optimizer will reduce the math to float constants, it's fine.
      x = ((float)ICE_BRIGHTNESS * 0.01) +
          x * (float)(100 - ICE_BRIGHTNESS) * 0.01;
    }
#endif
    set(dNum, dNum, i, x);
  }
}

// Set one pixel to a given brightness level (0.0 to 1.0).
// Strand # and drip # are BOTH passed in because "splats" are always
// on strand 7 but colors come from drip indices.
void set(uint8_t strand, uint8_t d, uint8_t pixel, float brightness) {
#if !defined(USE_HDR) // NeoPXL8HDR does its own gamma correction, else...
  brightness = pow(brightness, GAMMA);
#endif
  if ((strand < 7) || (N_DRIPS >= 8)) {
    pixels->setPixelColor(pixel + strand * longestStrand,
      (int)((float)drip[d].color[0] * brightness + 0.5),
      (int)((float)drip[d].color[1] * brightness + 0.5),
      (int)((float)drip[d].color[2] * brightness + 0.5));
  } else {
    pixels->setPixelColor(pixel + strand * longestStrand,
      (int)((float)drip[d].splatColor[0] * brightness + 0.5),
      (int)((float)drip[d].splatColor[1] * brightness + 0.5),
      (int)((float)drip[d].splatColor[2] * brightness + 0.5));
  }
}

// NeoPXL8HDR requires some background processing in a second thread.
// See NeoPXL8 library examples (NeoPXL8HDR/strandtest) for explanation.
// Currently this sketch only enables HDR if using Feather SCORPIO,
// but it could be useful for other RP2040s and for ESP32S3too.
#ifdef USE_HDR

#if defined(ARDUINO_ARCH_RP2040)

void loop1() {
  if (pixels) pixels->refresh();
}

void setup1() {
}

#elif defined(CONFIG_IDF_TARGET_ESP32S3)

void loop0(void *param) {
  for(;;) {
    yield();
    if (pixels) pixels->refresh();
  }
}

#else // SAMD

#include "Adafruit_ZeroTimer.h"

Adafruit_ZeroTimer zerotimer = Adafruit_ZeroTimer(3);

void TC3_Handler() {
  Adafruit_ZeroTimer::timerHandler(3);
}

void timerCallback(void) {
  if (pixels) pixels->refresh();
}

#endif // end SAMD

#endif // end USE_HDR
