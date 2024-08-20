// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#include "Adafruit_TestBed.h"
extern Adafruit_TestBed TB;

Adafruit_NeoPixel pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

void setup() {
  //while (! Serial) delay(10);
  Serial.begin(115200);
  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1; 
  TB.begin();
  TB.setColor(WHITE);
}

uint8_t j = 0;

void loop() {
  
    TB.setColor(TB.Wheel(j++));
    delay(10);
    if (j == 0) {
      TB.printI2CBusScan();
    }

}
