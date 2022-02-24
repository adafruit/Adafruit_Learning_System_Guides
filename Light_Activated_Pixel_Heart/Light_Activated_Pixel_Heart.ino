// SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#define NUM_LEDS 8  // This many NeoPixels...
#define LED_PIN  1  // are connected to this DIGITAL pin #
#define SENSOR   2  // Light sensor to this DIGITAL pin #

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN);

void setup() {
  strip.begin();
  strip.show();                  // Initialize all pixels to 'off'
  pinMode(SENSOR, INPUT_PULLUP); // Enable pull-up resistor on sensor pin
}

void loop() {
  // The LDR is being used as a digital (binary) sensor, so it must be
  // COMPLETELY dark to turn it off, your finger is not opaque enough!
  if(!digitalRead(SENSOR)) {                 // Sensor exposed to light?
    colorWipe(strip.Color(255, 0, 255), 50); // Animate purple
  } else {                                   // else sensor is dark
    colorWipe(strip.Color(0, 0, 0), 50);     // Animate off
  }
  delay(2); // Pause 2 ms before repeating
}

// Fill pixels one after the other with a color
void colorWipe(uint32_t c, uint8_t wait) {
  for(uint16_t i=0; i<strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
    strip.show();
    delay(wait);
  }
}
