// SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*------------------------------------------------------------------------
  Gemma "Firewalker Lite" sneakers sketch.
  Uses the following Adafruit parts (X2 for two shoes):

  - Gemma 3V microcontroller (adafruit.com/product/1222 or 2470)
  - 150 mAh LiPoly battery (#1317) or larger
  - Medium vibration sensor switch (#2384)
  - 60/m NeoPixel RGB LED strip (#1138 or #1461)
  - LiPoly charger such as #1304 (only one is required, unless you want
    to charge both shoes at the same time)

  Needs Adafruit_NeoPixel library: github.com/adafruit/Adafruit_NeoPixel

  THIS CODE USES FEATURES SPECIFIC TO THE GEMMA MICROCONTROLLER BOARD AND
  WILL NOT COMPILE OR RUN ON MOST OTHERS.  OK on basic Trinket but NOT
  Pro Trinket nor anything else.  VERY specific to the Gemma!

  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing
  products from Adafruit!

  Written by Phil Burgess / Paint Your Dragon for Adafruit Industries.
  MIT license, all text above must be included in any redistribution.
  See 'COPYING' file for additional notes.
  ------------------------------------------------------------------------*/

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <avr/power.h>
#include <avr/sleep.h>

// CONFIGURABLE STUFF ------------------------------------------------------

#define NUM_LEDS      40 // Actual number of LEDs in NeoPixel strip
#define CIRCUMFERENCE 40 // Shoe circumference, in pixels, may be > NUM_LEDS
#define FPS           50 // Animation frames per second
#define LED_DATA_PIN   1 // NeoPixels are connected here
#define MOTION_PIN     0 // Vibration switch from here to GND
// CIRCUMFERENCE is distinct from NUM_LEDS to allow a gap (if desired) in
// LED strip around perimeter of shoe (might not want any on inside egde)
// so animation is spatially coherent (doesn't jump across gap, but moves
// as if pixels were in that space).  CIRCUMFERENCE can be equal or larger
// than NUM_LEDS, but not less.

// The following features are OPTIONAL and require ADDITIONAL COMPONENTS.
// Only ONE of these may be enabled due to limited pins on Gemma:

// BATTERY LEVEL graph on power-up: requires two resistors of same value,
// 10K or higher, connected to pin D2 -- one goes to Vout pin, other to GND.
//#define BATT_LVL_PIN  2 // Un-comment this line to enable battery level.
// Pin number cannot be changed, this is the only AREF pin on ATtiny85.
// Empty and full thresholds (millivolts) used for battery level display:
#define BATT_MIN_MV 3350 // Some headroom over battery cutoff near 2.9V
#define BATT_MAX_MV 4000 // And little below fresh-charged battery near 4.1V
// Graph works only on battery power; USB power will always show 100% full.

// POWER DOWN NeoPixels when idle to prolong battery: requires P-channel
// power MOSFET + 220 Ohm resistor, is a 'high side' switch to NeoPixel +V.
// DO NOT do this w/N-channel on GND side, could DESTROY strip!
//#define LED_PWR_PIN   2 // Un-comment this for NeoPixel power-down.
// Could be moved to other pin on Trinket to allow both options together.

// GLOBAL STUFF ------------------------------------------------------------

Adafruit_NeoPixel    strip(NUM_LEDS, LED_DATA_PIN);
void                 sleep(void); // Power-down function
extern const uint8_t gamma[];     // Table at the bottom of this code

// INTERMISSION explaining the animation code.  This works procedurally --
// using mathematical functions -- rather than moving discrete pixels left
// or right incrementally.  This sometimes confuses people because they go
// looking for some "setpixel(x+1, color)" type of code and can't find it.
// Also makes extensive use of fixed-point math, where discrete integer
// values are used to represent fractions (0.0 to 1.0) without relying on
// floating-point math, which just wouldn't even fit in Gemma's limited
// code space, RAM or speed.  The reason the animation's done this way is
// to produce smoother, more organic motion...when pixels are the smallest
// discrete unit, animation tends to have a stuttery, 1980s quality to it.
// We can do better!
// Picture the perimeter of the shoe in two different coordinate spaces:
// One is "pixel space," each pixel spans exactly one integer unit, from
// zero to N-1 when there are N pixels.  This is how NeoPixels are normally
// addressed.  Now, overlaid on this, imagine another coordinate space,
// spanning the same physical width (the perimeter of the shoe, or length
// of the LED strip), but this one has 256 discrete steps (8 bits)...finer
// resolution than the pixel steps...and we do most of the math using
// these units rather than pixel units.  It's then possible to move things
// by fractions of a pixel, but render each whole pixel by taking a sample
// at its approximate center in the alternate coordinate space.
// More explanation further in the code.
//
// |Pixel|Pixel|Pixel|    ...    |Pixel|Pixel|Pixel|<- end of strip
// |  0  |  1  |  2  |           |  3  |  4  | N-1 |
// |0...                  ...                ...255|<- fixed-point space
//
// So, inspired by the mothership in Close Encounters of the Third Kind,
// the animation in this sketch is a series of waves moving around the
// perimeter and interacting as they cross.  They're triangle waves,
// height proportional to LED brightness, determined by the time since
// motion was last detected.
//
//   <- /\       /\ -> <- /\          Pretend these are triangle waves
// ____/  \_____/  \_____/  \____  <- moving in 8-bit coordinate space.

struct {
  uint8_t center;    // Center point of wave in fixed-point space (0 - 255)
  int8_t  speed;     // Distance to move between frames (-128 - +127)
  uint8_t width;     // Width from peak to bottom of triangle wave (0 - 128)
  uint8_t hue;       // Current wave hue (color) see comments later
  uint8_t hueTarget; // Final hue we're aiming for
  uint8_t r, g, b;   // LED RGB color calculated from hue
} wave[] = {
  { 0,  3, 60 },     // Gemma can animate 3 of these on 40 LEDs at 50 FPS
  { 0, -5, 45 },     // More LEDs and/or more waves will need lower FPS
  { 0,  7, 30 }
};
// Note that the speeds of each wave are different prime numbers.  This
// avoids repetition as the waves move around the perimeter...if they were
// even numbers or multiples of each other, there'd be obvious repetition
// in the pattern of motion...beat frequencies.
#define N_WAVES (sizeof(wave) / sizeof(wave[0]))

// ONE-TIME INITIALIZATION -------------------------------------------------

void setup() {
#if defined(__AVR_ATtiny85__) && (F_CPU == 16000000L)
  clock_prescale_set(clock_div_1); // Allow 16 MHz Trinket too
#endif
#ifdef POWER_PIN
  pinMode(POWER_PIN, OUTPUT);
  digitalWrite(POWER_PIN, LOW);    // Power-on LED strip
#endif
  strip.begin();                   // Allocate NeoPixel buffer
  strip.clear();                   // Make sure strip is clear
  strip.show();                    // before measuring battery

#ifdef BATT_LVL_PIN
  // Battery monitoring code does some low-level Gemma-specific stuff...
  int      i, prev;
  uint8_t  count;
  uint16_t mV;

  pinMode(BATT_LVL_PIN, INPUT);    // No pullup

  // Select AREF (PB0) voltage reference + Bandgap (1.8V) input
  ADMUX  = _BV(REFS0) | _BV(MUX3) | _BV(MUX2);   // AREF, Bandgap input
  ADCSRA = _BV(ADEN)  |                          // Enable ADC
           _BV(ADPS2) | _BV(ADPS1) | _BV(ADPS0); // 1/128 prescale (125 KHz)
  delay(1); // Allow 1 ms settling time as per datasheet
  // Bandgap readings may still be settling.  Repeated readings are
  // taken until four concurrent readings stabilize within 5 mV.
  for(prev=9999, count=0; count<4; ) {
    for(ADCSRA |= _BV(ADSC); ADCSRA & _BV(ADSC); ); // Start, await ADC conv
    i  = ADC;                                       // Result
    mV = i ? (1100L * 1023 / i) : 0;                // Scale to millivolts
    if(abs((int)mV - prev) <= 5) count++;   // +1 stable reading
    else                         count = 0; // too much change, start over
    prev = mV;
  }
  ADCSRA = 0; // ADC off
  mV *= 2;    // Because 50% resistor voltage divider (to work w/3.3V MCU)

  uint8_t  lvl = (mV >= BATT_MAX_MV) ? NUM_LEDS : // Full (or nearly)
                 (mV <= BATT_MIN_MV) ?        1 : // Drained
                 1 + ((mV - BATT_MIN_MV) * NUM_LEDS + (NUM_LEDS / 2)) /
                 (BATT_MAX_MV - BATT_MIN_MV + 1); // # LEDs lit (1-NUM_LEDS)
  for(uint8_t i=0; i<lvl; i++) {                  // Each LED to batt level
    uint8_t g = (i * 5 + 2) / NUM_LEDS;           // Red to green
    strip.setPixelColor(i, 4-g, g, 0);
    strip.show();                                 // Animate a bit
    delay(250 / NUM_LEDS);
  }
  delay(1500);                                    // Hold last state a moment
  strip.clear();                                  // Then clear strip
  strip.show();
  randomSeed(mV);
#else
  randomSeed(analogRead(2));
#endif // BATT_LVL_PIN

  // Assign random starting colors to waves
  for(uint8_t w=0; w<N_WAVES; w++) {
    wave[w].hue = wave[w].hueTarget = 90 + random(90);
    wave[w].r = h2rgb(wave[w].hue - 30);
    wave[w].g = h2rgb(wave[w].hue);
    wave[w].b = h2rgb(wave[w].hue + 30);
  }

  // Configure motion pin for change detect & interrupt
  pinMode(MOTION_PIN, INPUT_PULLUP);
  PCMSK = _BV(MOTION_PIN); // Pin change interrupt mask
  GIFR  = 0xFF;            // Clear interrupt flags
  // Interrupt is not actually enabled yet, that's in sleep function...

  sleep(); // Sleep until motion is detected
}

// MAIN LOOP ---------------------------------------------------------------

uint32_t prevFrameTime = 0L;    // Used for animation timing
uint8_t  brightness    = 0;     // Current wave height
boolean  rampingUp     = false; // If true, brightness is increasing

void loop() {
  uint32_t t;
  uint16_t r, g, b, m, n;
  uint8_t  i, x, w, d1, d2, y;

  // Pause until suitable interval since prior frame has elapsed.
  // This is preferable to delay(), as the time to render each frame
  // can vary.
  while(((t = micros()) - prevFrameTime) < (1000000L / FPS));

  // Immediately show results calculated on -prior- pass,
  // so frame-to-frame timing is consistent.  Then render next frame.
  strip.show();
  prevFrameTime = t;     // Save frame update time for next pass

  if(GIFR & _BV(PCIF)) { // Pin change detected?
    rampingUp = true;    // Set brightness-ramping flag
    GIFR      = 0xFF;    // Clear interrupt masks
  }

  // Okay, here's where the animation starts to happen...

  // First, check the 'rampingUp' flag.  If set, this indicates that
  // the vibration switch was activated recently, and the LEDs should
  // increase in brightness.  If clear, the LEDs ramp down.
  if(rampingUp) {
    // But it's not just a straight shot that it ramps up.  This is a
    // low-pass filter...it makes the brightness value decelerate as it
    // approaches a target (200 in this case).  207 is used here because
    // integers round down on division and we'd never reach the target;
    // it's an ersatz ceil() function: ((199*7)+200+7)/8 = 200;
    brightness = ((brightness * 7) + 207) / 8;
    // Once max brightness is reached, switch off the rampingUp flag.
    if(brightness >= 200) rampingUp = false;
  } else {
    // If not ramping up, we're ramping down.  This too uses a low-pass
    // filter so it eases out, but with different constants so it's a
    // slower fade.  Also, no addition here because we want it rounding
    // down toward zero...
    if(!(brightness = (brightness * 15) / 16)) { // Hit zero?
      sleep(); // Turn off animation
      return;  // Start over at top of loop() on wake
    }
  }

  // Wave positions and colors are updated...
  for(w=0; w<N_WAVES; w++) {
    wave[w].center += wave[w].speed; // Move wave; wraps around ends, is OK!
    if(wave[w].hue == wave[w].hueTarget) { // Hue not currently changing?
      // There's a tiny random chance of picking a new hue...
      if(!random(FPS * 4)) {
        // Within 1/3 color wheel
        wave[w].hueTarget = random(wave[w].hue - 30, wave[w].hue + 30);
      }
    } else { // This wave's hue is currently shifting...
      if(wave[w].hue < wave[w].hueTarget) wave[w].hue++; // Move up or
      else                                wave[w].hue--; // down as needed
      if(wave[w].hue == wave[w].hueTarget) { // Reached destination?
        wave[w].hue = 90 + wave[w].hue % 90; // Clamp to 90-180 range
        wave[w].hueTarget = wave[w].hue;     // Copy to target
      }
      wave[w].r = h2rgb(wave[w].hue - 30);
      wave[w].g = h2rgb(wave[w].hue);
      wave[w].b = h2rgb(wave[w].hue + 30);
    }
  }

  // Now render the LED strip using the current brightness & wave states

  for(i=0; i<NUM_LEDS; i++) { // Each LED in strip is visited just once...

    // Transform 'i' (LED number in pixel space) to the equivalent point
    // in 8-bit fixed-point space (0-255).  "* 256" because that would be
    // the start of the (N+1)th pixel.  "+ 127" to get pixel center.
    x = (i * 256 + 127) / CIRCUMFERENCE;

    r = g = b = 0; // LED assumed off, but wave colors will add up here

    for(w=0; w<N_WAVES; w++) { // For each item in wave[] array...

      // Calculate distance from pixel center to wave center point,
      // using both signed and unsigned 8-bit integers...
      d1 = abs((int8_t)x  - (int8_t)wave[w].center);
      d2 = abs((uint8_t)x - (uint8_t)wave[w].center);
      // Then take the lesser of the two, resulting in a distance (0-128)
      // that 'wraps around' the ends of the strip as necessary...it's a
      // contiguous ring, and waves can move smoothly across the gap.
      if(d2 < d1) d1 = d2;       // d1 is pixel-to-wave-center distance
      if(d1 < wave[w].width) {   // Is distance within wave's influence?
        d2 = wave[w].width - d1; // d2 is opposite; distance to wave's end

        // d2 distance, relative to wave width, is then proportional to the
        // wave's brightness at this pixel (basic linear y=mx+b stuff).
        // Normally this would require a fraction -- floating-point math --
        // but by reordering the operations we can get the same result with
        // integers -- fixed-point math -- that's why brightness is cast
        // here to a 16-bit type; the interim result of the multiplication
        // is a big integer that's then divided by wave width (back to an
        // 8-bit value) to yield the pixel's brightness.  This massive wall
        // of comments is basically to explain that fixed-point math is
        // faster and less resource-intensive on processors with limited
        // capabilities.  Topic for another Adafruit Learning System guide?
        y = (uint16_t)brightness * d2 / wave[w].width; // 0 to 200

        // y is a brightness scale value -- proportional to, but not
        // exactly equal to, the resulting RGB value.  Values from 0-127
        // represent a color ramp from black to the wave's assigned RGB
        // color.  Values from 128-255 ramp from the RGB color to white.
        // It's by design that y only goes to 200...white peaks then occur
        // only when certain waves overlap.
        if(y < 128) { // Fade black to RGB color
          // In HSV colorspace, this would be tweaking 'value'
          n  = (uint16_t)y * 2 + 1;  // 1-256
          r += (wave[w].r * n) >> 8; // More fixed-point math
          g += (wave[w].g * n) >> 8; // Wave color is scaled by 'n'
          b += (wave[w].b * n) >> 8; // >>8 is equiv to /256
        } else {      // Fade RGB color to white
          // In HSV colorspace, this would be tweaking 'saturation'
          n  = (uint16_t)(y - 128) * 2; // 0-255 affects white level
          m  = 256 * n;
          n  = 256 - n;                 // 1-256 affects RGB level
          r += (m + wave[w].r * n) >> 8;
          g += (m + wave[w].g * n) >> 8;
          b += (m + wave[w].b * n) >> 8;
        }
      }
    }

    // r,g,b are 16-bit types that accumulate brightness from all waves
    // that affect this pixel; may exceed 255.  Now clip to 0-255 range:
    if(r > 255) r = 255;
    if(g > 255) g = 255;
    if(b > 255) b = 255;
    // Store resulting RGB value and we're done with this pixel!
    strip.setPixelColor(i, r, g, b);
  }

  // Once rendering is complete, a second pass is made through pixel data
  // applying gamma correction, for more perceptually linear colors.
  // https://learn.adafruit.com/led-tricks-gamma-correction
  uint8_t *pixels = strip.getPixels(); // Pointer to LED strip buffer
  for(i=0; i<NUM_LEDS*3; i++) pixels[i] = pgm_read_byte(&gamma[pixels[i]]);
}

// SLEEP/WAKE CODE is very Gemma-specific  ---------------------------------

void sleep() {
  strip.clear();                       // Clear pixel buffer
#ifdef POWER_PIN
  pinMode(LED_DATA_PIN, INPUT);        // Avoid parasitic power to strip
  digitalWrite(POWER_PIN, HIGH);       // Cut power to pixels
#else
  strip.show();                        // Turn off LEDs
#endif // POWER_PIN
  power_all_disable();                 // Peripherals ALL OFF
  GIMSK = _BV(PCIE);                   // Allow pin-change interrupt only
  set_sleep_mode(SLEEP_MODE_PWR_DOWN); // Deepest sleep mode
  sleep_enable();
  interrupts();                        // Needed for pin-change wake
  sleep_mode();                        // Power down (stops here)
  //                                   ** RESUMES HERE ON WAKE **
  GIMSK = 0;                           // Clear global interrupt mask
  // Pin change when awake is done by polling GIFR register, not interrupt
#ifdef POWER_PIN
  digitalWrite(POWER_PIN, LOW);        // Power-up LEDs
  pinMode(LED_DATA_PIN, OUTPUT);
  strip.show();                        // Clear any startup garbage
#endif
  power_timer0_enable();               // Used by micros()
  // Remaining peripherals (ADC, Timer1, etc) are NOT re-enabled, as they're
  // not used elsewhere in the sketch.  If adding features, you might need
  // to re-enable some/all peripherals here.
  rampingUp = true;
}

EMPTY_INTERRUPT(PCINT0_vect); // Pin change (does nothing, but required)

// COLOR-HANDLING CODE -----------------------------------------------------

// A full HSV-to-RGB function wasn't required by sketch, just needed limited
// hue-to-RGB.  There are 90 distinct hues (0-89) around color wheel (to
// allow 4-bit table entries).  This function gets called three times (for
// R,G,B, with different offsets relative to hue) to produce a fully-
// saturated color.  Was a little more compact than a full HSV function.

static const uint8_t PROGMEM hueTable[45] = {
 0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xED,0xCB,0xA9,0x87,0x65,0x43,0x21,
 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
 0x12,0x34,0x56,0x78,0x9A,0xBC,0xDE,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF
};

uint8_t h2rgb(uint8_t hue) {
  hue %= 90;
  uint8_t h = pgm_read_byte(&hueTable[hue >> 1]);
  return ((hue & 1) ? (h & 15) : (h >> 4)) * 17;
}

// Gamma-correction table (see earlier comments).  It's big and ugly
// and would interrupt trying to read the code, so I put it down here.
const uint8_t gamma[] PROGMEM = {
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
    5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
   10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
   17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
   25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
   37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
   51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
   69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
   90, 92, 93, 95, 96, 98, 99,101,102,104,105,107,109,110,112,114,
  115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,
  144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,
  177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,
  215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255 };
