// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // required for USB Serial
#include <Adafruit_NeoPixel.h>

const int neopixel_pin = PA4;
#define LED_COUNT 1
Adafruit_NeoPixel pixels(LED_COUNT, neopixel_pin, NEO_GRB + NEO_KHZ800);

void setup () {
  pixels.begin();
}

uint16_t firstPixelHue = 0;

void loop() {  
  firstPixelHue += 256;
  for(int i=0; i<pixels.numPixels(); i++) {
      int pixelHue = firstPixelHue + (i * 65536L / pixels.numPixels());
      pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(pixelHue)));
    }
  pixels.show();
  
  delay(10);

}
