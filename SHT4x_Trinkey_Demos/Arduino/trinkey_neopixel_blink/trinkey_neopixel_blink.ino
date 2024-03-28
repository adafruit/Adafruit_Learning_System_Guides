// SPDX-FileCopyrightText: 2024 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

Adafruit_NeoPixel pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

void setup() {
  pixel.begin();
  pixel.setBrightness(10);
  pixel.show();
}

void loop() {
  pixel.setPixelColor(0, 0xFF0000);
  pixel.show();
  Serial.println("on!");
  delay(1000);
  pixel.setPixelColor(0, 0x0);
  pixel.show();
  Serial.println("off!");
  delay(1000);
}
