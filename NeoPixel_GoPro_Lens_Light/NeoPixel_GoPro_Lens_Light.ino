// SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

#define PIN 0 //neopixel pin

int POT = A1; //analog pin 1 = Trinket m0 Pin 2
int val = 0;

// Parameter 1 = number of pixels in strip
// Parameter 2 = Arduino pin number (most are valid)
// Parameter 3 = pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
//   NEO_RGBW    Pixels are wired for RGBW bitstream (NeoPixel RGBW products)
Adafruit_NeoPixel ring = Adafruit_NeoPixel(16, PIN, NEO_RGBW + NEO_KHZ800);

void setup() {
  ring.begin();
  ring.setBrightness(255); //max brightness available for the pot
  ring.show(); // Initialize all pixels to 'off'
}

void loop() {
  val = analogRead(POT); //will hold analog value sent by pot
  val = map(val, 0, 1023, 0, 255); //maps analog values to digital so that it can be used by the neopixel

  uint16_t i;

  //sets all 16 pixels to on and only show level of white light defined by analog value of the pot
  for (i = 0; i < ring.numPixels(); i++) {
    ring.setPixelColor(i, 0, 0, 0, val);
  }
  ring.show();
}