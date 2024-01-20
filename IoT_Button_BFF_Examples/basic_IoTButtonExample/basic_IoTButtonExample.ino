// SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Basic IoT Button with NeoPixel BFF Demo

#include <Adafruit_NeoPixel.h>

#define LED_PIN    A3
#define BUTTON_PIN A2
#define LED_COUNT 1

int buttonState = 0;

Adafruit_NeoPixel pixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  pinMode(BUTTON_PIN, INPUT);
  pixel.begin();
  pixel.show();            
  pixel.setBrightness(50); 
}

void loop() {
  //pixel.clear();
  buttonState = digitalRead(BUTTON_PIN);

  if(buttonState == HIGH) {      
    pixel.setPixelColor(0, pixel.Color(150, 0, 0));
    pixel.show();
  }

  if(buttonState == LOW) {
    pixel.setPixelColor(0, pixel.Color(0, 0, 0));
    pixel.show();
  }

}
