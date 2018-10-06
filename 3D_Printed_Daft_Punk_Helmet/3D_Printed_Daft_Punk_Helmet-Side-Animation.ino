// Adafruit Trinket+NeoPixel animation for Daft Punk-inspired helmet.
// Contains some ATtiny85-specific stuff; won't run as-is on Uno, etc.

// Operates in HSV (hue, saturation, value) colorspace rather than RGB.
// Animation is an interference pattern between two waves; one controls
// saturation, the other controls value (brightness).  The wavelength,
// direction, speed and type (square vs triangle wave) for each is randomly
// selected every few seconds.  Hue is always linear, but other parameters
// are similarly randomized.

#include <Adafruit_NeoPixel.h>
#include <avr/power.h>

// GLOBAL STUFF --------------------------------------------------------------

#define N_LEDS 29
#define PIN     0

Adafruit_NeoPixel    pixels = Adafruit_NeoPixel(N_LEDS, PIN);
volatile uint16_t    count  = 1; // Countdown to next animation change
extern const uint8_t gamma[];    // Big table at end of this code

volatile struct {
  uint8_t type,      // 0 = square wave, 1 = triangle wave
          value[2];  // 0 = start-of-frame value, 1 = pixel-to-pixel value
  int8_t  inc[2];    // 0 = frame-to-frame increment, 1 = pixel-to-pixel inc
} wave[3];           // 0 = Hue, 1 = Saturation, 2 = Value (brightness)

#define WAVE_H 0     // Array indices for wave[]
#define WAVE_S 1
#define WAVE_V 2
#define FRAME  0     // Array indices for value[] and inc[]
#define PIXEL  1


// INITIALIZATION ------------------------------------------------------------

void setup() {
  pixels.begin();
  randomSeed(analogRead(0)); // Seed random() from a floating pin (D2)

  // Timer/Counter 1 is used to generate a steady ~50 Hz frame rate.
#if F_CPU == 16000000L
  clock_prescale_set(clock_div_1);
  TCCR1  = _BV(PWM1A) | _BV(CS13) | _BV(CS12); // 1:2048 prescale
  OCR1C  = F_CPU / 2048 / 50 - 1;
#else
  TCCR1  = _BV(PWM1A) | _BV(CS13) | _BV(CS11) | _BV(CS10); // 1:1024
  OCR1C  = F_CPU / 1024 / 50 - 1;
#endif
  GTCCR  = 0;          // No PWM out
  TIMSK |= _BV(TOIE1); // Enable overflow interrupt
}

void loop() { } // Not used here -- everything's in interrupt below


// 50 HZ LOOP ----------------------------------------------------------------

ISR(TIMER1_OVF_vect) {
  uint8_t  w, i, n, s, v, r, g, b;
  uint16_t v1, s1;

  if(!(--count)) {              // Time for new animation?
    count = 250 + random(250);  // New effect will run for 5-10 sec.
    for(w=0; w<3; w++) {        // Three waves (H,S,V)...
      wave[w].type = random(2); // Assign random type (square/triangle)
      for(i=0; i<2; i++) {      // For frame and pixel increments...
        while(!(wave[w].inc[i] = random(15) - 7)); // Set non-zero random
        // wave value is never initialized; it's allowed to carry over
      }
      wave[w].value[PIXEL] = wave[w].value[FRAME];
    }
    wave[WAVE_S].inc[PIXEL] *= 16; // Make saturation & value
    wave[WAVE_V].inc[PIXEL] *= 16; // blinkier along strip
  } else { // Continue current animation; update waves
    for(w=0; w<3; w++) {
      wave[w].value[FRAME] += wave[w].inc[FRAME];   // OK if this wraps!
      wave[w].value[PIXEL]  = wave[w].value[FRAME];
    }
  }

  // Render current animation frame.  COGNITIVE HAZARD: fixed point math.

  for(i=0; i<N_LEDS; i++) { // For each LED along strip...

    // Coarse (8-bit) HSV-to-RGB conversion, hue first:
    n   = (wave[WAVE_H].value[PIXEL] % 43) * 6; // Angle within sextant; 0-255
    switch(wave[WAVE_H].value[PIXEL] / 43) {    // Sextant number; 0-5
      case 0 : r = 255    ; g =   n    ; b =   0    ; break; // R to Y
      case 1 : r = 254 - n; g = 255    ; b =   0    ; break; // Y to G
      case 2 : r =   0    ; g = 255    ; b =   n    ; break; // G to C
      case 3 : r =   0    ; g = 254 - n; b = 255    ; break; // C to B
      case 4 : r =   n    ; g =   0    ; b = 255    ; break; // B to M
      default: r = 255    ; g =   0    ; b = 254 - n; break; // M to R
    }

    // Saturation = 1-256 to allow >>8 instead of /255
    s = wave[WAVE_S].value[PIXEL];
    if(wave[WAVE_S].type) {     // Triangle wave?
      if(s & 0x80) {            // Downslope
        s    = (s & 0x7F) << 1;
        s1   = 256 - s;
      } else {                  // Upslope
        s  <<= 1;
        s1   = 1   + s;
        s    = 255 - s;
      }
    } else {                    // Square wave
      if(s & 0x80) {            // 100% saturation
        s1 = 256;
        s  =   0;
      } else {                  // 0% saturation (white)
        s1 =   1;
        s  = 255;
      }
    }

    // Value (brightness) = 1-256 for similar reasons
    v  = wave[WAVE_V].value[PIXEL];
    v1 = (wave[WAVE_V].type) ?                      // Triangle wave?
         ((v & 0x80) ? 64 - ((v & 0x7F) << 1) :    // Downslope
                         1 + ( v         << 1)  ) : // Upslope
         ((v & 0x80) ? 256 : 1);                    // Square wave; on/off

    pixels.setPixelColor(i,
      pgm_read_byte(&gamma[((((r * s1) >> 8) + s) * v1) >> 8]),
      pgm_read_byte(&gamma[((((g * s1) >> 8) + s) * v1) >> 8]),
      pgm_read_byte(&gamma[((((b * s1) >> 8) + s) * v1) >> 8]));

    // Update wave values along length of strip (values may wrap, is OK!)
    for(w=0; w<3; w++) wave[w].value[PIXEL] += wave[w].inc[PIXEL];
  }

  pixels.show();
}

// Gamma correction improves appearance of midrange colors.
// This table is positioned down here because it's a big annoying
// distraction.  The 'extern' near the top lets us reference it earlier.
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
