// SPDX-FileCopyrightText: 2017 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#define NUM_LEDS 5 // Number of NeoPixels
#define PIN 1      // DIGITAL pin # where NeoPixels are connected

// IMPORTANT: Avoid connecting on a live circuit...
// if you must, connect GND first.

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIN);

void setup() {
  strip.begin();
  strip.setBrightness(100); // 100/255 brightness (about 40%)
  strip.show();             // Initialize all pixels to 'off'
}

void loop() {
  for(int j=0; j<256; j++) {
    for(int i=0; i<NUM_LEDS; i++) {
      strip.setPixelColor(i, Wheel((i * 8 + j) & 255));
    }
    strip.show();
    delay(20);
  }
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
    return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
    WheelPos -= 170;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}
