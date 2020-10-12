// 'Firewalker' LED sneakers sketch for Adafruit NeoPixels by Phillip Burgess

#include <Adafruit_NeoPixel.h>

const uint8_t gamma1[] PROGMEM = { // Gamma correction table for LED brightness
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

// LEDs go around the full perimeter of the shoe sole, but the step animation
// is mirrored on both the inside and outside faces, while the strip doesn't
// necessarily start and end at the heel or toe.  These constants help configure
// the strip and shoe sizes, and the positions of the front- and rear-most LEDs.
// Becky's shoes: 39 LEDs total, 20 LEDs long, LED #5 at back.
// Phil's shoes: 43 LEDs total, 22 LEDs long, LED #6 at back.
#define N_LEDS        39 // TOTAL number of LEDs in strip
#define SHOE_LEN_LEDS 20 // Number of LEDs down ONE SIDE of shoe
#define SHOE_LED_BACK  5 // Index of REAR-MOST LED on shoe
#define STEP_PIN      A2 // Analog input for footstep
#define LED_PIN       A0 // NeoPixel strip is connected here
#define MAXSTEPS       3 // Process (up to) this many concurrent steps

Adafruit_NeoPixel strip = Adafruit_NeoPixel(N_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// The readings from the sensors are usually around 250-350 when not being pressed,
// then dip below 100 when the heel is standing on it (for Phil's shoes; Becky's
// don't dip quite as low because she's smaller).
#define STEP_TRIGGER    150  // Reading must be below this to trigger step
#define STEP_HYSTERESIS 200  // After trigger, must return to this level

int
  stepMag[MAXSTEPS],  // Magnitude of steps
  stepX[MAXSTEPS],    // Position of 'step wave' along strip
  mag[SHOE_LEN_LEDS], // Brightness buffer (one side of shoe)
  stepFiltered,       // Current filtered pressure reading
  stepCount,          // Number of 'frames' current step has lasted
  stepMin;            // Minimum reading during current step
uint8_t
  stepNum = 0,        // Current step number in stepMag/stepX tables
  dup[SHOE_LEN_LEDS]; // Inside/outside copy indexes
boolean
  stepping  = false;  // If set, step was triggered, waiting to release


void setup() {
  pinMode(9, INPUT_PULLUP); // Set internal pullup resistor for sensor pin
  // As previously mentioned, the step animation is mirrored on the inside and
  // outside faces of the shoe.  To avoid a bunch of math and offsets later, the
  // 'dup' array indicates where each pixel on the outside face of the shoe should
  // be copied on the inside.  (255 = don't copy, as on front- or rear-most LEDs).
  // Later, the colors for the outside face of the shoe are calculated and then get
  // copied to the appropriate positions on the inside face.
  memset(dup, 255, sizeof(dup));
  int8_t a, b;
  for(a=1              , b=SHOE_LED_BACK-1            ; b>=0    ;) dup[a++] = b--;
  for(a=SHOE_LEN_LEDS-2, b=SHOE_LED_BACK+SHOE_LEN_LEDS; b<N_LEDS;) dup[a--] = b++;

  // Clear step magnitude and position buffers
  memset(stepMag, 0, sizeof(stepMag));
  memset(stepX  , 0, sizeof(stepX));
  strip.begin();
  stepFiltered = analogRead(STEP_PIN); // Initial input
}

void loop() {
  uint8_t i, j;

  // Read analog input, with a little noise filtering
  //stepFiltered = ((stepFiltered * 3) + analogRead(STEP_PIN)) >> 2;
    stepFiltered = (((stepFiltered * 3) - 100) + analogRead(STEP_PIN)) >> 2;
    
  // The strip doesn't simply display the current pressure reading.  Instead,
  // there's a bit of an animated flourish from heel to toe.  This takes time,
  // and during quick foot-tapping there could be multiple step animations
  // 'in flight,' so a short list is kept.
  if(stepping) { // If a step was previously triggered...
    if(stepFiltered >= STEP_HYSTERESIS) { // Has step let up?
      stepping = false;                   // Yep! Stop monitoring.
      // Add new step to the step list (may be multiple in flight)
      stepMag[stepNum] = (STEP_HYSTERESIS - stepMin) * 6; // Step intensity
      stepX[stepNum]   = -80; // Position starts behind heel, moves forward
      if(++stepNum >= MAXSTEPS) stepNum = 0; // If many, overwrite oldest
    } else if(stepFiltered < stepMin) stepMin = stepFiltered; // Track min val
  } else if(stepFiltered < STEP_TRIGGER) { // No step yet; watch for trigger
    stepping = true;         // Got one!
    stepMin  = stepFiltered; // Note initial value
  }

  // Render a 'brightness map' for all steps in flight.  It's like
  // a grayscale image; there's no color yet, just intensities.
  int mx1, px1, px2, m;
  memset(mag, 0, sizeof(mag));    // Clear magnitude buffer
  for(i=0; i<MAXSTEPS; i++) {     // For each step...
    if(stepMag[i] <= 0) continue; // Skip if inactive
    for(j=0; j<SHOE_LEN_LEDS; j++) { // For each LED...
      // Each step has sort of a 'wave' that's part of the animation,
      // moving from heel to toe.  The wave position has sub-pixel
      // resolution (4X), and is up to 80 units (20 pixels) long.
      mx1 = (j << 2) - stepX[i]; // Position of LED along wave
      if((mx1 <= 0) || (mx1 >= 80)) continue; // Out of range
      if(mx1 > 64) { // Rising edge of wave; ramp up fast (4 px)
        m = ((long)stepMag[i] * (long)(80 - mx1)) >> 4;
      } else { // Falling edge of wave; fade slow (16 px)
        m = ((long)stepMag[i] * (long)mx1) >> 6;
      }
      mag[j] += m; // Add magnitude to buffered sum
    }
    stepX[i]++; // Update position of step wave
    if(stepX[i] >= (80 + (SHOE_LEN_LEDS << 2)))
      stepMag[i] = 0; // Off end; disable step wave
    else
      stepMag[i] = ((long)stepMag[i] * 127L) >> 7; // Fade
  }

  // For a little visual interest, some 'sparkle' is added.
  // The cumulative step magnitude is added to one pixel at random.
  long sum = 0;
  for(i=0; i<MAXSTEPS; i++) sum += stepMag[i];
  if(sum > 0) {
    i = random(SHOE_LEN_LEDS);
    mag[i] += sum / 4;
  }

  // Now the grayscale magnitude buffer is remapped to color for the LEDs.
  // The code below uses a blackbody palette, which fades from white to yellow
  // to red to black.  The goal here was specifically a "walking on fire"
  // aesthetic, so the usual ostentatious rainbow of hues seen in most LED
  // projects is purposefully skipped in favor of a more plain effect.
  uint8_t r, g, b;
  int     level;
  for(i=0; i<SHOE_LEN_LEDS; i++) { // For each LED on one side...
    level = mag[i];                // Pixel magnitude (brightness)
    if(level < 255) {              // 0-254 = black to red-1
      r = pgm_read_byte(&gamma1[level]);
      g = b = 0;
    } else if(level < 510) {       // 255-509 = red to yellow-1
      r = 255;
      g = pgm_read_byte(&gamma1[level - 255]);
      b = 0;
    } else if(level < 765) {       // 510-764 = yellow to white-1
      r = g = 255;
      b = pgm_read_byte(&gamma1[level - 510]);
    } else {                       // 765+ = white
      r = g = b = 255;
    }
    // Set R/G/B color along outside of shoe
    strip.setPixelColor(i+SHOE_LED_BACK, r, g, b);
    // Pixels along inside are funny...
    j = dup[i];
    if(j < 255) strip.setPixelColor(j, r, g, b);
  }

  strip.show();
  delayMicroseconds(1500);
}
