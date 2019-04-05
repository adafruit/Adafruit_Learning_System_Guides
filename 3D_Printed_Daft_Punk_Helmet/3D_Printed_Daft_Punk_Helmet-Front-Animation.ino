// Fiery demon horns (rawr!) for Adafruit Trinket/Gemma.
// Adafruit invests time and resources providing this open source code, 
// please support Adafruit and open-source hardware by purchasing 
// products from Adafruit!
#include <Adafruit_NeoPixel.h>
#include <avr/power.h>

#define N_HORNS 1
#define N_LEDS 30 // Per horn
#define PIN     0
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(N_HORNS * N_LEDS, PIN);

//      /\  ->   Fire-like effect is the sum of multiple triangle
// ____/  \____  waves in motion, with a 'warm' color map applied.
#define N_WAVES 6     // Number of simultaneous waves (per horn)
// Coordinate space for waves is 16x the pixel spacing,
// allowing fixed-point math to be used instead of floats.
struct {
  int16_t  lower;     // Lower bound of wave
  int16_t  upper;     // Upper bound of wave
  int16_t  mid;       // Midpoint (peak) ((lower+upper)/2)
  uint8_t  vlower;    // Velocity of lower bound
  uint8_t  vupper;    // Velocity of upper bound
  uint16_t intensity; // Brightness at peak
} wave[N_HORNS][N_WAVES];
long fade; // Decreases brightness as wave moves

// Gamma correction improves appearance of midrange colors
uint8_t gamma[] PROGMEM = {
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

static void random_wave(uint8_t h,uint8_t w) {          // Randomize one wave struct
  wave[h][w].upper     = -1;                            // Always start just below head of strip
  wave[h][w].lower     = -16 * (3 + random(4));         // Lower end starts ~3-7 pixels back
  wave[h][w].mid       = (wave[h][w].lower + wave[h][w].upper) / 2;
  wave[h][w].vlower    = 3 + random(4);                 // Lower end moves at ~1/8 to 1/4 pixel/frame
  wave[h][w].vupper    = wave[h][w].vlower + random(4); // Upper end moves a bit faster, spreading wave
  wave[h][w].intensity = 300 + random(600);
}

void setup() {
  uint8_t h, w;

  randomSeed(analogRead(1));
  pixels.begin();
  for(h=0; h<N_HORNS; h++) {
    for(w=0; w<N_WAVES; w++) random_wave(h, w);
  }
  fade = 234 + N_LEDS / 2;
  if(fade > 255) fade = 255;

  // A ~100 Hz timer interrupt on Timer/Counter1 makes everything run
  // at regular intervals, regardless of current amount of motion.
#if F_CPU == 16000000L
  clock_prescale_set(clock_div_1);
  TCCR1  = _BV(PWM1A) | _BV(CS13) | _BV(CS11) | _BV(CS10); // 1:1024 prescale
  OCR1C  = F_CPU / 1024 / 100 - 1;
#else
  TCCR1  = _BV(PWM1A) | _BV(CS13) | _BV(CS11); // 1:512 prescale
  OCR1C  = F_CPU / 512 / 100 - 1;
#endif
  GTCCR  = 0;          // No PWM out
  TIMSK |= _BV(TOIE1); // Enable overflow interrupt
}

void loop() { } // Not used -- everything's in interrupt below

ISR(TIMER1_OVF_vect) {
  uint8_t  h, w, i, r, g, b;
  int16_t  x;
  uint16_t sum;

  for(h=0; h<N_HORNS; h++) {              // For each horn...
    for(x=7, i=0; i<N_LEDS; i++, x+=16) { // For each LED along horn...
      for(sum=w=0; w<N_WAVES; w++) {      // For each wave of horn...
        if((x < wave[h][w].lower) || (x > wave[h][w].upper)) continue; // Out of range
        if(x <= wave[h][w].mid) { // Lower half of wave (ramping up to peak brightness)
          sum += wave[h][w].intensity * (x - wave[h][w].lower) / (wave[h][w].mid - wave[h][w].lower);
        } else {               // Upper half of wave (ramping down from peak)
          sum += wave[h][w].intensity * (wave[h][w].upper - x) / (wave[h][w].upper - wave[h][w].mid);
        }
      }
      // Now the magnitude (sum) is remapped to color for the LEDs.
      // A blackbody palette is used - fades white-yellow-red-black.
      if(sum < 255) {        // 0-254 = black to red-1
        r = pgm_read_byte(&gamma[sum]);
        g = b = 0;
      } else if(sum < 510) { // 255-509 = red to yellow-1
        r = 255;
        g = pgm_read_byte(&gamma[sum - 255]);
        b = 0;
      } else if(sum < 765) { // 510-764 = yellow to white-1
        r = g = 255;
        b = pgm_read_byte(&gamma[sum - 510]);
      } else {               // 765+ = white
        r = g = b = 255;
      }
      pixels.setPixelColor(h * N_LEDS + i, r, g, b);
    }

    for(w=0; w<N_WAVES; w++) { // Update wave positions for each horn
      wave[h][w].lower += wave[h][w].vlower;  // Advance lower position
      if(wave[h][w].lower >= (N_LEDS * 16)) { // Off end of strip?
        random_wave(h, w);                    // Yes, 'reboot' wave
      } else {                                // No, adjust other values...
        wave[h][w].upper    +=  wave[h][w].vupper;
        wave[h][w].mid       = (wave[h][w].lower + wave[h][w].upper) / 2;
        wave[h][w].intensity = (wave[h][w].intensity * fade) / 256; // Dimmer
      }
    }
  }
  pixels.show();
}
