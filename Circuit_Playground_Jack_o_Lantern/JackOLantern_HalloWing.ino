// Jack-o-Lantern sketch for Adafruit Hallowing

#include "Adafruit_NeoPixel.h"

#define NUM_PIXELS 30

Adafruit_NeoPixel strip(NUM_PIXELS, 4, NEO_GRB + NEO_KHZ800);

void setup() {
  strip.begin();
}

uint8_t prev = 128;              // Start brightness in middle

void loop() {
  uint8_t lvl = random(64, 192); // End brightness at 128±64
  split(prev, lvl, 32);          // Start subdividing, ±32 at midpoint
  prev = lvl;                    // Assign end brightness to next start
}

void split(uint8_t y1, uint8_t y2, uint8_t offset) {
  if(offset) { // Split further into sub-segments w/midpoint at ±offset
    uint8_t mid = (y1 + y2 + 1) / 2 + random(-offset, offset);
    split(y1 , mid, offset / 2); // First segment (offset is halved)
    split(mid, y2 , offset / 2); // Second segment (ditto)
  } else { // No further subdivision - y1 determines LED brightness
    uint32_t c = (((int)(pow((float)y1 / 255.0, 2.7) * 255.0 + 0.5) // Gamma
                 * 0x1004004) >> 8) & 0xFF3F03; // Expand to 32-bit RGB color
    for(uint8_t i=0; i<NUM_PIXELS; i++) strip.setPixelColor(i, c);
    strip.show();
    delay(4);
  }
}
