// 'Cyber falls' sketch, adapted from code for Firewalker sneakers.
// Creates a fiery rain-like effect on multiple NeoPixel strips.
// Requires Adafruit Trinket and NeoPixel strips.  Strip length is
// inherently limited by Trinket RAM and processing power; this is
// written for five 15-pixel strands, which are paired up per pin
// for ten 15-pixel strips total.

#include <Adafruit_NeoPixel.h>
#include <avr/power.h>

uint8_t gamma[] PROGMEM = { // Gamma correction table for LED brightness
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

#define STRIPLEN 15 // Length of LED strips
#define MAXDROPS  5 // Max concurrent 'raindrops'
#define N_STRIPS  5 // Connect strips to pins 0 to (N_STRIPS-1)

Adafruit_NeoPixel strip = Adafruit_NeoPixel(STRIPLEN, 0);

// Everything's declared volatile because state changes inside
// an interrupt routine.
volatile struct {
  uint8_t  strip;
  int16_t  pos;
  uint8_t  speed;
  uint16_t brightness;
} drop[MAXDROPS];
volatile uint8_t
  nDrops    = 0,   // Number of 'active' raindrops
  prevStrip = 255; // Last selected strip
volatile uint16_t
  countdown = 0;   // Time to next raindrop

void setup() {

  // Set up Timer/Counter1 for ~30 Hz interrupt
#if F_CPU == 16000000L
  clock_prescale_set(clock_div_1);
  TCCR1  = _BV(PWM1A) |_BV(CS13) | _BV(CS12);             // 1:2048 prescale
#else
  TCCR1  = _BV(PWM1A) |_BV(CS13) | _BV(CS11) | _BV(CS10); // 1:1024 prescale
#endif

  // Turn strips off ASAP (must follow clock_prescale_set)
  strip.begin();
  for(uint8_t s=0; s<N_STRIPS; s++) {
    strip.setPin(s);
    strip.show();
  }

  // Finish timer/counter setup
  OCR1C  = 255;        // ~30 Hz
  GTCCR  = 0;          // No PWM out
  TIMSK |= _BV(TOIE1); // Enable overflow interrupt
}

void loop() { } // Not used -- everything's in interrupt below

// A timer interrupt is used so that everything runs at regular
// intervals, regardless of current amount of motion.
ISR(TIMER1_OVF_vect) {

  uint16_t mag[STRIPLEN];
  uint8_t  s, d, p, r, g, b;
  int      mx1, m, level;

  if(countdown == 0) {         // Time to launch new drop?
    if(nDrops < MAXDROPS-1) {  // Is there space for one in the list?
      do {
        s = random(N_STRIPS);
      } while(s == prevStrip); // Don't repeat prior strip
      drop[nDrops].strip      = prevStrip = s;
      drop[nDrops].pos        = -32; // Start off top of strip
      drop[nDrops].speed      = 1 + random(3);
      drop[nDrops].brightness = 250 + random(520);
      nDrops++;
      countdown = 9 + random(28); // Time to launch next one
    }
  } else countdown--;


  for(s=0; s<N_STRIPS; s++) { // For each strip...
    memset(mag, 0, sizeof(mag)); // Clear magnitude table

    // Render active drops for this strip into magnitude table
    for(d=0; d<nDrops; d++) {
      if(drop[d].strip == s) {
        for(p=0; p<STRIPLEN; p++) { // For each pixel...
          mx1 = (p << 2) - drop[d].pos; // Position of LED along wave
          if((mx1 <= 0) || (mx1 >= 32)) continue; // Out of range
          if(mx1 > 24) { // Rising edge of wave; ramp up fast (2 px)
            m = ((long)drop[d].brightness * (long)(32 - mx1)) >> 4;
          } else { // Falling edge of wave; fade slow (6 px)
            m = ((long)drop[d].brightness * (long)mx1) / 24;
          }
          mag[p] += m; // Accumulate result in magnitude buffer
        }
      }
    }

    // Remap magnitude table to RGB for strand
    for(p=0; p<STRIPLEN; p++) {      // For each pixel in strip
      level = mag[p];                // Pixel magnitude (brightness)
      if(level < 255) {              // 0-254 = black to green-1
        r = b = 0;
        g = pgm_read_byte(&gamma[level]);
      } else if(level < 510) {       // 255-509 = green to yellow-1
        r = pgm_read_byte(&gamma[level - 255]);
        g = 255;
        b = 0;
      } else if(level < 765) {       // 510-764 = yellow to white-1
        r = g = 255;
        b = pgm_read_byte(&gamma[level - 510]);
      } else {                       // 765+ = white
        r = g = b = 255;
      }
      strip.setPixelColor(p, r, g, b);
    }

    strip.setPin(s); // Select output pin
    strip.show();    // Strips don't need to refresh in sync
  }

  // Move 'active' drops
  for(d=0; d<nDrops; d++) {
    drop[d].pos += drop[d].speed;
    if(drop[d].pos >= (STRIPLEN * 4)) { // Off end?
      // Remove drop from list (move last one to this place)
      memcpy((void *)&drop[d], (void *)&drop[nDrops-1], sizeof(drop[0]));
      nDrops--;
    }
  }
}