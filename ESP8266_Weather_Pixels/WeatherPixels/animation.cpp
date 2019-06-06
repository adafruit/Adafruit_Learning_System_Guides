// Weather animation is rendered procedurally based on a few parameters
// (time of day, cloud cover, rainfall, etc.). Most of the inputs are NOT
// real-world units...see comments for explanation of what's needed.

// NeoPixel stuff --------------------------------------------------------

#include <Adafruit_NeoPixel.h>

#define NEOPIXEL_PIN 14 // NeoPixels are connected to this pin
#define NUM_LEDS    16 // Number of NeoPixels
#define FPS         50 // Animation frame rate (frames per second)

Adafruit_NeoPixel leds(NUM_LEDS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

// Animation control stuff -------------------------------------------------

uint8_t renderBuf[NUM_LEDS][3], // Each frame of animation is assembled here
        alphaBuf[NUM_LEDS],     // Alpha mask for compositing each layer
        rainBuf[NUM_LEDS],      // Extra mask just for raindrop brightness
        rainCounter  = 1,       // Drop-to-drop countdown, in frames
        rainInterval = 0,       // Drop-to-drop interval, frames (0=no rain)
        windSpeed    = 0,       // Per-frame cloud motion (see comments)
        cloudCover   = 0;       // Percent cloud cover

uint16_t sunCenter   = 0,       // Position of 'sun' in 16-bit sky
         sunRadius   = 8192,    // Size of sun (same units)
         cloudOffset = 0,       // Position of cloud bitmap 'seam'
         timeOfDay   = 32768;   // Fixed-point day/night value (see notes)

uint8_t lightningBrightness = 0;
uint8_t lightningIntensity  = 0;
uint8_t snowIntensity       = 0;

uint32_t cloudBits   = 0;       // Bitmask of clouds
#if NUM_LEDS < 32
 #define NUM_CLOUD_BITS NUM_LEDS
#else
 #define NUM_CLOUD_BITS 32
#endif

#define N_STARS (3 + (NUM_LEDS / 7))
struct star {
  uint8_t pos;
  uint8_t brightness;
} star[N_STARS];

// Flake will "move," then "stop" when it hits the "ground," then fade.
// Kinda like raindrops, but moving first.
#define MAX_FLAKES (3 + (NUM_LEDS / 7))
struct flake {
  uint16_t pos;
  int16_t  speed;
  uint8_t  brightness;
  uint8_t  time;
} flake[MAX_FLAKES];
uint8_t nFlakes = 0;

void randomFlake(void) {
  flake[nFlakes].pos        = random(65536);
  uint8_t w = windSpeed;
  if(w < 20) w = 20;
  do {
    flake[nFlakes].speed    = random(w / -4, (w * 5) / 4);
  } while(!flake[nFlakes].speed);
  flake[nFlakes].brightness = random(128, 255);
  flake[nFlakes].time       = random(FPS, FPS * 2); // # frames until snowflake "touches ground"
  nFlakes++;
}


uint16_t lightningCounter = 0;

extern const uint8_t gamma8[]; // Big table at end of this code

// One-time initialization - clears NeoPixels & sets up some variables -----

void animSetup(void) {

  leds.begin();
  leds.setBrightness(200);
  leds.clear(); // All NeoPixels off ASAP
  leds.show();

  randomSeed(analogRead(A0));

  memset(rainBuf, 0, sizeof(rainBuf)); // Clear rain buffer
  for(uint8_t i=0; i<N_STARS; i++) {   // Initialize star positions
    star[i].pos = random(NUM_LEDS);    // TO DO: make stars not overlap
    star[i].brightness = random(15, 45);
  }
  memset(flake, 0, sizeof(flake));     // Clear snowflakes
}

// Utility functions -------------------------------------------------------

// Set up animation based on some weather attributes like cloud cover, etc.
void animConfig(
 uint16_t t,   // Time of day in fixed-point 16-bit units, where 0=midnight,
               // 32768=noon, 65536=midnight. THIS DOES NOT CORRESPOND TO
               // ANY SORT OF REAL-WORLD UNITS LIKE SECONDS, nor does it
               // handle things like seasons or Daylight Saving Time, it's
               // just an "ish" approximation to give the sky animation some
               // vague context. The time of day should be polled from the
               // same source that's providing the weather data, DO NOT use
               // millis() or micros() to attempt to follow real time, as
               // the NeoPixel library is known to mangle these interrupt-
               // based functions. TIME OF DAY IS "ISH!"
 uint8_t  c,   // Cloud cover, as a percentage (0-100).
 uint8_t  r,   // Rainfall as a "strength" value (0-255) that doesn't really
               // correspond to anything except "none" to "max."
 uint8_t  s,   // Snowfall, similar "strength" value (0-255).
 uint8_t  l,   // Lightning, ditto.
 uint8_t  w) { // Wind speed as a "strength" value (0-255) that also doesn't
               // correspond to anything real; this is the number of fixed-
               // point units that the clouds will move per frame. There are
               // 65536 units around the 'sky,' so a value of 255 will take
               // about 257 frames to make a full revolution of the LEDs,
               // which at 50 FPS would be a little over 5 seconds.

  timeOfDay          = t;
  cloudCover         = (c > 100) ? 100 : c;
  rainInterval       = r ? map(r, 1, 255, 64, 1) : 0;
  windSpeed          = w;
  lightningIntensity = l;
  snowIntensity      = s;

  // Randomize cloud bitmask based on cloud cover percentage:
  cloudBits = 0;
  for(uint8_t i=0; i<NUM_CLOUD_BITS; i++) {
    cloudBits <<= 1;
    if(cloudCover > random(150)) cloudBits |= 1;
  }

  nFlakes = 0;
  memset(flake, 0, sizeof(flake));
  if(s) {
    uint8_t n = 3 + (snowIntensity * (MAX_FLAKES - 2)) / 256;
    while(nFlakes < n) {
      randomFlake();
    }
  }
}

// Interpolate between two 'packed' (32-bit) RGB colors.
// Second argument is weighting (0-255) of second color.
uint32_t colorInterp(uint32_t color1, uint32_t color2, uint8_t w) {
  uint8_t  r1 = (color1 >> 16) & 0xFF,
           g1 = (color1 >>  8) & 0xFF,
           b1 =  color1        & 0xFF,
           r2 = (color2 >> 16) & 0xFF,
           g2 = (color2 >>  8) & 0xFF,
           b2 =  color2        & 0xFF;
  uint16_t w2 = (uint16_t)w + 1, // 1-256
           w1 = 257 - w2;        // 1-256
  r1 = (r1 * w1 + r2 * w2) >> 8;
  g1 = (g1 * w1 + g2 * w2) >> 8;
  b1 = (b1 * w1 + b2 * w2) >> 8;
  return (((uint32_t)r1 << 16) | ((uint32_t)g1 << 8) | b1);
}

// Using alphaBuf as a mask, fill an RGB color atop renderBuf
void overlay(uint8_t r, uint8_t g, uint8_t b) {
  uint16_t i, a1, a2;
  for(i=0; i<NUM_LEDS; i++) {
    a1 = alphaBuf[i] + 1; // 1-256
    a2 = 257 - a1;        // 1-256
    renderBuf[i][0] = (r * a1 + renderBuf[i][0] * a2) >> 8;
    renderBuf[i][1] = (g * a1 + renderBuf[i][1] * a2) >> 8;
    renderBuf[i][2] = (b * a1 + renderBuf[i][2] * a2) >> 8;
  }
}

// Same as above, for packed 32-bit RGB value
void overlay(uint32_t color) {
  overlay((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF);
}

void waitForFrame(void) {
  static uint32_t timeOfLastFrame = 0L;
  uint32_t t;
  while(((t = millis()) - timeOfLastFrame) < (1000 / FPS)) yield();
  timeOfLastFrame = t;
}

#define NIGHTSKYCLEAR   0x0a1923
#define DAYSKYCLEAR     0x28648c
#define NIGHTSKYCLOUDBG 0x2c2425
#define DAYSKYCLOUDBG   0x5e6065
#define NIGHTSKYCLOUDFG 0x515159
#define DAYSKYCLOUDFG   0xc2c2c2
#define NIGHTSNOW       0xa6b1c0
#define DAYSNOW         0xffffff
#define SUNCLEAR        0xffff60
#define SUNCLOUDY       0x7a7a61

void renderFrame(void) {
  // Display *prior* frame of data at start of function --
  // this ensures uniform updates, as render time may vary.
  leds.show();

  // Then begin processing next frame...

  int i;

  // tod: 0-64K, where 0 = midnight, 32K = noon, 64K = midnight
  // this is an artistic approximation and doesn't take seasons,
  // etc into consideration. if you need that, can fudge it into
  // tod rather than here.
  // Sunrise and sunset are two 90-minute periods centered around
  // 6am and 6pm (again, not factoring in seasons, daylight savings
  // time, etc.). Sky and other effects will interpolate between
  // day and night states for these two things.
  long y = timeOfDay;
  uint8_t dayWeight;
  if(y > 32767) y = 65536 - y;
  y = y * 256L / 4096 - 896;
  dayWeight = (y > 255) ? 255 : ((y < 0) ? 0 : y); // 0-255 night/day

  // Determine sky and cloud color based on % of cloud cover
  uint32_t
    clearSkyColor  = colorInterp(NIGHTSKYCLEAR  , DAYSKYCLEAR  , dayWeight),
    cloudySkyColor = colorInterp(NIGHTSKYCLOUDBG, DAYSKYCLOUDBG, dayWeight),
    cloudColor     = colorInterp(NIGHTSKYCLOUDFG, DAYSKYCLOUDFG, dayWeight),
    skyColor       = colorInterp(clearSkyColor, cloudySkyColor, map(cloudCover, 30, 70, 0, 255));

  for(i=0; i<NUM_LEDS; i++) {
    renderBuf[i][0] = skyColor >> 16;
    renderBuf[i][1] = skyColor >>  8;
    renderBuf[i][2] = skyColor;
  }

  // Stars
  if(dayWeight < 128) { // Dark? Or getting there?
    uint16_t nightWeight = 257 - dayWeight;
    memset(alphaBuf, 0, sizeof(alphaBuf));
    for(i=0; i<N_STARS; i++) {
      alphaBuf[star[i].pos] = (nightWeight * random(star[i].brightness/2, star[i].brightness)) >> 8;
    }
    overlay(255, 255, 255);
  } else {
    sunRadius = map(dayWeight, 128, 255, 1, 8192);
    uint16_t x;
    int16_t px1, px2, sx1, sx2;

    // Clear alpha buffer, gonna render 'sun' there...
    memset(alphaBuf, 0, sizeof(alphaBuf));

    uint32_t
      sunColor = colorInterp(SUNCLEAR, SUNCLOUDY, map(cloudCover, 30, 70, 0, 255));

    // Figure overlap between sun and each pixel...
    //  uint16_t left, right, dist1, dist2;
    for(i=0; i<NUM_LEDS; i++) {
      // Pixel coord in fixed-point space
      x = (i * 65536L) / NUM_LEDS;
      int16_t foo = sunCenter - x; // sun center in pixel space
      sx1 = foo - sunRadius;
      sx2 = foo + sunRadius;
      px1 = 0;
      px2 = 65536 / NUM_LEDS;
      if((sx1 >= px2) || (sx2 < 0)) continue; // No overlap
      else if((sx1 <= 0) && (sx2 >= px2)) alphaBuf[i] = 255; // Fully encompassed
      else {
        if(sx1 > 0) {
          if(sx2 < px2) {
            alphaBuf[i] = 255L * (sx2 - sx1) / (px2 - px1);
          } else {
            alphaBuf[i] = 255L * (px2 - sx1) / (px2 - px1);
          }
        } else {
          alphaBuf[i] = 255L * (sx2 - px1) / (px2 - px1);
        }
      }
    }
    
    overlay(sunColor); // Composite sun atop sky
  }

  if(cloudBits) {
    // Clear alpha buffer, gonna render clouds there...
    memset(alphaBuf, 0, sizeof(alphaBuf));
    uint16_t x, minor;
    uint8_t  major, l, r;
    for(i=0; i<NUM_LEDS; i++) {
      x           = (i * 65536L) / NUM_LEDS - cloudOffset;  // Pixel coord in fixed-point space (0-65535) relative to clouds
      x           = (x * (NUM_CLOUD_BITS * 256UL)) / 65536; // Scale to cloud pixel space
      major       = x >> 8;                                 // Left bit number (0 to NUM_CLOUD_BITS-1)
      minor       = x & 0xFF;                               // Weight (0-255) of next bit over
      l           = (cloudBits & (1 << major)) ? 220 : 0;   // Left bit opacity
      if(++major >= NUM_CLOUD_BITS) major = 0;              // Next bit over
      r           = (cloudBits & (1 << major)) ? 220 : 0;   // Right bit opacity
      alphaBuf[i] = ((l * (257 - minor)) + (r * (minor + 1))) >> 8; // Blend
    }

    uint32_t c = colorInterp(NIGHTSKYCLOUDFG, DAYSKYCLOUDFG, dayWeight);
    overlay(c); // Composite clouds atop sky
  }

  if(rainInterval) {
    memset(alphaBuf, 0, sizeof(alphaBuf));
    for(i=0; i<NUM_LEDS; i++) {
      rainBuf[i] = (rainBuf[i] * (uint16_t)245) >> 8;
    }
    // Periodically, randomly, add a drop to rainBuf[]
    if(!--rainCounter) {
      i = random(NUM_LEDS); // Which spot?
      int16_t foo = rainBuf[i] + 255;
      if(foo > 255) foo = 255;
      rainBuf[i] = foo;
      uint8_t r4 = rainInterval / 4;
      if(r4 < 1) r4 = 1;
      rainCounter = random(r4, rainInterval);
    }
    memcpy(alphaBuf, rainBuf, sizeof(rainBuf));
    overlay(130, 130, 150);
  }

  if(nFlakes) {
    uint16_t x, minor;
    uint8_t  major, l, r;
    memset(alphaBuf, 0, sizeof(alphaBuf));
    for(i=0; i<nFlakes; i++) {
      // Render flake here
      x     = (flake[i].pos * (NUM_LEDS * 256UL)) / 65536;
      major = x >> 8;   // Left pixel number (0 to NUM_LEDS-1)
      minor = x & 0xFF; // Weight (0-255) of next pixel over
      alphaBuf[major] = (alphaBuf[major] * (1   + minor)) + (flake[i].brightness * (257 - minor)) >> 8;
      if(++major >= NUM_LEDS) major = 0;
      alphaBuf[major] = (alphaBuf[major] * (257 - minor)) + (flake[i].brightness * (1   + minor)) >> 8;
      flake[i].pos += flake[i].speed;
      if(flake[i].time) {
        flake[i].time--;
      } else {
        flake[i].brightness = (flake[i].brightness * 253) >> 8;
        if(!flake[i].brightness) {
          memcpy(&flake[i], &flake[nFlakes-1], sizeof(struct flake)); // Move last flake to this pos.
          i--;           // Flake moved, so don't increment
          nFlakes--;     // Decrement number of flakes
          randomFlake(); // And add a new one in last pos.
        }
      }
    }
    overlay(255, 255, 255);
  }

  if(lightningBrightness) {
    for(i=0; i<NUM_LEDS; i++) alphaBuf[i] = lightningBrightness;
    overlay(255, 255, 255);
    lightningBrightness = (lightningBrightness * 220) >> 8;
  }
  if(lightningIntensity) {
    if(!random(50 + (255 - lightningIntensity) * 3)) {
      i = random(128, 256);
      if(i > lightningBrightness) lightningBrightness = i;
    }
  }

  sunCenter   += 65536 / 30 / FPS; // 30 sec for 1 revolution
  cloudOffset -= windSpeed;

//  timeOfDay += 65536/60/FPS; // 1 min for day/night cycle

  // Convert RGB renderbuf to gamma-corrected LED-native color order:
  for(uint16_t i=0; i<NUM_LEDS; i++) {
    leds.setPixelColor(i,
      pgm_read_byte(&gamma8[renderBuf[i][0]]),
      pgm_read_byte(&gamma8[renderBuf[i][1]]),
      pgm_read_byte(&gamma8[renderBuf[i][2]]));
  }
  // DON'T call leds.show() here! That's done at start of function.
}

// Gamma correction improves appearance of midrange colors
const uint8_t gamma8[] PROGMEM = {
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


