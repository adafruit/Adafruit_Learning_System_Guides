// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "Adafruit_TestBed.h"

extern Adafruit_TestBed TB;

void setup() {
  Serial.begin(115200);
  // while (! Serial) delay(10);
  
  delay(100);
  
  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1; 
  TB.begin();
  TB.setColor(WHITE);
}

uint8_t j = 0;

void loop() {

  if (j % 10 == 0) {
    TB.printI2CBusScan();
  }
  TB.setColor(TB.Wheel(j++));
  delay(100);
  return;
}
