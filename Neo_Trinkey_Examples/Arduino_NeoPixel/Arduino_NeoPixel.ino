// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#define NUMPIXELS 64
Adafruit_NeoPixel neostrip(NUMPIXELS, PIN_DATA, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);

  neostrip.begin();
  neostrip.setBrightness(25);
  neostrip.show();

}

uint16_t firstPixelHue = 0;

void loop() {  
  firstPixelHue += 256;
  for(int i=0; i<neostrip.numPixels(); i++) {
      int pixelHue = firstPixelHue + (i * 65536L / neostrip.numPixels());
      neostrip.setPixelColor(i, neostrip.gamma32(neostrip.ColorHSV(pixelHue)));
    }
  neostrip.show();
  
  delay(10);

}
