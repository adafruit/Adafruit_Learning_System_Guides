// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

Adafruit_NeoPixel pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

const int buttonPin = MISO;

int buttonState = 0;

void setup() {
  Serial.begin(115200);
  pinMode(buttonPin, INPUT);
  pixel.begin();
  pixel.setBrightness(10);
  pixel.show();
}

void loop() {
  buttonState = digitalRead(buttonPin);

  if (buttonState == HIGH) {
    pixel.setPixelColor(0, 0x0);
    pixel.show();
  } else {
    pixel.setPixelColor(0, 0xFF0000);
    pixel.show();
  }
  delay(100);
}
