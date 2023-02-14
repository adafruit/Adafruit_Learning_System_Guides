// SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Basic Keyboard Example for NeoKey BFF

#include <Keyboard.h>
#include <Adafruit_NeoPixel.h>

#define LED_PIN A3
#define MX_PIN A2
#define LED_COUNT 1

int mxState = 0;

Adafruit_NeoPixel pixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  Keyboard.begin();
  delay(5000);
  pinMode(MX_PIN, INPUT);
  pixel.begin();
  pixel.show();            
  pixel.setBrightness(50); 
}

void loop() {
  mxState = digitalRead(MX_PIN);

  if(mxState == HIGH) {      
    pixel.setPixelColor(0, pixel.Color(150, 0, 0));
    pixel.show();
    Keyboard.print("Hello World!");
  }

  if(mxState == LOW) {
    pixel.setPixelColor(0, pixel.Color(0, 0, 0));
    pixel.show();
  }

}
