// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#define BLOCK_1 33
#define BLOCK_2 32
#define NUM_PIXELS 8

Adafruit_NeoPixel STRIP_1(NUM_PIXELS, BLOCK_1, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel STRIP_2(NUM_PIXELS, BLOCK_2, NEO_GRB + NEO_KHZ800);

void setup() {
  STRIP_1.begin();
  STRIP_2.begin();
  STRIP_1.setBrightness(25);
  STRIP_2.setBrightness(50);
}

uint16_t pixelHue_1 = 0;
uint16_t pixelHue_2 = 256;

void loop() {  
  pixelHue_1 += 256;
  for(int i=0; i<STRIP_1.numPixels(); i++) {
      int hue_1 = pixelHue_1 + (i * 65536L / STRIP_1.numPixels());
      STRIP_1.setPixelColor(i, STRIP_1.gamma32(STRIP_1.ColorHSV(hue_1)));
    }
  STRIP_1.show();

  pixelHue_2 -= 256;
  for(int i=STRIP_2.numPixels(); i>-1; i--) {
      int hue_2 = pixelHue_2 + (i * 65536L / STRIP_2.numPixels());
      STRIP_2.setPixelColor(i, STRIP_2.gamma32(STRIP_2.ColorHSV(hue_2)));
    }
  STRIP_2.show();
  
  delay(10);

}
