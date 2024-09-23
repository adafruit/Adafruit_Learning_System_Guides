// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_DotStar.h>

#define NUMPIXELS 64
Adafruit_DotStar  dotstrip(NUMPIXELS, PIN_DATA, PIN_CLOCK, DOTSTAR_BRG);

void setup() {
  Serial.begin(115200);
  
  dotstrip.begin();
  dotstrip.setBrightness(25);
  dotstrip.show();

}

uint16_t firstPixelHue = 0;

void loop() {  
  firstPixelHue += 256;
  
  for(int i=0; i<dotstrip.numPixels(); i++) {
    int pixelHue = firstPixelHue + (i * 65536L / dotstrip.numPixels());
    dotstrip.setPixelColor(i, dotstrip.gamma32(dotstrip.ColorHSV(pixelHue)));
  }
  dotstrip.show();
  delay(10);

}
