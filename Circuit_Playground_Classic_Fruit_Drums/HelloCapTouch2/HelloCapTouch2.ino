// SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_CircuitPlayground.h>

#define CAP_THRESHOLD   50
#define DEBOUNCE        250

////////////////////////////////////////////////////////////////////////////
boolean capButton(uint8_t pad) {
  if (CircuitPlayground.readCap(pad) > CAP_THRESHOLD) {
    return true;  
  } else {
    return false;
  }
}

////////////////////////////////////////////////////////////////////////////
void setup() {
  // Initialize serial.
  Serial.begin(9600); 
  
  // Initialize Circuit Playground library.
  CircuitPlayground.begin();
}

////////////////////////////////////////////////////////////////////////////
void loop() {
  // Check if capacitive touch exceeds threshold.
  if (capButton(1)) {

      // Print message.
      Serial.println("Touched!");
      
      // But not too often.
      delay(DEBOUNCE); 
  }
}
