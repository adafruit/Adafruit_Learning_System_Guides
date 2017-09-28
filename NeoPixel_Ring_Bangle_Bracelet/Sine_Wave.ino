//Basic sine wave animation for NeoPixel Ring Bangle Bracelet
//by Dano Wall and Becky Stern for Adafruit Industries
#include <Adafruit_NeoPixel.h>

#define PIN       1 // Marked D1 on GEMMA
#define NUM_LEDS 64

// Parameter 1 = number of pixels in strip
// Parameter 2 = pin number (most are valid)
// Parameter 3 = pixel type:
//   NEO_GRB  Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB  Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIN, NEO_GRB);

uint32_t color = strip.Color(75, 250, 100); // Change RGB color value here

// These are the pixels in order of animation-- 36 pixels in total:
int sine[] = {
   4,  3,  2,  1,  0, 15, 14, 13, 12, 20, 21, 22, 23, 24, 25, 26, 27, 28,
  36, 35, 34, 33, 32, 47, 46, 45, 44, 52, 53, 54, 55, 56, 57, 58, 59, 60 };

void setup() {
  strip.begin();
  strip.show();            // Initialize all pixels to 'off'
  strip.setBrightness(40); // 40/255 brightness (about 15%)
}

void loop() {
  for(int i=0; i<36; i++) {
    strip.setPixelColor(sine[i], color);             // Draw 'head' pixel
    strip.setPixelColor(sine[(i + 36 - 8) % 36], 0); // Erase 'tail'
    strip.show();
    delay(40);
  }
}
